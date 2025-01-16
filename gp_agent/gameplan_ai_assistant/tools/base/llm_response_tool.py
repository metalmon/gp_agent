"""
Base class for tools that use LLM to process their results.
Extends OpenAITool with natural language response generation.
"""

from typing import Dict, Any, Optional, List
from .openai_tool import OpenAITool


class LLMResponseTool(OpenAITool):
    """Base class for tools that use LLM to generate natural language responses"""
    
    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Initialize tool with name, description and optional system prompt
        
        Args:
            name: Tool name
            description: Tool description
            system_prompt: Optional system prompt for response generation
            **kwargs: Additional arguments for OpenAITool
        """
        super().__init__(name, description, **kwargs)
        self.system_prompt = system_prompt or "You are a helpful assistant. Generate a natural language response."
    
    def process_result(
        self,
        result: Dict[str, Any],
        format_prompt: str
    ) -> Dict[str, Any]:
        """Process raw result using LLM to generate natural description
        
        Args:
            result: Raw result data from tool execution
            format_prompt: Prompt template for formatting the result
            
        Returns:
            Result with added natural language description
        """
        messages = [{
            "role": "system",
            "content": self.system_prompt
        }, {
            "role": "user",
            "content": format_prompt.format(**result)
        }]
        
        response = self.chat_completion(messages)
        
        return {
            **result,
            "description": response["content"]
        } 