"""
API Schema definitions for different LLM providers.
All schemas should follow OpenAI-like interface for compatibility.
"""

from typing import Dict, List, Optional, Union, Any, TypedDict
import json
from .types import ContextData, TokenUsage, ChatCompletionResponse
from .errors import SchemaError
from ..utils.logging import log_debug
from ..context.formatters.openai import OpenAIContextFormatter
from ..context.formatters.anthropic import AnthropicContextFormatter
from ..context.base import Message
import traceback


class TokenUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMSchema:
    """Base class for LLM API schemas"""
    
    def __init__(self):
        self.formatter = None  # Should be initialized in subclasses
    
    def format_request(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Format request data according to schema
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tool definitions
            **kwargs: Additional parameters to pass to API
            
        Returns:
            Formatted request data
            
        Raises:
            SchemaError: If request formatting fails
        """
        raise NotImplementedError
        
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response data according to schema
        
        Args:
            response: Raw response data from API
            
        Returns:
            Parsed response data
            
        Raises:
            SchemaError: If response parsing fails
        """
        raise NotImplementedError
        
    def get_token_usage(self, response_data: Dict[str, Any]) -> Optional[TokenUsage]:
        """Extract token usage from response data
        
        Args:
            response_data: Raw response data from API
            
        Returns:
            TokenUsage if available, None otherwise
            
        Raises:
            SchemaError: If token usage data is malformed
        """
        raise NotImplementedError
        

class OpenAISchema(LLMSchema):
    """OpenAI-compatible API schema (including OpenRouter)"""
    
    def __init__(self):
        super().__init__()
        self.formatter = OpenAIContextFormatter()
    
    def is_raw_response(self, response: Dict[str, Any]) -> bool:
        """Check if this is a raw API response
        
        Args:
            response: Response data to check
            
        Returns:
            True if this is a raw API response, False if already parsed
        """
        return "choices" in response
        
    def extract_message(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message from raw API response
        
        Args:
            response: Raw API response
            
        Returns:
            Extracted message data
        """
        choices = response.get("choices", [{}])
        if not choices:
            return {}
        return choices[0].get("message", {})
        
    def get_finish_reason(self, response: Dict[str, Any]) -> str:
        """Get finish reason from raw API response
        
        Args:
            response: Raw API response
            
        Returns:
            Finish reason string
        """
        choices = response.get("choices", [{}])
        if not choices:
            return ""
        return choices[0].get("finish_reason", "")
        
    def format_request(
        self,
        system_prompt: Dict[str, str] = {}, 
        messages: List[Dict[str, str]] = [],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Format request in OpenAI API format"""
        try:
            # Parse system_prompt if it's a string
            if isinstance(system_prompt, str):
                try:
                    system_prompt = json.loads(system_prompt)
                    #log_debug(f"Parsed system_prompt from string: {json.dumps(system_prompt, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    log_debug(f"Error parsing system_prompt string: {str(e)}")
                    raise SchemaError(f"Invalid system_prompt JSON: {str(e)}")

            # Parse messages if it's a string
            if isinstance(messages, str):
                try:
                    messages = json.loads(messages)
                    #log_debug(f"Parsed messages from string: {json.dumps(messages, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    log_debug(f"Error parsing messages string: {str(e)}")
                    raise SchemaError(f"Invalid messages JSON: {str(e)}")

            # Parse tools if it's a string
            if isinstance(tools, str):
                try:
                    tools = json.loads(tools)
                    #log_debug(f"Parsed tools from string: {json.dumps(tools, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    log_debug(f"Error parsing tools string: {str(e)}")
                    raise SchemaError(f"Invalid tools JSON: {str(e)}")

            # Add system prompt to messages if present
            if system_prompt:
                messages = [system_prompt] + messages
                
            # Convert messages to Message objects
            message_objects = [
                Message(
                    content=msg.get("content"),
                    tasks=[],
                    context={},
                    role=msg.get("role"),
                    tool_calls=msg.get("tool_calls"),
                    tool_name=msg.get("name"),
                    tool_call_id=msg.get("tool_call_id")
                )
                for msg in messages
            ]
            
            # Format messages using the formatter
            formatted_messages = self.formatter.format_to_model_messages(message_objects)
            
            request = {
                "messages": formatted_messages,
                "tools": tools or [],  # Always include tools array
                "tool_choice": "auto"  # Always include tool_choice
            }
            
            # Add non-null kwargs
            for key, value in kwargs.items():
                if value is not None:
                    request[key] = value
                    
            return request
        except Exception as e:
            log_debug(f"Error in format_request: {str(e)}")
            log_debug(f"Traceback: {traceback.format_exc()}")
            raise SchemaError(f"Failed to format request: {str(e)}")
        
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response data according to schema
        
        The response structure from API:
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": str,  # Optional message content
                    "refusal": str,  # Optional refusal reason
                    "tool_calls": List[Dict]  # Optional tool calls
                },
                "finish_reason": str  # Completion status
            }],
            "usage": {  # Token usage data
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int
            }
        }
        
        Returns standardized response format:
        {
            "type": "message" | "refusal" | "tool_call",
            "content": Optional[str],
            "tool_calls": Optional[List[Dict]],
            "refusal": Optional[str],
            "usage": Optional[Dict]  # Preserved token usage data
        }
        """
        # Check for error response first
        if "error" in response:
            error = json.dumps(response["error"], ensure_ascii=False, indent=2)
            log_debug(f"API returned error: {error}")
            raise SchemaError(f"API error: {error}")
            
        # Handle empty response
        choices = response.get("choices", [])
        log_debug(f"Raw API response: {json.dumps(response, ensure_ascii=False, indent=2)}")
        #log_debug(f"Found {len(choices)} choices in response")
        if not choices:
            log_debug("Empty response from API - no choices array")
            raise SchemaError("Empty response from API")
            
        choice = choices[0]
        message = choice.get("message", {})
        #log_debug(f"First choice: {json.dumps(choice, ensure_ascii=False, indent=2)}")
        #log_debug(f"Message from choice: {json.dumps(message, ensure_ascii=False, indent=2)}")
        
        # Check for refusal first - it's a top-level message property
        if message.get("refusal"):
            return {
                "type": "refusal",
                "content": None,
                "tool_calls": None,
                "refusal": message["refusal"],
                "usage": response.get("usage")  # Preserve usage data
            }
        
        # Parse the message content and metadata
        parsed_message = self.formatter.parse_model_response(message)
        finish_reason = choice.get("finish_reason")
        
        # Log parsed message details for debugging
        #log_debug(f"Parsed message: {json.dumps(message, ensure_ascii=False, indent=2)}")
        log_debug(f"Finish reason: {finish_reason}")
        
        # Handle tool calls - either explicit or inferred from finish_reason
        if finish_reason == "tool_calls" or parsed_message.tool_calls:
            tool_calls = parsed_message.tool_calls or []
            return {
                "type": "tool_call",
                "content": parsed_message.content,
                "tool_calls": tool_calls,
                "refusal": None,
                "usage": response.get("usage")  # Preserve usage data
            }
            
        # Regular message response
        return {
            "type": "message",
            "content": parsed_message.content,
            "tool_calls": None,
            "refusal": None,
            "usage": response.get("usage")  # Preserve usage data
        }
        
    def get_token_usage(self, response_data: Dict[str, Any]) -> Optional[TokenUsage]:
        """Extract token usage from response data"""
        usage = response_data.get("usage", {})
        if not usage:
            return None
            
        try:
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            )
        except (KeyError, TypeError) as e:
            raise SchemaError(f"Invalid token usage data: {e}")


class AnthropicSchema(LLMSchema):
    """Anthropic API schema"""
    
    def __init__(self):
        super().__init__()
        self.formatter = AnthropicContextFormatter()
    
    def format_request(
        self,
        system_prompt: Dict[str, str] = {},
        messages: List[Dict[str, str]] = [],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Format request in Anthropic API format"""
        # Add system prompt to messages if present
        if system_prompt:
            messages = [system_prompt] + messages
            
        # Convert messages to Message objects
        message_objects = [
            Message(
                content=msg.get("content"),
                tasks=[],
                context={},
                role=msg.get("role"),
                tool_calls=msg.get("tool_calls"),
                tool_name=msg.get("name"),
                tool_call_id=msg.get("tool_call_id")
            )
            for msg in messages
        ]
        
        # Format messages using the formatter
        formatted_messages = self.formatter.format_to_model_messages(message_objects)
        
        request = {
            "messages": formatted_messages,
            "tools": tools or [],  # Always include tools array
        }
        
        # Add non-null kwargs
        for key, value in kwargs.items():
            if value is not None:
                request[key] = value
                
        return request
        
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response data according to schema
        
        The response structure from API:
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": str,  # Optional message content
                    "refusal": str,  # Optional refusal reason
                    "tool_calls": List[Dict]  # Optional tool calls
                },
                "finish_reason": str  # Completion status
            }]
        }
        
        Or error response:
        {
            "error": {
                "message": str,
                "code": int,
                "metadata": Dict
            }
        }
        
        Returns standardized response format:
        {
            "type": "message" | "refusal" | "tool_call",
            "content": Optional[str],
            "tool_calls": Optional[List[Dict]],
            "refusal": Optional[str]
        }
        
        Raises:
            SchemaError: If response is empty or malformed
        """
        # Check for error response first
        if "error" in response:
            error = json.dumps(response["error"], ensure_ascii=False, indent=2)
            log_debug(f"API returned error: {error}")
            raise SchemaError(f"API error: {error}")
            
        # Handle empty response
        choices = response.get("choices", [])
        log_debug(f"Raw API response: {json.dumps(response, ensure_ascii=False, indent=2)}")
        log_debug(f"Found {len(choices)} choices in response")
        if not choices:
            log_debug("Empty response from API - no choices array")
            raise SchemaError("Empty response from API")
            
        choice = choices[0]
        message = choice.get("message", {})
        log_debug(f"First choice: {json.dumps(choice, ensure_ascii=False, indent=2)}")
        log_debug(f"Message from choice: {json.dumps(message, ensure_ascii=False, indent=2)}")
        
        # Check for refusal first - it's a top-level message property
        if message.get("refusal"):
            return {
                "type": "refusal",
                "content": None,
                "tool_calls": None,
                "refusal": message["refusal"]
            }
        
        # Parse the message content and metadata
        parsed_message = self.formatter.parse_model_response(message)
        finish_reason = choice.get("finish_reason")
        
        # Log parsed message details for debugging
        log_debug(f"Parsed message: {json.dumps(message, ensure_ascii=False, indent=2)}")
        log_debug(f"Finish reason: {finish_reason}")
        
        # Handle tool calls - either explicit or inferred from finish_reason
        if finish_reason == "tool_calls" or parsed_message.tool_calls:
            return {
                "type": "tool_call",
                "content": parsed_message.content,
                "tool_calls": parsed_message.tool_calls
            }
        
        # Handle regular message content
        content = message.get("content")
        if content is None or not content.strip():
            log_debug(f"Empty content in API response. Content: {content}")
            log_debug(f"Tool calls present: {bool(parsed_message.tool_calls)}")
            raise SchemaError("Empty response content from API")
            
        return {
            "type": "message",
            "content": content,
            "tool_calls": None
        }
        
    def get_token_usage(self, response_data: Dict[str, Any]) -> Optional[TokenUsage]:
        """Extract token usage from response data"""
        # Anthropic doesn't provide token usage info
        return None