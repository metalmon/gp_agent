"""
OpenAI-compatible tool implementation.
Extends BaseLLMTool with OpenAI-specific functionality.
"""

from typing import Dict, Any, Optional, List, Type
import json
from .llm_tool import BaseLLMTool
from ...llm.base import BaseLLMClient
from ...llm.openai import OpenAIClient


class OpenAITool(BaseLLMTool):
    """Base class for tools that use OpenAI-compatible LLM capabilities"""
    
    def get_default_client_class(self) -> Type[BaseLLMClient]:
        """Get default LLM client class for OpenAI tools
        
        Returns:
            OpenAIClient class
        """
        return OpenAIClient
    
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get tool schema for specific format type
        
        Args:
            schema_type: Schema format type (must be "OpenAI")
            
        Returns:
            Tool schema in OpenAI format
            
        Raises:
            ValueError: If schema type is not "OpenAI"
        """
        if schema_type != "OpenAI":
            raise ValueError(f"OpenAITool only supports OpenAI schema type, got {schema_type}")
            
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters()
            }
        }
    
    def parse_call(
        self,
        schema_type: str,
        call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse tool call data based on schema type
        
        Args:
            schema_type: Schema format type (must be "OpenAI")
            call_data: Raw tool call data to parse
            
        Returns:
            Parsed parameters for tool execution
            
        Raises:
            ValueError: If schema type is not "OpenAI"
        """
        if schema_type != "OpenAI":
            raise ValueError(f"OpenAITool only supports OpenAI schema type, got {schema_type}")
            
        return json.loads(call_data["function"]["arguments"])
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make a chat completion request using OpenAI-compatible LLM client
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tool definitions
            **kwargs: Additional parameters to override settings
            
        Returns:
            Parsed API response
        """
        return self.llm_client.chat_completion(
            messages=messages,
            tools=tools,
            **kwargs
        ) 