"""
Tool for getting tasks assigned to a user.
"""

from typing import Dict, List, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from datetime import datetime


class GetUserTasksTool(BaseTaskTool):
    """Tool for getting tasks assigned to a specific user"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_user_tasks",
            description="Get tasks assigned to a specific user with optional filtering"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "ID of the user to get tasks for"
                },
                "status": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
                    },
                    "description": "Optional list of statuses to filter by"
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to filter tasks from"
                }
            },
            "required": ["user_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters
            settings: Optional settings to customize tool behavior
        
        Returns:
            List of tasks matching the criteria
        """
        log_debug(f"Getting tasks for user {params['user_id']}")
        
        try:
            # Get tasks using GameplanAPI
            tasks = self.api.get_user_tasks(
                user_id=params["user_id"],
                status=params.get("status"),
                project_id=params.get("project_id")
            )
            
            # Format tasks and handle datetime fields
            formatted_tasks = []
            for task in tasks:
                # Convert datetime fields
                start_date = task.get('start_date')
                if isinstance(start_date, datetime):
                    start_date = start_date.isoformat()
                    
                due_date = task.get('due_date')
                if isinstance(due_date, datetime):
                    due_date = due_date.isoformat()
                    
                modified = task.get('modified')
                if isinstance(modified, datetime):
                    modified = modified.isoformat()
                    
                created = task.get('creation')
                if isinstance(created, datetime):
                    created = created.isoformat()
                
                formatted_task = {
                    "id": task.get('name'),
                    "title": task.get('title'),
                    "description": task.get('description'),
                    "status": task.get('status'),
                    "priority": task.get('priority'),
                    "start_date": start_date,
                    "due_date": due_date,
                    "created": created,
                    "modified": modified,
                    "project_id": task.get('project'),
                    "project_title": task.get('project_title', ''),
                    "is_completed": task.get('is_completed', 0),
                    "assigned_to": task.get('assigned_to')
                }
                formatted_tasks.append(formatted_task)
            
            log_debug(f"Found {len(formatted_tasks)} tasks")
            return formatted_tasks
            
        except Exception as e:
            log_debug(f"Error getting user tasks: {str(e)}")
            raise 