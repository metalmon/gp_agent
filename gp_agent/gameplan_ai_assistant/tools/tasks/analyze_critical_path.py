"""
Tool for analyzing critical path in project tasks.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...utils.task_analytics import analyze_critical_path as analyze_critical_path_impl
import json


class AnalyzeCriticalPathTool(BaseTaskTool):
    """Tool for analyzing critical path in project tasks"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="analyze_critical_path",
            description="Analyze critical path for project tasks to identify bottlenecks and dependencies"
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
                    "description": "ID of the project to analyze"
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
            Dict with critical path analysis including:
            - List of tasks in critical path
            - Total estimated duration
            - Earliest possible completion date
            - Risk factors
        """
        project_id = params["project_id"]
        log_debug(f"Analyzing critical path for project {project_id}")
        
        try:
            # Get project details
            project = self.api.get_project(project_id)
            if not project:
                return {
                    "error": f"Project {project_id} not found"
                }
            
            # Get critical path analysis
            result = analyze_critical_path_impl(project_id)
            
            # Add project info
            result["project_id"] = project_id
            result["project_title"] = project.get("title", "")
            
            log_debug(
                f"Critical path analysis completed for project {project_id}. "
                f"Found {len(result['critical_path'])} tasks in critical path. "
                f"Total duration: {result['total_duration_hours']} hours. "
                f"Estimated completion: {result['estimated_completion_date']}"
            )
            
            return result
            
        except Exception as e:
            log_debug(f"Error analyzing critical path: {str(e)}")
            raise 