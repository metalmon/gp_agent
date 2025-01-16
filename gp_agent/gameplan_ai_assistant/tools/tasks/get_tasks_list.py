"""
Tool for listing tasks in a project.
"""

from typing import Dict, Any, Optional, List
from .base import BaseTaskTool
from ...utils.logging import log_debug
from datetime import datetime
import json


class GetTasksListTool(BaseTaskTool):
    """Tool for listing tasks in a project with filtering"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_tasks_list",
            description="List tasks in a project with filtering"
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
                    "description": "ID of the project to list tasks from"
                },
                "status": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Optional list of statuses to filter by (Backlog/Todo/In Progress/Done/Canceled)"
                },
                "assigned_to": {
                    "type": "string",
                    "description": "Optional user to filter tasks assigned to"
                }
            },
            "required": ["project_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
        
        Returns:
            List of tasks matching the filter criteria or error message if project_id is missing
        """
        log_debug(f"GetTasksListTool params: {params}")
        
        # Check for required project_id
        if "project_id" not in params:
            return [{
                "error": "Missing required parameter: project_id",
                "message": "Please provide a project ID to list tasks from. Example: {\"project_id\": \"123\", \"status\": [\"Backlog\"]}",
                "provided_params": params
            }]
            
        try:
            # Get tasks from API
            tasks = self.api.get_all_project_tasks(
                project_id=params["project_id"],
                status=params.get("status"),
                assigned_to=params.get("assigned_to")
            )
            
            # Format response
            formatted_tasks = []
            for task in tasks:
                # Convert datetime objects to ISO format strings
                start_date = str(task.get('start_date'))
                due_date = str(task.get('due_date'))
                modified = str(task.get('modified'))
                formatted_task = {
                    "id": task.get('name'),
                    "title": task.get('title', ''),
                    "description": task.get('description'),
                    "status": task.get('status'),
                    "priority": task.get('priority'),
                    "start_date": start_date,
                    "due_date": due_date,
                    "assigned_to": task.get('assigned_to'),
                    "is_completed": task.get('is_completed'),
                    "comments_count": task.get('comments_count'),
                    "idx": task.get('idx'),
                    "modified": modified
                }
                formatted_tasks.append(formatted_task)
            
            # Return list of formatted tasks
            return formatted_tasks
            
        except Exception as e:
            log_debug(f"Error in GetTasksListTool: {str(e)}")
            return [{
                "error": f"Failed to list tasks: {str(e)}",
                "message": "An error occurred while trying to list tasks",
                "provided_params": params
            }] 