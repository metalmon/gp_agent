"""
Base class for web-related tools.
"""

import frappe
import json
from typing import Dict, Any, Optional
from ..base.tool import BaseTool


class BaseWebTool(BaseTool):
    """Base class for web-related tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize tool
        
        Args:
            name: Tool name
            description: Tool description
        """
        super().__init__(name=name, description=description)
        
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get tool schema for specific format type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            
        Returns:
            Tool schema in requested format
            
        Raises:
            ValueError: If schema type is not supported
        """
        if schema_type not in ["OpenAI", "Anthropic"]:
            raise ValueError(f"Unsupported schema type: {schema_type}")
            
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
        else:  # Anthropic
            return {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
                "returns": {
                    "type": "object",
                    "description": "Tool execution results"
                }
            }
            
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
            ValueError: If schema type is not supported or parsing fails
        """
        if schema_type not in ["OpenAI", "Anthropic"]:
            raise ValueError(f"Unsupported schema type: {schema_type}")
            
        try:
            if schema_type == "OpenAI":
                return json.loads(call_data["function"]["arguments"])
            else:  # Anthropic
                return call_data["parameters"]
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse {schema_type} call data: {str(e)}") 