"""
Tool for performing web searches using Google Custom Search API.
Allows searching the web and getting structured results.
"""

import frappe
import requests
from typing import Dict, Any, List
import logging

from .base import BaseWebTool
from ...exceptions import GPAgentException


class WebSearchTool(BaseWebTool):
    """Tool for performing web searches using Google Custom Search API.
    
    This tool enables searching the web using Google's Custom Search API.
    It returns structured results including titles, snippets, and URLs.
    
    Features:
    - Full web search capability through Google's API
    - Configurable number of results (1-10)
    - Returns structured data for each result
    - Handles various search queries including:
        * General web searches
        * Site-specific searches (using site: operator)
        * Phrase searches (using quotes)
        * Complex queries with multiple terms
    """
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="web_search",
            description=(
                "Perform a web search using Google Custom Search API. "
                "Returns structured results including titles, snippets, and URLs. "
                "Supports site-specific searches using 'site:' operator. "
                "Example: 'site:example.com search terms'"
            )
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format with detailed descriptions
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query string. Can include special operators like:\n"
                        "- site:domain.com (limit search to specific domain)\n"
                        "- \"exact phrase\" (search for exact phrase)\n"
                        "- term1 OR term2 (search for either term)\n"
                        "- -term (exclude term)\n"
                        "Example: 'site:frappecrm.ru installation guide'"
                    )
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - query: Search query
                   - num_results: Optional number of results (default: 5)
            settings: Optional settings dict with API credentials
            
        Returns:
            Dict containing search results:
            {
                "query": str,
                "results": List[Dict[str, str]]  # List of results with title, url, snippet
            }
        """
        try:
            # Get API credentials from settings
            if settings:
                # If settings is a dictionary
                api_key = settings.get('google_search_api_key')
                search_engine_id = settings.get('google_search_engine_id')
                
                # If API key is not in the dictionary, try to get it from the settings document
                if not api_key:
                    base_settings = frappe.get_single('GP Agent Settings')
                    api_key = base_settings.get_password('google_search_api_key')
                    search_engine_id = search_engine_id or base_settings.google_search_engine_id
                
                logging.debug(f"Using settings: api_key={bool(api_key)}, search_engine_id={bool(search_engine_id)}")
            else:
                # Get settings from document
                settings = frappe.get_single('GP Agent Settings')
                api_key = settings.get_password('google_search_api_key')
                search_engine_id = settings.google_search_engine_id
                logging.debug(f"Using settings from doc: api_key={bool(api_key)}, search_engine_id={bool(search_engine_id)}")
                
            if not api_key or not search_engine_id:
                raise ValueError("Google Custom Search API credentials not configured")
            
            # Get number of results
            num_results = params.get("num_results", 5)
            
            # Validate num_results
            if not 1 <= num_results <= 10:
                raise GPAgentException("Number of results must be between 1 and 10")
                
            # Make API request
            request_params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': params["query"],
                'num': num_results,
                'fields': 'items(title,link,snippet,displayLink)'  # Only get fields we need
            }
            logging.debug(f"Making Google API request with params: q={params['query']}, num={num_results}")
            
            response = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=request_params
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            logging.debug(f"Google API response status: {response.status_code}")
            logging.debug(f"Google API response data: {data}")
            
            # Format results
            results = []
            if "items" in data:
                logging.debug(f"Found {len(data['items'])} search results")
                for item in data["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("displayLink", "")
                    })
            else:
                logging.debug("No search results found in response")
                logging.debug(f"Response keys: {data.keys()}")
            
            # Return both query and results
            return {
                "query": params["query"],
                "results": results
            }
            
        except requests.exceptions.RequestException as e:
            raise GPAgentException(f"Failed to perform web search: {str(e)}")
        except ValueError as e:
            raise GPAgentException(str(e))
        except Exception as e:
            raise GPAgentException(f"Search failed: {str(e)}") 