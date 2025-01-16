"""
Tool for getting task dependencies.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseTaskTool
from ...utils.logging import log_debug


class GetTaskDependenciesTool(BaseTaskTool):
    """Tool for getting dependencies for a specific task"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_task_dependencies",
            description="Get list of dependencies for a specific task"
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
                    "description": "ID of the task to get dependencies for"
                }
            },
            "required": ["task_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - task_id: Task ID
            settings: Optional settings for tool execution
            
        Returns:
            List of dependencies with their details:
            [
                {
                    "id": str,
                    "task_id": str,
                    "depends_on_task_id": str,
                    "dependency_type": str,
                    "created_at": str,
                    "created_by": str
                }
            ]
        """
        log_debug(f"Getting dependencies for task {params['task_id']}")
        
        try:
            # Get dependencies using GameplanAPI
            dependencies = self.api.get_task_dependencies(
                task_id=params["task_id"]
            )
            
            # Format response
            formatted_dependencies = []
            for dep in dependencies:
                # Get creation timestamp and convert to ISO format if needed
                creation = dep.get("creation")
                if isinstance(creation, datetime):
                    creation = creation.isoformat()
                
                formatted_dep = {
                    "id": dep.get("name", ""),
                    "task_id": dep.get("task", ""),
                    "depends_on_task_id": dep.get("depends_on_task", ""),
                    "dependency_type": dep.get("dependency_type", ""),
                    "created_at": creation,
                    "created_by": dep.get("owner", "")
                }
                formatted_dependencies.append(formatted_dep)
            
            log_debug(f"Found {len(formatted_dependencies)} dependencies")
            return formatted_dependencies
            
        except Exception as e:
            log_debug(f"Error getting task dependencies: {str(e)}")
            raise 