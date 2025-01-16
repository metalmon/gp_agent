import requests
from typing import Dict, Any, Optional
from .base import BaseLLMClient
from .errors import APIError, SchemaError
from .types import ChatCompletionRequest, ChatCompletionResponse

class AnthropicClient(BaseLLMClient):
    """Client for Anthropic API"""
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """Initialize Anthropic client
        
        Args:
            settings: Settings dictionary with API parameters including:
                - api_schema: API schema name
                - base_url: Base URL for API
                - api_key: API key
                - model: Model name
                - temperature: Temperature parameter
                - max_tokens: Maximum tokens
                - top_p: Top P parameter
                - top_k: Top K parameter
        """
        schema = AnthropicSchema()
        super().__init__(schema=schema, settings=settings)
    
    def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Make a chat completion request to Anthropic API
        
        Args:
            request: Chat completion request data
            
        Returns:
            Chat completion response
            
        Raises:
            APIError: If the API request fails
            SchemaError: If there's an error in schema formatting/parsing
        """
        # Format request using schema
        request_data = self.schema.format_request(request)
        
        # Get API URL
        base_url = self.settings.get('base_url', '').rstrip('/')
        api_url = f"{base_url}/v1/chat/completions"
        
        # Get API key
        api_key = self.settings.get('api_key')
        if not api_key:
            raise APIError("API key not configured")
            
        # Make request
        try:
            response = requests.post(
                api_url,
                json=request_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                    'anthropic-version': '2023-06-01'
                }
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}")
            
        except ValueError as e:
            raise SchemaError(f"Invalid response format: {str(e)}") 