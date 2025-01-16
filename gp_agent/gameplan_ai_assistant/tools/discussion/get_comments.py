"""
Tool for getting comments from a discussion.
"""

from typing import Dict, List, Optional, Any
from .base import BaseDiscussionTool


class GetCommentsDiscussionTool(BaseDiscussionTool):
    """Tool for getting comments from a discussion"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_discussion_comments",
            description="Get comments from a discussion with optional filtering by time"
        )
    
    def get_parameters(self) -> Dict:
        """Get tool parameters schema"""
        return {
            "type": "object",
            "properties": {
                "discussion_id": {
                    "type": "string",
                    "description": "ID of the discussion"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of comments to return",
                    "default": 10
                },
                "before_id": {
                    "type": "string",
                    "description": "Get comments before this comment ID (optional)"
                },
                "after_id": {
                    "type": "string",
                    "description": "Get comments after this comment ID (optional)"
                }
            },
            "required": ["discussion_id"]
        }
        
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict]]:
        """Execute the tool
        
        Args:
            params: Tool parameters
                discussion_id: ID of the discussion
                limit: Maximum number of comments to return (default: 10)
                before_id: Get comments before this comment ID (optional)
                after_id: Get comments after this comment ID (optional)
            settings: Optional settings for tool execution
        
        Returns:
            Dictionary with list of comments:
            {
                "messages": [
                    {
                        "id": str,
                        "author": str,
                        "timestamp": str,
                        "content": str
                    }
                ]
            }
        """
        # Validate access
        self.validate_access(params["discussion_id"])
        
        # Get parameters
        limit = params.get("limit", 10)
        before_id = params.get("before_id")
        after_id = params.get("after_id")
        
        # Get comments using GameplanAPI
        comments = self.api.get_discussion_comments(
            discussion_id=params["discussion_id"],
            limit=limit
        )
        
        # Filter comments if before_id or after_id is specified
        if before_id or after_id:
            # Get creation times once
            before_time = self.api.get_comment_creation_time(before_id) if before_id else None
            after_time = self.api.get_comment_creation_time(after_id) if after_id else None
            
            filtered_comments = []
            for comment in comments:
                if before_time and comment.creation >= before_time:
                    continue
                if after_time and comment.creation <= after_time:
                    continue
                filtered_comments.append(comment)
            comments = filtered_comments
        
        # Format comments
        formatted_comments = [self.format_comment(comment) for comment in comments]
        
        return {"messages": formatted_comments} 