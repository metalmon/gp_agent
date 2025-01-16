"""
Tool for creating a new page in a project.
"""

from typing import Dict, Any, Optional
import re
from .base import BasePageTool
from ...utils.logging import log_debug
import json


class CreatePageTool(BasePageTool):
    """Tool for creating a new page in a project"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="create_page",
            description="Create a new page in a project with markdown content"
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
                    "description": "ID of the project where to create the page"
                },
                "title": {
                    "type": "string",
                    "description": "Title of the new page"
                },
                "content": {
                    "type": "string",
                    "description": "Content in markdown format. Supports standard markdown syntax including:\n" +
                                 "- Headers (# ## ###)\n" +
                                 "- Lists (- * 1.)\n" +
                                 "- Code blocks (```language)\n" +
                                 "- Tables (| --- |)\n" +
                                 "- Links and images\n" +
                                 "- Bold, italic, strikethrough\n" +
                                 "- Task lists (- [ ] - [x])"
                }
            },
            "required": ["project_id", "title", "content"]
        }

    def clean_duplicate_title(self, title: str, content: str) -> str:
        """Remove duplicate title from content if it appears at the start
        
        Handles different markdown title formats:
        - # Title
        - ## Title
        - ### Title
        - **Title**
        - __Title__
        
        Args:
            title: Page title
            content: Page content
            
        Returns:
            Content with duplicate title removed if found at start
        """
        # Clean up title for comparison
        clean_title = title.strip().lower()
        
        # Different markdown patterns for titles
        title_patterns = [
            # Headers
            rf"^#\s*{re.escape(clean_title)}[\n\r]+",
            rf"^##\s*{re.escape(clean_title)}[\n\r]+",
            rf"^###\s*{re.escape(clean_title)}[\n\r]+",
            # Bold
            rf"^\*\*{re.escape(clean_title)}\*\*[\n\r]+",
            rf"^__{re.escape(clean_title)}__[\n\r]+"
        ]
        
        # Try each pattern
        content_lower = content.lower()
        for pattern in title_patterns:
            if re.match(pattern, content_lower):
                # Remove the title from original content (preserving case)
                content = re.sub(rf"^.*?[\n\r]+", "", content, count=1, flags=re.IGNORECASE)
                log_debug(f"Removed duplicate title matching pattern: {pattern}")
                break
                
        return content.strip()
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool
        
        Args:
            params: Tool parameters
            settings: Optional settings for tool execution
            
        Returns:
            Tool execution results
        """
        log_debug(f"Creating page '{params['title']}' in project {params['project_id']}")
        
        try:
            # Clean content
            content = self.clean_duplicate_title(params["title"], params["content"])
            
            # Convert markdown content to HTML
            html_content = self.format_content(content, "html")
            log_debug(f"Converted markdown to HTML: {html_content[:200]}...")
            
            # Create page using API
            page = self.api.create_page(
                project_id=params["project_id"],
                title=params["title"],
                content=html_content
            )
            
            log_debug(f"Created page {page.get('id')} in project '{self.get_project_title(params['project_id'])}' (project_id={params['project_id']})")
            
            # Get project title
            project_title = self.get_project_title(params["project_id"])
            
            # Format response
            result = {
                "project_id": params["project_id"],
                "project_title": project_title,
                "page_id": str(page.get("id", "")),  # Use id instead of name
                "title": page.get("title", ""),
                "content": content,  # Return cleaned markdown
                "url": page.get("url", ""),
                "created": str(page.get("created_at", "")),
                "modified": str(page.get("modified_at", ""))
            }
            
            log_debug(f"Successfully created page: {result}")
            # Ensure result is JSON serializable
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            log_debug(f"Error creating page: {str(e)}")
            return json.dumps({
                "error": f"Failed to create page: {str(e)}",
                "message": "An error occurred while trying to create the page",
                "provided_params": params
            }, ensure_ascii=False) 