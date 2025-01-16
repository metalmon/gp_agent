from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Base message structure
    
    There are three types of messages:
    1. Regular messages (user/assistant) with content and optional tasks/context
    2. Assistant messages with tool calls - can contain multiple tool calls in tool_calls array
    3. Tool response messages - each tool response is a separate message referencing its tool call
    """
    content: Optional[str]
    tasks: List[Dict[str, Any]]
    context: Dict[str, Any]  # user_metadata (author, timestamp, etc) stored here
    role: str  # 'user', 'assistant', or 'tool'
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Multiple tool calls for assistant messages
    tool_name: Optional[str] = None  # Single tool name for tool response message
    tool_call_id: Optional[str] = None  # Reference to specific tool call for tool response message


@dataclass
class SystemContext:
    """System context structure"""
    base_instructions: str
    unassigned_tasks: List[Dict[str, Any]]
    pages: List[Dict[str, Any]]
    related_discussions: List[Dict[str, Any]]
    related_tasks: List[Dict[str, Any]]
    related_pages: List[Dict[str, Any]]
    related_messages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)  # Project/discussion metadata like IDs and titles


class BaseContextBuilder(ABC):
    """Base context builder interface"""
    
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
    
    @abstractmethod
    def build_system_context(self) -> SystemContext:
        """Build system context including base instructions and project context"""
        pass
    
    @abstractmethod
    def build_messages_context(self) -> List[Message]:
        """Build messages context"""
        pass
    
    @abstractmethod
    def build_tool_call_message(
        self,
        tool_calls: List[Dict[str, Any]],
        author: str,
        timestamp: str
    ) -> Message:
        """Build assistant message with tool calls"""
        pass
    
    @abstractmethod
    def build_tool_response_message(
        self,
        content: str,
        tool_name: str,
        tool_call_id: str,
        timestamp: str
    ) -> Message:
        """Build tool response message"""
        pass
    
    def build_tool_instructions(self) -> str:
        """Build instructions for tool usage that go into user message context"""
        return self.settings.get('tools_prompt', '')
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get list of available tools with their basic info"""
        tools = []
        registered_tools = self.settings.get('registered_tools', {})
        
        for tool_name, tool_class in registered_tools.items():
            tool_info = {
                'name': tool_name,
                'description': tool_class.description,
                'parameters': tool_class.parameters
            }
            tools.append(tool_info)
        
        return tools


class BaseContextFormatter(ABC):
    """Base context formatter interface"""
    
    @abstractmethod
    def format_system_context(self, context: SystemContext) -> str:
        """Format system context into string format for API"""
        pass
    
    @abstractmethod
    def format_message(self, message: Message) -> Dict[str, Any]:
        """Format message into API-specific format"""
        pass
    
    @abstractmethod
    def format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format list of messages into API-specific format"""
        pass
        
    @abstractmethod
    def format_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Format tool call into standard format
        
        Args:
            tool_call: Tool call dictionary from API response
            
        Returns:
            Formatted tool call dictionary with name and arguments fields
        """
        pass