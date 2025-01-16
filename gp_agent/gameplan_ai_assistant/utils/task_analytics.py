import frappe
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from ..doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate
from ..doctype.gp_task_dependency.gp_task_dependency import GPTaskDependency
from ..gameplan_api import GameplanAPI

def analyze_critical_path(project_id: str) -> Dict[str, Any]:
    """Analyze critical path for project tasks
    
    Args:
        project_id: ID of the project to analyze
    
    Returns:
        Dict with critical path analysis including:
        - List of tasks in critical path
        - Total estimated duration
        - Earliest possible completion date
        - Risk factors
    """
    # Get all project tasks
    tasks = frappe.get_all(
        "GP Task",
        filters={"project": project_id, "status": ["not in", ["Canceled", "Done"]]},
        fields=["name", "title", "start_date", "due_date", "status", "priority"]
    )
    
    # Build dependency graph
    graph: Dict[str, Dict[str, Any]] = {}
    for task in tasks:
        task_id = task["name"]
        deps = GPTaskDependency.get_dependencies(task_id)
        estimate = GPTaskEstimate.get_latest_estimate(task_id)
        
        graph[task_id] = {
            "task": task,
            "blocked_by": [d.task for d in deps["blocked_by"]],
            "duration": estimate.estimated_hours if estimate else 0,
            "earliest_start": None,
            "earliest_finish": None
        }
    
    # Calculate earliest start/finish times (forward pass)
    start_nodes = [tid for tid, data in graph.items() if not data["blocked_by"]]
    _calculate_earliest_times(graph, start_nodes)
    
    # Find critical path
    critical_path = _find_critical_path(graph)
    
    # Calculate metrics
    total_duration = sum(graph[tid]["duration"] for tid in critical_path)
    completion_date = _calculate_completion_date(graph, critical_path)
    risk_factors = _analyze_risk_factors(graph, critical_path)
    
    return {
        "critical_path": [
            {
                "task_id": tid,
                "title": graph[tid]["task"]["title"],
                "duration": graph[tid]["duration"],
                "earliest_start": str(graph[tid]["earliest_start"]) if graph[tid]["earliest_start"] else None,
                "earliest_finish": str(graph[tid]["earliest_finish"]) if graph[tid]["earliest_finish"] else None,
                "status": graph[tid]["task"]["status"],
                "priority": graph[tid]["task"]["priority"]
            }
            for tid in critical_path
        ],
        "total_duration_hours": total_duration,
        "estimated_completion_date": str(completion_date) if completion_date else None,
        "risk_factors": risk_factors
    }

def predict_completion_dates(project_id: str) -> Dict[str, Any]:
    """Predict completion dates for project tasks based on estimates and dependencies
    
    Args:
        project_id: ID of the project to analyze
    
    Returns:
        Dict with completion predictions including:
        - Predicted dates for each task
        - Confidence levels
        - Risk assessment
    """
    # Get critical path analysis
    critical_path_analysis = analyze_critical_path(project_id)
    
    # Get all tasks with their estimates
    tasks = frappe.get_all(
        "GP Task",
        filters={"project": project_id, "status": ["not in", ["Canceled", "Done"]]},
        fields=["name", "title", "start_date", "due_date", "status", "priority"]
    )
    
    predictions = {}
    for task in tasks:
        task_id = task.name
        estimate = GPTaskEstimate.get_latest_estimate(task_id)
        history = GPTaskEstimate.get_estimate_history(task_id) if estimate else []
        
        prediction = _predict_task_completion(
            task,
            estimate,
            history,
            task_id in [t["task_id"] for t in critical_path_analysis["critical_path"]]
        )
        predictions[task_id] = prediction
    
    # Calculate project-level metrics
    dates_with_estimates = [p for p in predictions.values() if p["optimistic_date"]]
    optimistic_date = max(p["optimistic_date"] for p in dates_with_estimates) if dates_with_estimates else None
    pessimistic_date = max(p["pessimistic_date"] for p in dates_with_estimates) if dates_with_estimates else None
    
    return {
        "tasks": predictions,
        "project_completion": {
            "optimistic_date": optimistic_date,
            "expected_date": critical_path_analysis["estimated_completion_date"],
            "pessimistic_date": pessimistic_date,
            "confidence_level": _calculate_project_confidence(predictions),
            "risk_factors": critical_path_analysis["risk_factors"]
        }
    }

