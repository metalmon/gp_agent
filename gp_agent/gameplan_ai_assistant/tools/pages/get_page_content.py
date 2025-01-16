"""
Tool for getting page content.
"""

from typing import Dict, Any, Optional
from .base import BasePageTool
from ...utils.logging import log_debug
import json


class GetPageContentTool(BasePageTool):
    """Tool for getting page content"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_page_content",
            description="Get content of a specific page"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "ID of the page to get content from"
                },
                "format": {
                    "type": "string",
                    "description": "Content format ('html' or 'markdown')",
                    "enum": ["html", "markdown"],
                    "default": "markdown"
                }
            },
            "required": ["page_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - page_id: Page ID
                   - format: Content format (html/markdown)
            settings: Optional settings for tool execution
            
        Returns:
            Page content and metadata or error details if something goes wrong
        """
        log_debug(f"Getting content for page {params['page_id']}")
        log_debug(f"Requested format: {params.get('format', 'markdown')}")
        
        try:
            # Get page from API
            page = self.api.get_page_content(params["page_id"])
            
            # Get project title
            project_id = page.get("project")
            project_title = self.get_project_title(project_id)
            
            # Format content
            content = page.get("content", "")
            if content:
                content = self.format_content(
                    content,
                    params.get("format", "markdown")
                )
            
            # Format response
            result = {
                "page_id": params["page_id"],
                "title": page.get("title", ""),
                "content": content,
                "project_id": project_id,
                "project_title": project_title,
                "url": page.get("url", ""),
                "created": str(page.get("created_at", "")),
                "modified": str(page.get("modified_at", ""))
            }
            
            log_debug(f"Successfully got page content: {result}")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error getting page content: {str(e)}")
            return json.dumps({
                "error": f"Failed to get page content: {str(e)}",
                "message": "An error occurred while trying to get the page content",
                "provided_params": params
            }, ensure_ascii=False) 