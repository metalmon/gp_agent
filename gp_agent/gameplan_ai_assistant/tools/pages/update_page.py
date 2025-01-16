"""
Tool for updating an existing page.
"""

from typing import Dict, Any, Optional
from .base import BasePageTool
from ...utils.logging import log_debug
import json


class UpdatePageTool(BasePageTool):
    """Tool for updating an existing page"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="update_page",
            description="Update an existing page with new content"
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
                    "description": "ID of the page to update"
                },
                "title": {
                    "type": "string",
                    "description": "New title for the page"
                },
                "content": {
                    "type": "string",
                    "description": "New content in markdown format. Supports standard markdown syntax including:\n" +
                                 "- Headers (# ## ###)\n" +
                                 "- Lists (- * 1.)\n" +
                                 "- Code blocks (```language)\n" +
                                 "- Tables (| --- |)\n" +
                                 "- Links and images\n" +
                                 "- Bold, italic, strikethrough\n" +
                                 "- Task lists (- [ ] - [x])"
                }
            },
            "required": ["page_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
            
        Returns:
            Tool execution results
        """
        log_debug(f"Updating page {params['page_id']}")
        log_debug(f"New title: {params.get('title')}")
        log_debug(f"New content length: {len(params['content']) if params.get('content') else 0}")
        
        try:
            # Get current page to check project access
            current = self.api.get_page_content(params["page_id"])
            project_id = current.get("project")
            
            # Convert markdown content to HTML if provided
            html_content = None
            if params.get("content"):
                html_content = self.format_content(params["content"], "html")
                log_debug(f"Converted markdown to HTML: {html_content[:200]}...")
            
            # Update page using API
            page = self.api.update_page(
                page_id=params["page_id"],
                title=params.get("title"),
                content=html_content
            )
            
            # Get project title
            project_title = self.get_project_title(project_id)
            
            # Get current content in markdown
            content = current.get("content", "")
            if content:
                content = self.format_content(content, "markdown")
            
            # Format response
            result = {
                "page_id": params["page_id"],
                "title": page.get("title", ""),
                "content": params.get("content", content),  # Return new content if provided, else current
                "project_id": project_id,
                "project_title": project_title,
                "url": page.get("url", ""),
                "created": str(page.get("created_at", "")),
                "modified": str(page.get("modified_at", "")),
                "updated": True
            }
            
            log_debug(f"Successfully updated page: {result}")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error updating page: {str(e)}")
            return json.dumps({
                "error": f"Failed to update page: {str(e)}",
                "message": "An error occurred while trying to update the page",
                "provided_params": params
            }, ensure_ascii=False) 