def analyze_team_workload(team_id: str) -> Dict[str, Any]:
    """Analyze team workload and capacity
    
    Args:
        team_id: ID of the team to analyze
    
    Returns:
        Dict with workload analysis including:
        - Per-user workload
        - Team capacity
        - Bottlenecks
    """
    # Get team members through GameplanAPI
    api = GameplanAPI()
    team_members = api.get_team_users(team_id)
    
    workloads = {}
    for member in team_members:
        if not member["enabled"]:
            continue
            
        user_id = member["id"]
        tasks = frappe.get_all(
            "GP Task",
            filters={
                "assigned_to": user_id,
                "status": ["not in", ["Canceled", "Done"]]
            },
            fields=["name", "title", "status", "priority", "due_date"]
        )
        
        # Calculate workload
        total_hours = 0
        task_details = []
        for task in tasks:
            estimate = GPTaskEstimate.get_latest_estimate(task.name)
            if estimate:
                total_hours += estimate.remaining_hours
                task_details.append({
                    "task_id": task.name,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": str(task.due_date) if task.due_date else None,
                    "remaining_hours": estimate.remaining_hours
                })
        
        workloads[user_id] = {
            "user": member,
            "total_hours": total_hours,
            "tasks": task_details,
            "overloaded": total_hours > 40,  # Assuming 40-hour work week
            "available_capacity": max(40 - total_hours, 0)
        }
    
    # Find bottlenecks
    bottlenecks = [
        {
            "user": data["user"]["full_name"],
            "total_hours": data["total_hours"],
            "overload_hours": data["total_hours"] - 40
        }
        for data in workloads.values()
        if data["overloaded"]
    ]
    
    return {
        "workloads": workloads,
        "team_capacity": {
            "total_assigned_hours": sum(w["total_hours"] for w in workloads.values()),
            "total_available_hours": sum(w["available_capacity"] for w in workloads.values()),
            "bottlenecks": bottlenecks
        }
    }

def _calculate_earliest_times(graph: Dict[str, Dict[str, Any]], start_nodes: List[str]) -> None:
    """Calculate earliest start and finish times for tasks (forward pass)"""
    processed = set()
    
    def process_node(node_id: str, current_time: float) -> None:
        if node_id in processed:
            return
        
        node = graph[node_id]
        
        # Can't start until all blocking tasks are done
        for blocker_id in node["blocked_by"]:
            if blocker_id not in processed:
                return
            blocker = graph[blocker_id]
            current_time = max(current_time, blocker["earliest_finish"] or 0)
        
        node["earliest_start"] = current_time
        node["earliest_finish"] = current_time + node["duration"]
        processed.add(node_id)
        
        # Process tasks that this task blocks
        for next_id, next_data in graph.items():
            if node_id in next_data["blocked_by"]:
                process_node(next_id, node["earliest_finish"])
    
    # Start with nodes that have no dependencies
    for node_id in start_nodes:
        process_node(node_id, 0)

def _find_critical_path(graph: Dict[str, Dict[str, Any]]) -> List[str]:
    """Find the critical path in the task graph"""
    # Find end nodes (nodes that don't block anything)
    end_nodes = []
    blocking_tasks = {tid for data in graph.values() for tid in data["blocked_by"]}
    for task_id in graph:
        if task_id not in blocking_tasks:
            end_nodes.append(task_id)
    
    # Find the path with longest duration
    def find_path(node_id: str, visited: set) -> Tuple[List[str], float]:
        if node_id in visited:
            return [], 0
        
        visited.add(node_id)
        node = graph[node_id]
        
        # Find the longest path through dependencies
        max_path = []
        max_duration = 0
        
        for dep_id in node["blocked_by"]:
            path, duration = find_path(dep_id, visited.copy())
            if duration > max_duration:
                max_path = path
                max_duration = duration
        
        return max_path + [node_id], max_duration + node["duration"]
    
    # Find the longest path from any end node
    critical_path = []
    max_duration = 0
    
    for end_node in end_nodes:
        path, duration = find_path(end_node, set())
        if duration > max_duration:
            critical_path = path
            max_duration = duration
    
    return critical_path

