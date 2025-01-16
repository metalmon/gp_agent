"""
Tool for analyzing estimation trends across a project.
"""

from typing import Dict, Any, List, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class AnalyzeEstimateTrendsTool(BaseTaskTool):
    """Tool for analyzing estimation trends across a project"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="analyze_estimate_trends",
            description="Analyze estimation trends across a project"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "ID of the project to analyze estimation trends for"
                }
            },
            "required": ["project_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - project_id: Project ID
            settings: Optional settings to customize tool behavior
            
        Returns:
            Dict with estimation trends analysis including:
            - Overall project estimation accuracy
            - Trends in estimate changes
            - Common patterns in estimates
            - Recommendations for improvement
        """
        project_id = params["project_id"]
        log_debug(f"Analyzing estimation trends for project {project_id}")
        
        # Get project tasks
        tasks = self.api.get_project_tasks(project_id)
        log_debug(f"Got {len(tasks)} tasks from API")
        
        # Analyze estimates for each task
        task_analyses = []
        total_initial_hours = 0
        total_current_hours = 0
        
        for task in tasks:
            log_debug(f"Processing task: {task['name']}")
            # Get estimate history for task
            history = GPTaskEstimate.get_estimate_history(task["name"])
            log_debug(f"Got {len(history) if history else 0} estimates for task")
            
            if not history:
                log_debug("No history, skipping task")
                continue
                
            # Get initial and current estimates
            initial_estimate = history[-1]  # Oldest estimate
            current_estimate = history[0]   # Latest estimate
            log_debug(f"Initial estimate: {initial_estimate.estimated_hours} hours")
            log_debug(f"Current estimate: {current_estimate.estimated_hours} hours")
            
            # Calculate total hours
            total_initial_hours += initial_estimate.estimated_hours
            total_current_hours += current_estimate.estimated_hours
            log_debug(f"Running totals - initial: {total_initial_hours}, current: {total_current_hours}")
            
            # Calculate change percentage
            change_percent = ((current_estimate.estimated_hours - initial_estimate.estimated_hours) 
                             / initial_estimate.estimated_hours * 100) if initial_estimate.estimated_hours else 0
            
            # Analyze confidence levels
            confidence_changes = self._analyze_confidence_changes(history)
            
            task_analyses.append({
                "task_id": task["name"],
                "title": task["title"],
                "status": task["status"],
                "initial_estimate": initial_estimate.estimated_hours,
                "current_estimate": current_estimate.estimated_hours,
                "change_percentage": change_percent,
                "confidence_trend": confidence_changes
            })
        
        log_debug(f"Final totals - initial: {total_initial_hours}, current: {total_current_hours}")
        
        # Calculate project-level metrics
        total_change_percent = ((total_current_hours - total_initial_hours) 
                              / total_initial_hours * 100) if total_initial_hours else 0
        
        # Generate insights and recommendations
        insights = self._generate_insights(task_analyses, total_change_percent)
        recommendations = self._generate_recommendations(insights)
        
        return {
            "project_metrics": {
                "total_initial_hours": total_initial_hours,
                "total_current_hours": total_current_hours,
                "total_change_percentage": total_change_percent
            },
            "task_trends": task_analyses,
            "insights": insights,
            "recommendations": recommendations
        }

    def _analyze_confidence_changes(self, history: List[Dict]) -> str:
        """Analyze how confidence levels have changed over time"""
        if not history or len(history) < 2:
            return "Stable"
            
        confidence_map = {
            "Low": 1,
            "Medium": 2,
            "High": 3
        }
        
        # Get confidence scores
        scores = [confidence_map.get(est.confidence_level, 0) for est in history]
        
        # Compare latest to oldest
        if scores[0] > scores[-1]:
            return "Increasing"
        elif scores[0] < scores[-1]:
            return "Decreasing"
        else:
            return "Stable"

    def _generate_insights(self, task_analyses: List[Dict], total_change_percent: float) -> List[Dict]:
        """Generate insights based on estimation trends"""
        insights = []
        
        log_debug(f"Generating insights for {len(task_analyses)} tasks")
        log_debug(f"Total change percent: {total_change_percent}")
        
        # Analyze overall trend
        if abs(total_change_percent) > 20:
            log_debug("Found significant change")
            insights.append({
                "type": "significant_change",
                "description": f"Project estimates have changed significantly ({total_change_percent:+.1f}%)",
                "impact": "high"
            })
        
        # Find tasks with major changes
        major_changes = [t for t in task_analyses if abs(t["change_percentage"]) >= 50]
        log_debug(f"Found {len(major_changes)} tasks with major changes")
        if major_changes:
            insights.append({
                "type": "major_changes",
                "description": f"{len(major_changes)} tasks had estimates change by more than 50%",
                "impact": "high"
            })
        
        # Analyze confidence trends
        decreasing_confidence = [t for t in task_analyses if t["confidence_trend"] == "Decreasing"]
        log_debug(f"Found {len(decreasing_confidence)} tasks with decreasing confidence")
        if decreasing_confidence:
            insights.append({
                "type": "decreasing_confidence",
                "description": f"{len(decreasing_confidence)} tasks show decreasing estimation confidence",
                "impact": "medium"
            })
            
        # Analyze estimation patterns
        increasing_estimates = [t for t in task_analyses if t["change_percentage"] > 0]
        decreasing_estimates = [t for t in task_analyses if t["change_percentage"] < 0]
        log_debug(f"Found {len(increasing_estimates)} increasing estimates and {len(decreasing_estimates)} decreasing estimates")
        
        if len(increasing_estimates) > len(task_analyses) * 0.7:
            insights.append({
                "type": "systematic_underestimation",
                "description": "Most tasks are being underestimated initially",
                "impact": "medium"
            })
        elif len(decreasing_estimates) > len(task_analyses) * 0.7:
            insights.append({
                "type": "systematic_overestimation", 
                "description": "Most tasks are being overestimated initially",
                "impact": "medium"
            })
        
        log_debug(f"Generated {len(insights)} insights")
        return insights

    def _generate_recommendations(self, insights: List[Dict]) -> List[str]:
        """Generate recommendations based on insights"""
        recommendations = []
        
        for insight in insights:
            if insight["type"] == "significant_change":
                recommendations.extend([
                    "Review estimation process for potential systematic biases",
                    "Consider breaking down large tasks into smaller, more predictable units"
                ])
                
            elif insight["type"] == "major_changes":
                recommendations.extend([
                    "Improve initial task analysis to better understand requirements",
                    "Document reasons for major estimate changes to improve future estimates"
                ])
                
            elif insight["type"] == "decreasing_confidence":
                recommendations.extend([
                    "Review tasks with decreasing confidence to identify common challenges",
                    "Consider additional planning or spike tasks for unclear requirements"
                ])
                
            elif insight["type"] == "systematic_underestimation":
                recommendations.extend([
                    "Consider adding buffer time to initial estimates",
                    "Review historical data to calibrate estimation process"
                ])
                
            elif insight["type"] == "systematic_overestimation":
                recommendations.extend([
                    "Analyze if requirements are being over-complicated during estimation",
                    "Consider breaking down estimates into smaller, more accurate components"
                ])
        
        return list(set(recommendations))  # Remove duplicates 