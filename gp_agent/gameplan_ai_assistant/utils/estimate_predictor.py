import frappe
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate

def analyze_estimate_changes(task_id: str) -> Dict[str, Any]:
    """Analyze reasons for estimate changes in a task
    
    Args:
        task_id: ID of the task to analyze
    
    Returns:
        Dict with change analysis including:
        - Change categories
        - Impact factors
        - Common patterns
        - Similar historical cases
    """
    task = frappe.get_doc("GP Task", task_id)
    history = GPTaskEstimate.get_estimate_history(task_id)
    
    if not history or len(history) < 2:
        return {
            "task_id": task_id,
            "has_changes": False
        }
    
    # Analyze changes
    changes = _analyze_change_sequence(history)
    
    # Find similar historical cases
    similar_cases = _find_similar_cases(task, changes)
    
    # Identify impact factors
    impact_factors = _identify_impact_factors(changes, similar_cases)
    
    return {
        "task_id": task_id,
        "has_changes": True,
        "changes": changes,
        "similar_cases": similar_cases,
        "impact_factors": impact_factors,
        "change_patterns": _identify_change_patterns(changes)
    }

def predict_estimate_changes(task_id: str) -> Dict[str, Any]:
    """Predict potential future changes in task estimates
    
    Args:
        task_id: ID of the task to analyze
    
    Returns:
        Dict with predictions including:
        - Likelihood of changes
        - Expected adjustments
        - Risk factors
        - Preventive actions
    """
    task = frappe.get_doc("GP Task", task_id)
    history = GPTaskEstimate.get_estimate_history(task_id)
    current = GPTaskEstimate.get_latest_estimate(task_id)
    
    if not current:
        return {
            "task_id": task_id,
            "has_estimate": False
        }
    
    # Get similar tasks
    similar_tasks = _find_similar_tasks(task)
    
    # Analyze historical patterns
    patterns = _analyze_historical_patterns(similar_tasks)
    
    # Calculate probabilities
    change_probabilities = _calculate_change_probabilities(task, current, patterns)
    
    return {
        "task_id": task_id,
        "has_estimate": True,
        "current_estimate": {
            "hours": current.estimated_hours,
            "confidence": current.confidence_level
        },
        "change_predictions": change_probabilities,
        "risk_factors": _identify_risk_factors(task, current, patterns),
        "preventive_actions": _suggest_preventive_actions(change_probabilities)
    }

def find_similar_tasks(task_id: str) -> Dict[str, Any]:
    """Find historically similar tasks and their estimation patterns
    
    Args:
        task_id: ID of the task to analyze
    
    Returns:
        Dict with similar tasks including:
        - Similar tasks list
        - Common patterns
        - Lessons learned
    """
    task = frappe.get_doc("GP Task", task_id)
    
    # Find similar tasks
    similar_tasks = _find_similar_tasks(task)
    
    # Analyze patterns
    patterns = _analyze_historical_patterns(similar_tasks)
    
    # Extract lessons
    lessons = _extract_estimation_lessons(similar_tasks, patterns)
    
    return {
        "task_id": task_id,
        "similar_tasks": [
            {
                "task_id": t.name,
                "title": t.title,
                "initial_estimate": _get_initial_estimate(t),
                "final_estimate": _get_final_estimate(t),
                "similarity_score": t.similarity_score,
                "key_differences": t.key_differences
            }
            for t in similar_tasks
        ],
        "common_patterns": patterns,
        "lessons_learned": lessons
    }

def _analyze_change_sequence(history: List["GPTaskEstimate"]) -> List[Dict[str, Any]]:
    """Analyze sequence of estimate changes"""
    changes = []
    
    for i in range(1, len(history)):
        prev = history[i-1]
        curr = history[i]
        
        change = {
            "timestamp": curr.creation_timestamp,
            "from_hours": prev.estimated_hours,
            "to_hours": curr.estimated_hours,
            "change_percentage": ((curr.estimated_hours - prev.estimated_hours) / prev.estimated_hours * 100),
            "confidence_change": _compare_confidence(prev.confidence_level, curr.confidence_level),
            "note": curr.note
        }
        
        # Categorize change
        change["category"] = _categorize_change(change)
        
        changes.append(change)
    
    return changes

