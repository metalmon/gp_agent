"""
Tool for analyzing team workload and capacity.
"""

from typing import Dict, Any, Optional
from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...utils.task_analytics import analyze_team_workload as analyze_workload_impl


class AnalyzeTeamWorkloadTool(BaseTaskTool):
    """Tool for analyzing team workload and capacity"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="analyze_team_workload",
            description="Analyze team workload and capacity to identify bottlenecks and resource allocation"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "team_id": {
                    "type": "string",
                    "description": "ID of the team to analyze"
                }
            },
            "required": ["team_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - team_id: Team ID
            settings: Optional settings to customize tool behavior
            
        Returns:
            Dict with workload analysis including:
            - Per-user workload
            - Team capacity
            - Bottlenecks
        """
        team_id = params["team_id"]
        log_debug(f"Analyzing workload for team {team_id}")
        
        try:
            # Get team details
            team = self.api.get_team(team_id)
            if not team:
                return {
                    "error": f"Team {team_id} not found"
                }
            
            # Get workload analysis
            result = analyze_workload_impl(team_id)
            
            # Add team info
            result["team_id"] = team_id
            result["team_name"] = team.get("name", "")
            
            log_debug(
                f"Workload analysis completed for team {team_id}. "
                f"Found {len(result['workloads'])} team members. "
                f"Total assigned hours: {result['team_capacity']['total_assigned_hours']}. "
                f"Bottlenecks: {len(result['team_capacity']['bottlenecks'])}"
            )
            
            return result
            
        except Exception as e:
            log_debug(f"Error analyzing team workload: {str(e)}")
            raise 