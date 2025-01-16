"""
Tool for creating dependencies between tasks.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from datetime import datetime
import frappe
import json


class CreateTaskDependencyTool(BaseTaskTool):
    """Tool for creating dependencies between tasks"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="create_task_dependency",
            description="Create a dependency relationship between two tasks"
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
                "depends_on_task_id": {
                    "type": "string",
                    "description": "ID of the task that blocks this task"
                },
                "dependency_type": {
                    "type": "string",
                    "description": "Type of dependency",
                    "enum": ["Blocks", "Is Blocked By"]
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID. If not provided, will be fetched from the task"
                },
                "analysis_reason": {
                    "type": "string",
                    "description": "Internal analysis explanation for creating this dependency"
                }
            },
            "required": ["task_id", "depends_on_task_id", "dependency_type"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
            
        Returns:
            Tool execution results
        """
        log_debug(f"Creating dependency: {params['task_id']} {params['dependency_type']} {params['depends_on_task_id']}")
        
        try:
            # Get task details to verify project
            task_details = self.api.get_task_details(params["task_id"])
            if not task_details:
                log_debug(f"Task {params['task_id']} not found")
                return {
                    "success": False,
                    "error": f"Task {params['task_id']} not found",
                    "details": "Cannot create dependency because the specified task does not exist"
                }

            # Check depends_on task exists
            depends_on_details = self.api.get_task_details(params["depends_on_task_id"])
            if not depends_on_details:
                log_debug(f"Task {params['depends_on_task_id']} not found")
                return {
                    "success": False,
                    "error": f"Task {params['depends_on_task_id']} not found",
                    "details": "Cannot create dependency because the specified dependency task does not exist"
                }

            # Handle project ID
            project_id = params.get("project_id")
            project_id_source = "provided"
            
            if not project_id:
                project_id = task_details["project"]
                project_id_source = "fetched from task"
            elif project_id != task_details["project"]:
                old_project_id = project_id
                project_id = task_details["project"]
                project_id_source = f"corrected from {old_project_id} to match task's project"

                
            # Create dependency document
            doc = frappe.get_doc({
                "doctype": "GP Task Dependency",
                "task": params["task_id"],
                "depends_on": params["depends_on_task_id"],
                "project": project_id,
                "dependency_type": params["dependency_type"],
                "created_by": frappe.session.user,
                "creation_timestamp": frappe.utils.now_datetime()
            })
            
            # Insert document
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
            # Format response
            result = {
                "success": True,
                "id": doc.name,
                "task_id": doc.task,
                "depends_on_task_id": doc.depends_on,
                "project": doc.project,
                "project_id_source": project_id_source,
                "dependency_type": doc.dependency_type,
                "created_by": doc.created_by,
                "creation_timestamp": str(doc.creation_timestamp)
            }
            
            log_debug(f"Successfully created dependency: {result}")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error creating task dependency: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "details": "An unexpected error occurred while creating the task dependency"
            }, ensure_ascii=False) 