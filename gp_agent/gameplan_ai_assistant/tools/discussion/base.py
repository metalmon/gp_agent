"""
Base class for discussion-related tools.
"""

import frappe
import json
from typing import Dict, Any, Optional
from ...gameplan_api import GameplanAPI
from ..base.tool import BaseTool


class BaseDiscussionTool(BaseTool):
    """Base class for discussion-related tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize tool
        
        Args:
            name: Tool name
            description: Tool description
        """
        super().__init__(name=name, description=description)
        self._api: Optional[GameplanAPI] = None
        
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get tool schema for specific format type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            
        Returns:
            Tool schema in requested format
            
        Raises:
            ValueError: If schema type is not supported
        """
        parameters = self.get_parameters()
        
        if schema_type == "OpenAI":
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": parameters
                }
            }
        elif schema_type == "Anthropic":
            return {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
                "returns": {
                    "type": "object",
                    "description": "Tool execution results"
                }
            }
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")
            
    def parse_call(
        self,
        schema_type: str,
        call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse tool call data based on schema type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            call_data: Raw tool call data to parse
            
        Returns:
            Parsed parameters for tool execution
            
        Raises:
            ValueError: If schema type is not supported
        """
        if schema_type == "OpenAI":
            return json.loads(call_data["function"]["arguments"])
        elif schema_type == "Anthropic":
            return call_data["parameters"]
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")
        
    @property
    def api(self) -> GameplanAPI:
        """Get or create GameplanAPI instance"""
        if not self._api:
            self._api = GameplanAPI()
        return self._api
        
    def validate_access(self, discussion_id: str, permission_type: str = "read") -> None:
        """Validate user has access to the discussion
        
        Args:
            discussion_id: ID of the discussion
            permission_type: Type of permission to check (read/write)
        
        Raises:
            frappe.PermissionError: If user doesn't have required permission
        """
        # Get discussion's project
        discussion = frappe.get_doc("GP Discussion", discussion_id)
        project = frappe.get_doc("GP Project", discussion.project)
        
        # Check permission
        if not project.has_permission(permission_type):
            frappe.throw(
                f"You don't have {permission_type} permission for project {project.name}",
                frappe.PermissionError
            )
            
    def format_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """Format a comment for API response
        
        Args:
            comment: Raw comment data from Gameplan
            
        Returns:
            Formatted comment data
        """
        return {
            "id": comment.name,
            "author": comment.owner,
            "timestamp": str(comment.creation),
            "content": comment.content
        } 