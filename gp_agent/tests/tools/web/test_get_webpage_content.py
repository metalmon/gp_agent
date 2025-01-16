"""
Tests for the GetWebpageContentTool class.
"""

import unittest
from unittest.mock import patch, MagicMock
import frappe
import requests
from bs4 import BeautifulSoup

from gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content import GetWebpageContentTool
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException


class TestGetWebpageContentTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.tool = GetWebpageContentTool()
        self.test_url = "https://example.com/test"
        
        # Mock HTML content
        self.mock_html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
                <meta property="og:title" content="OG Test Title">
            </head>
            <body>
                <main>
                    <h1>Main Content</h1>
                    <p>This is the main content of the page.</p>
                    <div class="sidebar">Sidebar content</div>
                    <script>alert('test');</script>
                </main>
            </body>
        </html>
        """

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_webpage_content")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("url", params["required"])
        self.assertEqual(len(params["required"]), 1)
        
        # Test parameter properties
        properties = params["properties"]
        self.assertIn("url", properties)
        self.assertEqual(properties["url"]["type"], "string")

    @patch('gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content.requests')
    async def test_get_webpage_content_success(self, mock_requests):
        """Test successful webpage content retrieval"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.mock_html
        mock_response.encoding = 'utf-8'
        mock_response.url = self.test_url
        mock_requests.Session.return_value.get.return_value = mock_response
        
        # Execute tool
        result = await self.tool.execute({"url": self.test_url})
        
        # Verify results
        self.assertEqual(result["url"], self.test_url)
        self.assertEqual(result["final_url"], self.test_url)
        self.assertEqual(result["title"], "Test Page")
        self.assertIn("Main Content", result["content"])
        self.assertIn("main content of the page", result["content"])
        self.assertNotIn("Sidebar content", result["content"])
        self.assertNotIn("alert('test')", result["content"])
        
        # Verify metadata
        self.assertIn("description", result["metadata"])
        self.assertEqual(result["metadata"]["description"], "Test description")
        self.assertEqual(result["metadata"]["og_title"], "OG Test Title")

    @patch('gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content.requests')
    async def test_get_webpage_content_invalid_url(self, mock_requests):
        """Test webpage content retrieval with invalid URL"""
        # Execute tool with invalid URL
        result = await self.tool.execute({"url": "invalid-url"})
        
        # Verify error
        self.assertIn("error", result)
        self.assertIn("Invalid URL format", result["error"])
        
        # Verify no requests were made
        mock_requests.Session.return_value.get.assert_not_called()

    @patch('gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content.requests')
    async def test_get_webpage_content_request_error(self, mock_requests):
        """Test webpage content retrieval with request error"""
        # Setup mock to raise error
        mock_requests.Session.return_value.get.side_effect = requests.RequestException("Network error")
        
        # Execute tool
        result = await self.tool.execute({"url": self.test_url})
        
        # Verify error
        self.assertIn("error", result)
        self.assertIn("Network error", result["error"])

    @patch('gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content.frappe')
    async def test_get_frappe_content_success(self, mock_frappe):
        """Test successful Frappe document content retrieval"""
        # Setup mock document
        mock_doc = MagicMock()
        mock_doc.doctype = "Test DocType"
        mock_doc.name = "TEST001"
        mock_doc.owner = "test@example.com"
        mock_doc.creation = "2023-01-01 12:00:00"
        mock_doc.modified = "2023-01-01 13:00:00"
        mock_doc.modified_by = "test@example.com"
        mock_doc.get_title.return_value = "Test Document"
        mock_doc.content = "Test document content"
        mock_doc.meta.istable = False
        
        mock_frappe.get_doc.return_value = mock_doc
        
        # Execute tool with Frappe URL
        result = await self.tool.execute({"url": "/app/test-doctype/TEST001"})
        
        # Verify results
        self.assertNotIn("error", result)
        self.assertEqual(result["title"], "Test Document")
        self.assertIn("Test document content", result["content"])
        
        # Verify metadata
        self.assertEqual(result["metadata"]["doctype"], "Test DocType")
        self.assertEqual(result["metadata"]["name"], "TEST001")
        self.assertEqual(result["metadata"]["owner"], "test@example.com")

    @patch('gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content.frappe')
    async def test_get_frappe_content_not_found(self, mock_frappe):
        """Test Frappe document content retrieval with non-existent document"""
        # Setup mock to raise DoesNotExistError
        mock_frappe.get_doc.side_effect = frappe.DoesNotExistError()
        
        # Execute tool
        result = await self.tool.execute({"url": "/app/test-doctype/NONEXISTENT"})
        
        # Verify error
        self.assertIn("error", result)
        self.assertIn("not found", result["error"])

    def test_clean_markdown(self):
        """Test markdown cleaning functionality"""
        # Test input with various formatting issues
        markdown = """
# Heading 1


* List item 1
*  List item 2

[Link] (https://example.com)

> Quote
>  With multiple lines

```
Code block
```
        """
        
        # Clean markdown
        cleaned = self.tool._clean_markdown(markdown)
        
        # Verify cleaning results
        self.assertNotIn("\n\n\n", cleaned)  # No triple newlines
        self.assertIn("* List item 1", cleaned)  # Proper list formatting
        self.assertIn("[Link](https://example.com)", cleaned)  # Fixed link spacing
        self.assertIn("> Quote", cleaned)  # Proper quote formatting
        self.assertIn("```Code block```", cleaned)  # Code block formatting 