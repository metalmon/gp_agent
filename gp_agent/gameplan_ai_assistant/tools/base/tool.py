"""
Base class for all tools.
Provides a format-agnostic interface for tool definitions and execution.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize tool with name and description
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get tool schema for specific format type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            
        Returns:
            Tool schema in requested format
            
        Raises:
            ValueError: If schema type is not supported
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema in JSON Schema format
        
        Returns:
            Parameter schema as JSON Schema
        """
        pass
    
    @abstractmethod
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters
            settings: Optional settings dictionary with API credentials and other settings
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If execution fails
        """
        pass