"""
Tool for updating task time estimates.
"""

import frappe
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .base import BaseTaskTool
from ...utils.logging import log_debug


class UpdateTaskEstimateTool(BaseTaskTool):
    """Tool for updating task time estimates"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="update_task_estimate",
            description="Update task time estimate with new hours and confidence level"
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
                    "description": "ID of the task"
                },
                "estimated_hours": {
                    "type": "number",
                    "description": "Total estimated hours"
                },
                "remaining_hours": {
                    "type": "number",
                    "description": "Hours remaining (defaults to estimated_hours if not provided)"
                },
                "confidence_level": {
                    "type": "string",
                    "description": "Confidence in estimate",
                    "enum": ["High", "Medium", "Low"]
                },
                "note": {
                    "type": "string",
                    "description": "Note explaining the estimate"
                }
            },
            "required": ["task_id", "estimated_hours"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
            
        Returns:
            Tool execution results
        """
        task_id = params["task_id"]
        estimated_hours = params["estimated_hours"]
        remaining_hours = params.get("remaining_hours")
        confidence_level = params.get("confidence_level")
        note = params.get("note")
        
        log_debug(f"Updating estimate for task {task_id}")
        
        # Create new estimate document
        estimate = frappe.get_doc({
            "doctype": "GP Task Estimate",
            "task": task_id,
            "estimated_hours": estimated_hours,
            "remaining_hours": remaining_hours if remaining_hours is not None else estimated_hours,
            "confidence_level": confidence_level,
            "note": note
        }).insert()
        
        # Get creation timestamp and convert to ISO format if needed
        creation = estimate.creation
        if isinstance(creation, datetime):
            creation = creation.isoformat()
        
        result = {
            "id": estimate.name,
            "task_id": estimate.task,
            "estimated_hours": estimate.estimated_hours,
            "remaining_hours": estimate.remaining_hours,
            "confidence_level": estimate.confidence_level,
            "note": estimate.note,
            "created_at": creation,
            "created_by": estimate.owner
        }
        
        # Ensure result is JSON serializable
        return json.dumps(result, ensure_ascii=False) 