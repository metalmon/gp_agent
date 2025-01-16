from typing import Dict, Any, Optional, List
from .types import ChatCompletionRequest, ChatCompletionResponse, TokenUsage
import json
import frappe
import traceback

class SchemaError(Exception):
    """Exception raised for schema validation and formatting errors"""
    pass

class APIError(Exception):
    """Exception raised for API request errors"""
    pass

class BaseLLMClient:
    """Base class for LLM clients"""
    
    def __init__(self, schema=None, settings: Dict[str, Any] = None):
        """Initialize client with schema and settings
        
        Args:
            schema: Schema for request/response formatting
            settings: Settings dictionary containing all required parameters:
                - api_schema: API schema name (e.g. "OpenAI", "Anthropic")
                - base_url: Base URL for API
                - api_key: API key
                - model: Model name
                - temperature: Temperature parameter
                - max_tokens: Maximum tokens
                - top_p: Top P parameter
                - top_k: Top K parameter
                - context_depth: Context depth setting
                - chat_memory: Chat memory setting
        """
        self.schema = schema
        self.settings = settings or {}
        
    def _validate_input(self, system_prompt, messages, tools):
        """Validate and preprocess input data
        
        Args:
            system_prompt: System prompt data
            messages: List of messages
            tools: List of tools
            
        Returns:
            Tuple of validated (system_prompt, messages, tools)
            
        Raises:
            SchemaError: If validation fails
        """
        try:
            frappe.logger("gameplan").debug("Validating input data:")
            frappe.logger("gameplan").debug(f"system_prompt type: {type(system_prompt)}")
            frappe.logger("gameplan").debug(f"messages type: {type(messages)}")
            frappe.logger("gameplan").debug(f"tools type: {type(tools)}")
            
            # Parse JSON strings if needed
            if isinstance(system_prompt, str):
                try:
                    system_prompt = json.loads(system_prompt)
                    frappe.logger("gameplan").debug("Parsed system_prompt from string")
                except json.JSONDecodeError as e:
                    frappe.logger("gameplan").error(f"Failed to parse system_prompt: {str(e)}")
                    raise SchemaError(f"Invalid system_prompt JSON: {str(e)}")
                    
            if isinstance(messages, str):
                try:
                    messages = json.loads(messages)
                    frappe.logger("gameplan").debug("Parsed messages from string")
                except json.JSONDecodeError as e:
                    frappe.logger("gameplan").error(f"Failed to parse messages: {str(e)}")
                    raise SchemaError(f"Invalid messages JSON: {str(e)}")
                    
            if isinstance(tools, str):
                try:
                    tools = json.loads(tools)
                    frappe.logger("gameplan").debug("Parsed tools from string")
                except json.JSONDecodeError as e:
                    frappe.logger("gameplan").error(f"Failed to parse tools: {str(e)}")
                    raise SchemaError(f"Invalid tools JSON: {str(e)}")
                    
            # Validate types after parsing
            if system_prompt is not None and not isinstance(system_prompt, (dict, list)):
                raise SchemaError(f"system_prompt must be dict or list, got {type(system_prompt)}")
                
            if not isinstance(messages, list):
                raise SchemaError(f"messages must be list, got {type(messages)}")
                
            if tools is not None and not isinstance(tools, list):
                raise SchemaError(f"tools must be list, got {type(tools)}")
                
            return system_prompt, messages, tools
            
        except Exception as e:
            frappe.logger("gameplan").error(f"Error in _validate_input: {str(e)}")
            frappe.logger("gameplan").error(f"Traceback: {traceback.format_exc()}")
            raise
        
    def chat_completion(
        self,
        system_prompt: List[Dict[str, str]] = [],
        messages: List[Dict[str, str]] = [],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make a chat completion request
        
        Args:
            system_prompt: System prompt data
            messages: List of messages
            tools: Optional list of tools
            **kwargs: Additional parameters
            
        Returns:
            Chat completion response
            
        Raises:
            APIError: If the API request fails
            SchemaError: If there's an error in schema formatting/parsing
        """
        try:
            # Log initial state
            frappe.logger("gameplan").debug("Starting chat completion request")
            #frappe.logger("gameplan").debug(f"Initial system_prompt: {system_prompt}")
            #frappe.logger("gameplan").debug(f"Initial messages: {messages}")
            #frappe.logger("gameplan").debug(f"Initial tools: {tools}")
            
            # Validate and preprocess input
            system_prompt, messages, tools = self._validate_input(system_prompt, messages, tools)
            
            # Format request using schema
            try:
                request_data = self.schema.format_request(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools,
                    **kwargs
                )
                frappe.logger("gameplan").debug("Request formatted successfully")
            except Exception as e:
                frappe.logger("gameplan").error(f"Schema format_request failed: {str(e)}")
                frappe.logger("gameplan").error(f"Traceback: {traceback.format_exc()}")
                raise SchemaError(f"Failed to format request: {str(e)}")
                
            # Make API request
            try:
                response = self._make_api_request(request_data)
                frappe.logger("gameplan").debug("API request successful")
            except Exception as e:
                frappe.logger("gameplan").error(f"API request failed: {str(e)}")
                frappe.logger("gameplan").error(f"Traceback: {traceback.format_exc()}")
                raise APIError(f"API request failed: {str(e)}")
                
            # Parse response using schema
            try:
                parsed_response = self.schema.parse_response(response)
                frappe.logger("gameplan").debug("Response parsed successfully")
                return parsed_response
            except Exception as e:
                frappe.logger("gameplan").error(f"Schema parse_response failed: {str(e)}")
                frappe.logger("gameplan").error(f"Traceback: {traceback.format_exc()}")
                raise SchemaError(f"Failed to parse response: {str(e)}")
                
        except Exception as e:
            frappe.logger("gameplan").error(f"Unhandled error in chat_completion: {str(e)}")
            frappe.logger("gameplan").error(f"Traceback: {traceback.format_exc()}")
            raise
            
    def _make_api_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make the actual API request
        
        Args:
            request_data: Formatted request data
            
        Returns:
            Raw API response
            
        Raises:
            APIError: If the request fails
        """
        raise NotImplementedError
        
    def get_token_usage(self, response_data: Dict[str, Any]) -> Optional[TokenUsage]:
        """Extract token usage from response data
        
        Args:
            response_data: Raw response data from API
            
        Returns:
            TokenUsage if available, None otherwise
        """
        return self.schema.get_token_usage(response_data) 