def _calculate_completion_date(graph: Dict[str, Dict[str, Any]], critical_path: List[str]) -> datetime:
    """Calculate estimated completion date based on critical path"""
    start_date = datetime.now()
    
    # Find earliest start date from tasks
    for task_id in critical_path:
        task = graph[task_id]["task"]
        if task["start_date"]:
            if task["start_date"] < start_date:
                start_date = task["start_date"]
    
    # Add total duration from critical path
    total_hours = sum(graph[tid]["duration"] for tid in critical_path)
    working_days = total_hours / 8  # Assuming 8-hour work days
    
    # Add working days to start date
    completion_date = start_date
    days_added = 0
    while days_added < working_days:
        completion_date += timedelta(days=1)
        # Skip weekends
        if completion_date.weekday() < 5:  # Monday = 0, Sunday = 6
            days_added += 1
    
    return completion_date

def _analyze_risk_factors(graph: Dict[str, Dict[str, Any]], critical_path: List[str]) -> List[Dict[str, str]]:
    """Analyze risk factors in critical path"""
    risks = []
    
    for task_id in critical_path:
        task = graph[task_id]["task"]
        
        # Check high priority tasks
        if task["priority"] == "High":
            risks.append({
                "type": "priority",
                "description": f"Task '{task['title']}' is high priority",
                "impact": "high"
            })
            
        # Check task dependencies
        if len(graph[task_id]["blocked_by"]) > 2:
            risks.append({
                "type": "dependency",
                "description": f"Task '{task['title']}' has many dependencies ({len(graph[task_id]['blocked_by'])})",
                "impact": "medium"
            })
            
        # Check task duration
        if graph[task_id]["duration"] > 40:  # More than a week
            risks.append({
                "type": "duration",
                "description": f"Task '{task['title']}' has long duration ({graph[task_id]['duration']} hours)",
                "impact": "medium"
            })
            
        # Check task status
        if task["status"] == "Blocked":
            risks.append({
                "type": "status",
                "description": f"Task '{task['title']}' is blocked",
                "impact": "high"
            })
            
        # Add dependency risks for critical path tasks
        for blocker_id in graph[task_id]["blocked_by"]:
            blocker = graph[blocker_id]["task"]
            risks.append({
                "type": "dependency",
                "description": f"Task '{task['title']}' depends on {blocker['title']}",
                "impact": "high"
            })
            
    return risks

def _predict_task_completion(
    task: Dict[str, Any],
    estimate: Optional["GPTaskEstimate"],
    history: List["GPTaskEstimate"],
    is_critical: bool
) -> Dict[str, Any]:
    """Predict completion date for a single task"""
    if not estimate:
        return {
            "task_id": task.name,
            "optimistic_date": None,
            "expected_date": None,
            "pessimistic_date": None,
            "confidence_level": None
        }
    
    # Calculate base duration in working days
    working_days = estimate.remaining_hours / 8
    
    # Add different buffers based on confidence and history
    if estimate.confidence_level == "High":
        buffer_multiplier = 1.1
    elif estimate.confidence_level == "Medium":
        buffer_multiplier = 1.2
    else:
        buffer_multiplier = 1.5
    
    # Add extra buffer for critical path tasks
    if is_critical:
        buffer_multiplier += 0.1
    
    # Calculate dates
    start_date = datetime.strptime(task.start_date, "%Y-%m-%d") if task.start_date else datetime.now()
    
    def add_working_days(date: datetime, days: float) -> datetime:
        result = date
        days_added = 0
        while days_added < days:
            result += timedelta(days=1)
            if result.weekday() < 5:  # Skip weekends
                days_added += 1
        return result
    
    optimistic_date = add_working_days(start_date, working_days)
    expected_date = add_working_days(start_date, working_days * buffer_multiplier)
    pessimistic_date = add_working_days(start_date, working_days * buffer_multiplier * 1.5)
    
    return {
        "task_id": task.name,
        "optimistic_date": optimistic_date,
        "expected_date": expected_date,
        "pessimistic_date": pessimistic_date,
        "confidence_level": estimate.confidence_level
    }

def _calculate_project_confidence(predictions: Dict[str, Dict[str, Any]]) -> str:
    """Calculate overall project confidence level"""
    confidence_scores = {
        "High": 3,
        "Medium": 2,
        "Low": 1
    }
    
    total_score = 0
    count = 0
    
    for pred in predictions.values():
        if pred["confidence_level"]:
            total_score += confidence_scores[pred["confidence_level"]]
            count += 1
    
    if not count:
        return None
    
    avg_score = total_score / count
    if avg_score > 2.5:
        return "High"
    elif avg_score > 1.5:
        return "Medium"
    else:
        return "Low" 