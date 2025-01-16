"""
Tool for getting task estimate history.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate
from ...utils.logging import log_debug
from datetime import datetime


class GetTaskEstimateHistoryTool(BaseTaskTool):
    """Tool for getting estimate history for a specific task"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_task_estimate_history",
            description="Get list of estimates and analysis for a specific task"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "ID of the task to get estimate history for"
                }
            },
            "required": ["task_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - task_id: Task ID
            settings: Optional settings to customize tool behavior
            
        Returns:
            Dict with estimate history and analysis including:
            - Current estimate details
            - History of all estimates
            - Analysis of changes
        """
        task_id = params["task_id"]
        log_debug(f"Getting estimate history for task {task_id}")
        
        # Get current estimate and history
        current = GPTaskEstimate.get_latest_estimate(task_id)
        history = GPTaskEstimate.get_estimate_history(task_id)
        
        if not history:
            return {
                "task_id": task_id,
                "current_estimate": None,
                "history": [],
                "analysis": None
            }
        
        # Calculate analysis
        initial = history[0]
        total_adjustment = current.estimated_hours - initial.estimated_hours if current else 0
        
        # Convert datetime for current estimate
        last_updated = current.creation if current else None
        if isinstance(last_updated, datetime):
            last_updated = last_updated.isoformat()
        
        return {
            "task_id": task_id,
            "current_estimate": {
                "estimated_hours": current.estimated_hours,
                "remaining_hours": current.remaining_hours,
                "confidence_level": current.confidence_level,
                "last_updated": last_updated
            } if current else None,
            "history": [
                {
                    "timestamp": est.creation.isoformat() if isinstance(est.creation, datetime) else est.creation,
                    "user": est.owner,
                    "estimated_hours": est.estimated_hours,
                    "remaining_hours": est.remaining_hours,
                    "confidence_level": est.confidence_level,
                    "note": est.note
                }
                for est in history
            ],
            "analysis": {
                "initial_estimate": initial.estimated_hours,
                "current_estimate": current.estimated_hours if current else initial.estimated_hours,
                "total_adjustment": total_adjustment,
                "completion_percentage": ((initial.estimated_hours - current.remaining_hours) / initial.estimated_hours * 100) if current else 0
            }
        } 