def _find_similar_cases(task: Any, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find similar historical cases with estimate changes"""
    similar_cases = []
    
    # Get all completed tasks in the project
    completed_tasks = frappe.get_all(
        "GP Task",
        filters={
            "project": task.project,
            "status": "Done",
            "name": ["!=", task.name]
        },
        fields=["name", "title", "description"]
    )
    
    for t in completed_tasks:
        history = GPTaskEstimate.get_estimate_history(t.name)
        if len(history) > 1:
            case_changes = _analyze_change_sequence(history)
            similarity_score = _calculate_change_similarity(changes, case_changes)
            
            if similarity_score > 0.7:  # 70% similarity threshold
                similar_cases.append({
                    "task_id": t.name,
                    "title": t.title,
                    "similarity_score": similarity_score,
                    "changes": case_changes
                })
    
    return sorted(similar_cases, key=lambda x: x["similarity_score"], reverse=True)

def _identify_impact_factors(
    changes: List[Dict[str, Any]],
    similar_cases: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Identify factors that impact estimate changes"""
    factors = []
    
    # Analyze timing patterns
    timing_patterns = _analyze_timing_patterns(changes)
    if timing_patterns:
        factors.extend(timing_patterns)
    
    # Analyze magnitude patterns
    magnitude_patterns = _analyze_magnitude_patterns(changes)
    if magnitude_patterns:
        factors.extend(magnitude_patterns)
    
    # Analyze similar cases
    if similar_cases:
        common_factors = _find_common_factors(changes, similar_cases)
        factors.extend(common_factors)
    
    return factors

def _identify_change_patterns(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify patterns in estimate changes"""
    patterns = []
    
    if not changes:
        return patterns
    
    # Look for gradual increase pattern
    if all(c["change_percentage"] > 0 for c in changes):
        patterns.append({
            "type": "gradual_increase",
            "description": "Estimates consistently increase over time",
            "confidence": "High"
        })
    
    # Look for early vs late changes
    early_changes = changes[:len(changes)//2]
    late_changes = changes[len(changes)//2:]
    
    early_avg = sum(abs(c["change_percentage"]) for c in early_changes) / len(early_changes) if early_changes else 0
    late_avg = sum(abs(c["change_percentage"]) for c in late_changes) / len(late_changes) if late_changes else 0
    
    if early_avg > late_avg * 2:
        patterns.append({
            "type": "early_adjustments",
            "description": "Major adjustments made early in the task",
            "confidence": "Medium"
        })
    elif late_avg > early_avg * 2:
        patterns.append({
            "type": "late_adjustments",
            "description": "Major adjustments made late in the task",
            "confidence": "High"
        })
    
    return patterns

def _find_similar_tasks(task: Any) -> List[Any]:
    """Find similar tasks based on various criteria"""
    # Get all completed tasks
    completed_tasks = frappe.get_all(
        "GP Task",
        filters={
            "project": task.project,
            "status": "Done"
        },
        fields=["name", "title", "description", "priority"]
    )
    
    similar_tasks = []
    for t in completed_tasks:
        similarity_score = _calculate_task_similarity(task, t)
        if similarity_score > 0.5:  # 50% similarity threshold
            t.similarity_score = similarity_score
            t.key_differences = _identify_key_differences(task, t)
            similar_tasks.append(t)
    
    return sorted(similar_tasks, key=lambda x: x.similarity_score, reverse=True)

def _calculate_task_similarity(task1: Any, task2: Any) -> float:
    """Calculate similarity score between two tasks"""
    score = 0.0
    
    # Compare titles (simple word overlap)
    words1 = set(task1.title.lower().split())
    words2 = set(task2.title.lower().split())
    title_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
    score += title_similarity * 0.3  # 30% weight
    
    # Compare descriptions
    if task1.description and task2.description:
        desc_words1 = set(task1.description.lower().split())
        desc_words2 = set(task2.description.lower().split())
        desc_similarity = len(desc_words1.intersection(desc_words2)) / len(desc_words1.union(desc_words2))
        score += desc_similarity * 0.4  # 40% weight
    
    # Compare other attributes
    if task1.priority == task2.priority:
        score += 0.3  # 30% weight
    
    return score

def _identify_key_differences(task1: Any, task2: Any) -> List[str]:
    """Identify key differences between two tasks"""
    differences = []
    
    if task1.priority != task2.priority:
        differences.append(f"Different priority: {task1.priority} vs {task2.priority}")
    
    if task1.assigned_to != task2.assigned_to:
        differences.append("Different assignee")
    
    # Compare estimate histories
    hist1 = GPTaskEstimate.get_estimate_history(task1.name)
    hist2 = GPTaskEstimate.get_estimate_history(task2.name)
    
    if hist1 and hist2:
        initial1 = hist1[0].estimated_hours
        initial2 = hist2[0].estimated_hours
        if abs(initial1 - initial2) / max(initial1, initial2) > 0.5:  # 50% difference
            differences.append(f"Significantly different initial estimates: {initial1} vs {initial2} hours")
    
    return differences

def _extract_estimation_lessons(
    similar_tasks: List[Any],
    patterns: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Extract lessons learned from similar tasks"""
    lessons = []
    
    # Analyze estimation accuracy
    accuracy_data = []
    for task in similar_tasks:
        history = GPTaskEstimate.get_estimate_history(task.name)
        if history:
            initial = history[0].estimated_hours
            final = history[-1].estimated_hours
            accuracy = abs(final - initial) / initial
            accuracy_data.append({
                "task": task,
                "accuracy": accuracy,
                "initial": initial,
                "final": final
            })
    
    if accuracy_data:
        # Find most accurate estimates
        accurate = [d for d in accuracy_data if d["accuracy"] < 0.2]  # Less than 20% change
        if accurate:
            lessons.append({
                "type": "accurate_estimates",
                "description": "Tasks with accurate initial estimates",
                "examples": [{"task_id": d["task"].name, "accuracy": d["accuracy"]} for d in accurate],
                "common_factors": _find_common_factors_in_accurate_estimates(accurate)
            })
        
        # Find problematic estimates
        problematic = [d for d in accuracy_data if d["accuracy"] > 0.5]  # More than 50% change
        if problematic:
            lessons.append({
                "type": "problematic_estimates",
                "description": "Tasks with significant estimate changes",
                "examples": [{"task_id": d["task"].name, "change": d["accuracy"]} for d in problematic],
                "common_factors": _find_common_factors_in_problematic_estimates(problematic)
            })
    
    return lessons

def _compare_confidence(prev: str, curr: str) -> str:
    """Compare confidence levels"""
    confidence_scores = {"High": 3, "Medium": 2, "Low": 1}
    if confidence_scores[curr] > confidence_scores[prev]:
        return "increased"
    elif confidence_scores[curr] < confidence_scores[prev]:
        return "decreased"
    return "unchanged"

def _categorize_change(change: Dict[str, Any]) -> str:
    """Categorize type of estimate change"""
    if change["change_percentage"] > 50:
        return "major_increase"
    elif change["change_percentage"] > 20:
        return "moderate_increase"
    elif change["change_percentage"] < -50:
        return "major_decrease"
    elif change["change_percentage"] < -20:
        return "moderate_decrease"
    return "minor_adjustment"

def _calculate_change_similarity(
    changes1: List[Dict[str, Any]],
    changes2: List[Dict[str, Any]]
) -> float:
    """Calculate similarity between two change sequences"""
    if not changes1 or not changes2:
        return 0.0
    
    # Compare number of changes
    length_similarity = 1 - abs(len(changes1) - len(changes2)) / max(len(changes1), len(changes2))
    
    # Compare change patterns
    pattern_similarity = sum(
        1 for c1, c2 in zip(changes1, changes2)
        if c1["category"] == c2["category"]
    ) / min(len(changes1), len(changes2))
    
    # Compare magnitude of changes
    magnitude_similarity = 1 - abs(
        sum(c["change_percentage"] for c in changes1) / len(changes1) -
        sum(c["change_percentage"] for c in changes2) / len(changes2)
    ) / 100
    
    return (length_similarity * 0.3 + pattern_similarity * 0.4 + magnitude_similarity * 0.3) 