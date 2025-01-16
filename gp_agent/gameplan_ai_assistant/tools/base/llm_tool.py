"""
Base class for tools that use LLM capabilities.
This is an abstract base class that defines the interface for all LLM-powered tools.
"""

from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod
from .tool import BaseTool
from ...llm.base import BaseLLMClient


class BaseLLMTool(BaseTool, ABC):
    """Abstract base class for tools that use LLM capabilities"""
    
    def __init__(
        self,
        name: str,
        description: str,
        client_class: Optional[Type[BaseLLMClient]] = None,
        client_settings: Optional[Dict[str, Any]] = None
    ):
        """Initialize tool with name, description and LLM client
        
        Args:
            name: Tool name
            description: Tool description
            client_class: Optional LLM client class to use
            client_settings: Optional settings override for LLM client
        """
        super().__init__(name, description)
        if client_class is None:
            client_class = self.get_default_client_class()
        self.client_class = client_class
        self.llm_client = self.client_class(settings=client_settings)
    
    @abstractmethod
    def get_default_client_class(self) -> Type[BaseLLMClient]:
        """Get default LLM client class for this tool type
        
        Returns:
            Default LLM client class to use
        """
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make a chat completion request using LLM client
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tool definitions
            **kwargs: Additional parameters to override settings
            
        Returns:
            Parsed API response
        """
        pass 