"""
Tool for predicting completion dates for project tasks.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...utils.task_analytics import predict_completion_dates as predict_dates_impl


class PredictCompletionDatesTool(BaseTaskTool):
    """Tool for predicting completion dates for project tasks"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="predict_completion_dates",
            description="Predict completion dates for project tasks based on historical data and dependencies"
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
            Dict with completion predictions including:
            - Predicted dates for each task
            - Confidence levels
            - Risk assessment
        """
        project_id = params["project_id"]
        log_debug(f"Predicting completion dates for project {project_id}")
        
        try:
            # Get project details
            project = self.api.get_project(project_id)
            if not project:
                return {
                    "error": f"Project {project_id} not found"
                }
            
            # Get completion date predictions
            result = predict_dates_impl(project_id)
            
            # Add project info
            result["project_id"] = project_id
            result["project_title"] = project.get("title", "")
            
            log_debug(
                f"Completion date predictions completed for project {project_id}. "
                f"Analyzed {len(result.get('task_predictions', []))} tasks."
            )
            
            return result
            
        except Exception as e:
            log_debug(f"Error predicting completion dates: {str(e)}")
            raise 