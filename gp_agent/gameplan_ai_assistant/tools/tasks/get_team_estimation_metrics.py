"""
Tool for getting team estimation metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import frappe
import json

from .base import BaseTaskTool
from ...utils.logging import log_debug
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class GetTeamEstimationMetricsTool(BaseTaskTool):
    """Tool for getting team estimation metrics"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_team_estimation_metrics",
            description="Get estimation metrics for a team including accuracy, confidence levels, and trends"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "team_id": {
                    "type": "string",
                    "description": "ID of the team to analyze"
                },
                "time_period": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["1 week", "1 month", "3 months", "6 months", "1 year"],
                    "default": "1 month"
                }
            },
            "required": ["team_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters
            settings: Optional settings to customize tool behavior
        
        Returns:
            Tool execution results
        """
        team_id = params["team_id"]
        time_period = params.get("time_period", "1 month")
        log_debug(f"Getting estimation metrics for team {team_id} over {time_period}")
        
        # Get all projects for the team
        try:
            projects = self.api.get_team_projects(team_id)
        except Exception as e:
            log_debug(f"Error getting projects for team {team_id}: {e}")
            return {
                "error": f"Error getting projects for team {team_id}",
                "time_period": time_period
            }

        if not projects:
            return {
                "error": f"No projects found for team {team_id}",
                "time_period": time_period
            }
        
        # Calculate start date based on time period
        start_date = self._get_start_date(time_period)
        
        # Get all tasks from all team's projects
        all_tasks = []
        for project in projects:
            try:
                tasks = self.api.get_all_project_tasks(project.name)
                if tasks:
                    all_tasks.extend(tasks)
            except Exception as e:
                log_debug(f"Error getting tasks for project {project.name}: {e}")
                continue
        
        if not all_tasks:
            return {
                "error": f"No tasks found for team {team_id}",
                "time_period": time_period
            }
        
        log_debug(f"Found {len(all_tasks)} tasks across {len(projects)} projects")
        
        # Filter tasks by date
        try:
            tasks = [t for t in all_tasks if self._is_task_in_period(t, start_date)]
        except Exception as e:
            log_debug(f"Error filtering tasks by date: {e}")
            tasks = all_tasks  # Use all tasks if date filtering fails
        
        if not tasks:
            return {
                "error": f"No tasks found in the specified time period ({time_period})",
                "time_period": time_period
            }
        
        # Get estimation history for all tasks
        task_estimates = {}
        estimate_errors = 0
        for task in tasks:
            try:
                history = GPTaskEstimate.get_estimate_history(task["name"])
                if history:
                    task_estimates[task["name"]] = history
            except Exception as e:
                log_debug(f"Error getting estimate history for task {task['name']}: {e}")
                estimate_errors += 1
                continue
        
        # Calculate metrics
        try:
            accuracy_metrics = self._calculate_accuracy_metrics(tasks, task_estimates)
            confidence_metrics = self._calculate_confidence_metrics(task_estimates)
            trend_metrics = self._calculate_trend_metrics(task_estimates)
            completion_metrics = self._calculate_completion_metrics(tasks, task_estimates)
            performance_metrics = self._calculate_performance_metrics(tasks, task_estimates)
        except Exception as e:
            log_debug(f"Error calculating metrics: {e}")
            # Return basic metrics if calculation fails
            return {
                "time_period": time_period,
                "total_tasks": len(tasks),
                "tasks_with_estimates": len(task_estimates),
                "error": "Error calculating detailed metrics"
            }
        
        result = {
            "time_period": time_period,
            "total_tasks": len(tasks),
            "tasks_with_estimates": len(task_estimates),
            "accuracy_metrics": accuracy_metrics,
            "confidence_metrics": confidence_metrics,
            "trend_metrics": trend_metrics,
            "completion_metrics": completion_metrics,
            "performance_metrics": performance_metrics
        }
        
        if estimate_errors > 0:
            result["estimate_errors"] = estimate_errors
            
        # Return result as dict
        return result

    def _get_start_date(self, time_period: str) -> datetime:
        """Calculate start date based on time period"""
        now = datetime.now()
        periods = {
            "1 week": timedelta(days=7),
            "1 month": timedelta(days=30),
            "3 months": timedelta(days=90),
            "6 months": timedelta(days=180),
            "1 year": timedelta(days=365)
        }
        return now - periods.get(time_period, periods["1 month"])

    def _is_task_in_period(self, task: Dict, start_date: datetime) -> bool:
        """Check if task was active in the given period"""
        try:
            modified = frappe.utils.get_datetime(task.get("modified"))
            # Convert datetime for comparison and return
            if isinstance(modified, datetime):
                return modified >= start_date
            return False
        except Exception as e:
            log_debug(f"Error parsing task modified date: {e}")
            # If we can't parse the date, include the task
            return True

    def _calculate_accuracy_metrics(self, tasks: List[Dict], task_estimates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate estimation accuracy metrics"""
        completed_tasks = [t for t in tasks if t.get("is_completed")]
        if not completed_tasks:
            return {
                "average_accuracy": 0,
                "accuracy_distribution": {
                    "highly_accurate": 0,
                    "moderately_accurate": 0,
                    "inaccurate": 0
                }
            }
        
        accuracies = []
        distribution = {
            "highly_accurate": 0,
            "moderately_accurate": 0,
            "inaccurate": 0
        }
        
        for task in completed_tasks:
            if task["name"] not in task_estimates:
                continue
                
            estimates = task_estimates[task["name"]]
            if not estimates:
                continue
                
            initial_estimate = estimates[-1].estimated_hours
            final_estimate = estimates[0].estimated_hours
            
            if initial_estimate == 0:
                continue
                
            accuracy = abs((final_estimate - initial_estimate) / initial_estimate * 100)
            accuracies.append(accuracy)
            
            if accuracy <= 20:
                distribution["highly_accurate"] += 1
            elif accuracy <= 50:
                distribution["moderately_accurate"] += 1
            else:
                distribution["inaccurate"] += 1
        
        total = sum(distribution.values())
        if total > 0:
            distribution = {k: v/total * 100 for k, v in distribution.items()}
        
        return {
            "average_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
            "accuracy_distribution": distribution
        }

    def _calculate_confidence_metrics(self, task_estimates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate confidence level metrics"""
        confidence_counts = {
            "Low": 0,
            "Medium": 0,
            "High": 0
        }
        
        total_estimates = 0
        for estimates in task_estimates.values():
            for estimate in estimates:
                confidence_counts[estimate.confidence_level] += 1
                total_estimates += 1
        
        distribution = {}
        if total_estimates > 0:
            distribution = {k: v/total_estimates * 100 for k, v in confidence_counts.items()}
        
        return {
            "confidence_distribution": distribution,
            "total_estimates": total_estimates
        }

    def _calculate_trend_metrics(self, task_estimates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate estimation trend metrics"""
        trends = {
            "increasing": 0,
            "decreasing": 0,
            "stable": 0
        }
        
        for estimates in task_estimates.values():
            if len(estimates) < 2:
                continue
                
            initial = estimates[-1].estimated_hours
            final = estimates[0].estimated_hours
            
            if final > initial * 1.1:  # 10% threshold
                trends["increasing"] += 1
            elif final < initial * 0.9:
                trends["decreasing"] += 1
            else:
                trends["stable"] += 1
        
        total = sum(trends.values())
        if total > 0:
            trends = {k: v/total * 100 for k, v in trends.items()}
        
        return {
            "estimate_trends": trends
        }

    def _calculate_completion_metrics(self, tasks: List[Dict], task_estimates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate completion-related metrics"""
        completed_tasks = [t for t in tasks if t.get("is_completed")]
        total_tasks = len(tasks)
        
        completion_rate = len(completed_tasks) / total_tasks * 100 if total_tasks > 0 else 0
        
        estimated_completion_rate = len([t for t in completed_tasks if t.get("name") in task_estimates]) / len(completed_tasks) * 100 if completed_tasks else 0
        
        return {
            "completion_rate": completion_rate,
            "estimated_completion_rate": estimated_completion_rate,
            "total_completed": len(completed_tasks),
            "total_tasks": total_tasks
        }

    def _calculate_performance_metrics(self, tasks: List[Dict], task_estimates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate team performance metrics"""
        total_estimated_hours = 0
        total_final_hours = 0
        
        for task in tasks:
            if task.get("name") not in task_estimates:
                continue
                
            estimates = task_estimates[task.get("name")]
            if not estimates:
                continue
                
            total_estimated_hours += estimates[-1].estimated_hours  # Initial estimate
            total_final_hours += estimates[0].estimated_hours  # Final/current estimate
        
        estimation_ratio = total_final_hours / total_estimated_hours if total_estimated_hours > 0 else 1
        
        return {
            "total_estimated_hours": total_estimated_hours,
            "total_final_hours": total_final_hours,
            "estimation_ratio": estimation_ratio
        } 