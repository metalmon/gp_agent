from typing import Dict, List, Optional, Any
import frappe
from frappe.exceptions import ValidationError
import requests
from .base import BaseLLMClient
from .schema import OpenAISchema
from .schema import TokenUsage
from ..utils.logging import log_debug
import json
from ..llm.errors import APIError

class OpenAIClient(BaseLLMClient):
    """Client for making LLM API calls using OpenAI-compatible API (including OpenRouter)"""
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI client
        
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
        schema = OpenAISchema()
        super().__init__(schema=schema, settings=settings)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        headers = {
            "Authorization": f"Bearer {self.settings.get('api_key')}",
            "HTTP-Referer": frappe.utils.get_url(),
            "Content-Type": "application/json"
        }
        
        # Add OpenRouter specific headers
        if self.settings.get('base_url', '').startswith("https://openrouter.ai/"):
            headers.update({
                "HTTP-Referer": frappe.utils.get_url(),  # OpenRouter requires this
                "X-Title": "Gameplan AI Assistant",  # Name of your application
            })
            
        return headers
    
    def _make_api_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to OpenAI-compatible endpoint
        
        Args:
            request_data: Formatted request data
            
        Returns:
            Raw API response
            
        Raises:
            APIError: If the request fails
        """
        try:
            # Get base URL and construct endpoint
            base_url = self.settings.get('base_url', '').rstrip('/')
            if base_url == "https://openrouter.ai":
                url = f"{base_url}/api/v1/chat/completions"
            else:
                url = f"{base_url}/chat/completions"
                
            # Log request details
            frappe.logger("gameplan").debug(f"Making request to: {url}")
            
            # Make request
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=request_data
            )
            
            # Log response details
            frappe.logger("gameplan").debug(f"Response status: {response.status_code}")
            frappe.logger("gameplan").debug(f"Response headers: {response.headers}")
            frappe.logger("gameplan").debug(f"Response text: {response.text}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                frappe.logger("gameplan").error(f"Failed to parse response JSON: {str(e)}")
                frappe.logger("gameplan").error(f"Response text: {response.text}")
                raise APIError(f"Invalid JSON response: {str(e)}")
                
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_message = "Tools not supported by the model"
                elif e.response.status_code == 429:
                    error_message = "Rate limit exceeded"
                elif e.response.status_code == 402:
                    error_message = "Payment required: Insufficient credits"
                else:
                    # Try to get more details from response
                    try:
                        response_json = e.response.json()
                        if 'error' in response_json:
                            error_message = f"{e.response.status_code} {e.response.reason}: {response_json['error'].get('message', str(response_json['error']))}"
                        else:
                            error_message = f"{e.response.status_code} {e.response.reason}: {str(response_json)}"
                    except:
                        error_message = f"{e.response.status_code} {e.response.reason}: {e.response.text}"
            raise APIError(error_message) from e
            
    def get_token_usage(self, response_data: Dict[str, Any]) -> Optional[TokenUsage]:
        """Extract token usage from response data
        
        Args:
            response_data: Parsed response data from API
            
        Returns:
            TokenUsage if available, None otherwise
        """
        try:
            # Get usage data either from raw response or parsed response
            usage = response_data.get('usage')
            if usage:
                log_debug(f"Found token usage in response: {json.dumps(usage, ensure_ascii=False)}")
                return TokenUsage(
                    prompt_tokens=usage.get('prompt_tokens', 0),
                    completion_tokens=usage.get('completion_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0)
                )
            log_debug("No token usage data found in response")
            return None
        except Exception as e:
            log_debug(f"Error extracting token usage: {str(e)}")
            return None