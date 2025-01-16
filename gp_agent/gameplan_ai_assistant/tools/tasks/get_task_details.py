"""
Tool for getting task details.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from datetime import datetime
import json


class GetTaskDetailsTool(BaseTaskTool):
    """Tool for getting detailed information about a task"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_task_details",
            description="Get detailed information about a task with optional format conversion"
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
                    "description": "ID of the task to get details for"
                },
                "format": {
                    "type": "string",
                    "description": "Content format for description",
                    "enum": ["html", "markdown"],
                    "default": "html"
                }
            },
            "required": ["task_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - task_id: Task ID
                   - format: Content format (html/markdown)
            settings: Optional settings for tool execution
        """
        log_debug(f"Getting details for task {params['task_id']} in {params.get('format', 'html')} format")
        
        try:
            # Get task details using GameplanAPI
            task = self.api.get_task_details(params["task_id"])
            
            # Convert description to markdown if requested
            description = task.get("description", "")
            if params.get("format") == "markdown" and description:
                description = self.parser.html_to_markdown(description)
                log_debug(f"Converted description to markdown: {description[:200]}...")
            
            # Get project title if available
            project_title = ""
            if task.get("project"):
                project_title = self.get_project_title(task["project"])
            
            # Convert datetime fields
            due_date = str(task.get("due_date"))
            created = str(task.get("creation"))
            modified = str(task.get("modified"))
            
            # Format response
            result = {
                "task_id": params["task_id"],
                "title": task.get("title", ""),
                "description": description,
                "status": task.get("status", ""),
                "priority": task.get("priority", ""),
                "assignee": task.get("assigned_to", ""),
                "due_date": due_date,
                "project_id": task.get("project", ""),
                "project_title": project_title,
                "created": created,
                "modified": modified
            }
            
            log_debug(f"Successfully got task details: {result}")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error getting task details: {str(e)}")
            return json.dumps({
                "error": f"Failed to get task details: {str(e)}",
                "message": "An error occurred while trying to get the task details",
                "provided_params": params
            }, ensure_ascii=False) 