"""
Tool for updating task details.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
import json


class UpdateTaskTool(BaseTaskTool):
    """Tool for updating task details"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="update_task",
            description="Update task details including status, description, dates, priority and assignee"
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
                    "description": "ID of the task to update"
                },
                "status": {
                    "type": "string",
                    "description": "New status",
                    "enum": ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
                },
                "description": {
                    "type": "string",
                    "description": "New description in markdown format. Supports standard markdown syntax including:\n" +
                                 "- Headers (# ## ###)\n" +
                                 "- Lists (- * 1.)\n" +
                                 "- Code blocks (```language)\n" +
                                 "- Tables (| --- |)\n" +
                                 "- Links and images\n" +
                                 "- Bold, italic, strikethrough\n" +
                                 "- Task lists (- [ ] - [x])"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)"
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date (YYYY-MM-DD)"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level",
                    "enum": ["Urgent", "High", "Medium", "Low"]
                },
                "assigned_to": {
                    "type": "string",
                    "description": "User to assign the task to"
                }
            },
            "required": ["task_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
            
        Returns:
            Tool execution results
        """
        log_debug(f"Updating task {params['task_id']}")
        
        try:
            # Get task details first to check existence
            task = self.api.get_task_details(params["task_id"])
            if not task:
                error_result = {
                    "success": False,
                    "error": f"Task {params['task_id']} not found",
                    "details": "Cannot update task because it does not exist",
                    "provided_params": params
                }
                return json.dumps(error_result, ensure_ascii=False)

            # Get project title if available
            project_title = ""
            if task.get("project"):
                project_title = self.get_project_title(task["project"])
            
            # Convert markdown description to HTML if provided
            html_description = None
            if params.get("description") is not None:
                html_description = self.markdown_to_html(params["description"])
                log_debug(f"Converted description to HTML: {html_description[:200]}...")
            
            # Update task using GameplanAPI
            task = self.api.update_task(
                task_id=params["task_id"],
                status=params.get("status"),
                description=html_description,
                start_date=params.get("start_date"),
                due_date=params.get("due_date"),
                priority=params.get("priority"),
                assigned_to=params.get("assigned_to")
            )
            
            # Return result with metadata
            result = {
                "task_id": params["task_id"],
                "title": task.get("title", ""),
                "description": params.get("description") or task.get("description", ""),  # Return original markdown
                "status": task.get("status", ""),
                "priority": task.get("priority", ""),
                "assignee": task.get("assigned_to", ""),
                "start_date": str(task.get("start_date", "")),
                "due_date": str(task.get("due_date", "")),
                "project_id": task.get("project", ""),
                "project_title": project_title,
                "modified": str(task.get("modified", "")),
                "updated": True
            }
            
            log_debug(f"Successfully updated task: {result}")
            # Ensure result is JSON serializable
            return result
            
        except Exception as e:
            log_debug(f"Error updating task: {str(e)}")
            return {
                "error": f"Failed to update task: {str(e)}",
                "message": "An error occurred while trying to update the task",
                "provided_params": params
            } 