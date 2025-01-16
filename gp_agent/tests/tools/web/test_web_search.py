"""
Tests for the WebSearchTool class.
"""

import unittest
from unittest.mock import patch, MagicMock
import frappe
import requests

from gp_agent.gameplan_ai_assistant.tools.web.web_search import WebSearchTool
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException


class TestWebSearchTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.tool = WebSearchTool()
        self.test_query = "test search query"
        
        # Mock search results
        self.mock_results = {
            "items": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "This is a test result snippet 1",
                    "displayLink": "example.com"
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "This is a test result snippet 2",
                    "displayLink": "example.com"
                }
            ]
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "web_search")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("query", params["required"])
        self.assertEqual(len(params["required"]), 1)
        
        # Test parameter properties
        properties = params["properties"]
        self.assertIn("query", properties)
        self.assertIn("num_results", properties)
        
        # Test num_results constraints
        num_results = properties["num_results"]
        self.assertEqual(num_results["type"], "integer")
        self.assertEqual(num_results["default"], 5)
        self.assertEqual(num_results["minimum"], 1)
        self.assertEqual(num_results["maximum"], 10)

    @patch('frappe.get_single')
    async def test_web_search_success(self, mock_get_single):
        """Test successful web search"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.get_password.return_value = "test_api_key"
        mock_settings.google_search_engine_id = "test_engine_id"
        mock_get_single.return_value = mock_settings
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "Test snippet 1",
                    "displayLink": "example.com"
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "Test snippet 2",
                    "displayLink": "example.com"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        # Create tool
        tool = WebSearchTool()
        
        # Execute search
        with patch('requests.get', return_value=mock_response):
            results = await tool.execute(
                params={"query": "test query", "num_results": 2},
                settings={
                    "google_api_key": "test_api_key",
                    "google_search_engine_id": "test_engine_id"
                }
            )
        
        # Verify results
        assert len(results) == 2
        assert results[0]["title"] == "Test Result 1"
        assert results[0]["link"] == "https://example.com/1"
        assert results[0]["snippet"] == "Test snippet 1"
        assert results[0]["source"] == "example.com"
        
    @patch('frappe.get_single')
    async def test_web_search_no_results(self, mock_get_single):
        """Test web search with no results"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.get_password.return_value = "test_api_key"
        mock_settings.google_search_engine_id = "test_engine_id"
        mock_get_single.return_value = mock_settings
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No items
        mock_response.raise_for_status.return_value = None
        
        # Create tool
        tool = WebSearchTool()
        
        # Execute search
        with patch('requests.get', return_value=mock_response):
            results = await tool.execute(
                params={"query": "test query"},
                settings={
                    "google_api_key": "test_api_key",
                    "google_search_engine_id": "test_engine_id"
                }
            )
        
        # Verify empty results
        assert len(results) == 0
        
    @patch('frappe.get_single')
    async def test_web_search_missing_credentials(self, mock_get_single):
        """Test web search with missing credentials"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.get_password.return_value = None
        mock_settings.google_search_engine_id = None
        mock_get_single.return_value = mock_settings
        
        # Create tool
        tool = WebSearchTool()
        
        # Execute search and verify error
        with pytest.raises(GPAgentException, match="Google Custom Search API credentials not configured"):
            await tool.execute(
                params={"query": "test query"},
                settings={}
            )
        
    @patch('frappe.get_single')
    async def test_web_search_api_error(self, mock_get_single):
        """Test web search with API error"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.get_password.return_value = "test_api_key"
        mock_settings.google_search_engine_id = "test_engine_id"
        mock_get_single.return_value = mock_settings
        
        # Create tool
        tool = WebSearchTool()
        
        # Execute search with mocked API error
        with patch('requests.get', side_effect=requests.exceptions.RequestException("API Error")):
            with pytest.raises(GPAgentException, match="Failed to perform web search: API Error"):
                await tool.execute(
                    params={"query": "test query"},
                    settings={
                        "google_api_key": "test_api_key",
                        "google_search_engine_id": "test_engine_id"
                    }
                )

    async def test_web_search_invalid_num_results(self):
        """Test web search with invalid number of results"""
        # Test with too low value
        with self.assertRaises(GPAgentException) as context:
            await self.tool.execute({
                "query": self.test_query,
                "num_results": 0
            })
        self.assertIn("must be between 1 and 10", str(context.exception))
        
        # Test with too high value
        with self.assertRaises(GPAgentException) as context:
            await self.tool.execute({
                "query": self.test_query,
                "num_results": 11
            })
        self.assertIn("must be between 1 and 10", str(context.exception)) 