"""
Tool for listing pages in a project.
"""

from typing import Dict, Any, Optional, List
from .base import BasePageTool
from ...utils.logging import log_debug
import json


class GetPagesListTool(BasePageTool):
    """Tool for listing pages in a project"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_pages_list",
            description="List pages in a project"
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
                    "description": "ID of the project to list pages from"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of pages to return (default: 10)",
                    "default": 10,
                    "minimum": 1
                }
            },
            "required": ["project_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - project_id: Project ID
                   - limit: Maximum number of pages to return (optional)
            settings: Optional settings for tool execution
            
        Returns:
            Dict containing:
            - project_id: Project ID
            - project_title: Project title
            - pages: List of pages with metadata
            - total_count: Total number of pages
        """
        log_debug(f"Listing pages for project {params['project_id']}")
        
        try:
            # Get pages from API
            pages = self.api.list_pages(
                project_id=params["project_id"],
                limit=params.get("limit", 10)
            )
            
            # Get project title
            project_title = self.get_project_title(params["project_id"])
            
            # Format response
            result = {
                "project_id": params["project_id"],
                "project_title": project_title,
                "pages": {
                    "result": [{
                        "id": page["id"],
                        "title": page["title"],
                        "project": page["project"],
                        "owner": page["owner"],
                        "user": page["user"],
                        "modified": page["modified"],
                        "creation": page["creation"]
                    } for page in pages]
                },
                "total_count": len(pages)
            }
            
            log_debug(f"Found {len(pages)} pages")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error listing pages: {str(e)}")
            raise 