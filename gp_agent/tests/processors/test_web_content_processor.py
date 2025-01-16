import unittest
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.processors.web_content_processor import WebContentProcessor
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException

class TestWebContentProcessor(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.test_urls = [
            "https://example.com/1",
            "https://example.com/2",
            "http://localhost:8000/app/1"
        ]
        
        self.mock_web_content = {
            "url": "https://example.com/1",
            "title": "Test Page",
            "content": "Test content",
            "metadata": {}
        }
    
    @patch('gp_agent.gameplan_ai_assistant.processors.web_content_processor.get_webpage_content')
    def test_process_web_urls(self, mock_get_content):
        """Test processing web URLs"""
        # Setup mock
        mock_get_content.return_value = self.mock_web_content
        
        # Process URLs
        result = WebContentProcessor.process_urls(self.test_urls)
        
        # Check structure
        self.assertIn('successful_results', result)
        self.assertIn('failed_urls', result)
        self.assertIn('stats', result)
        
        # Check stats
        self.assertEqual(result['stats']['total_urls'], 3)
        self.assertGreater(result['stats']['successful'], 0)
        
        # Verify mock was called
        self.assertTrue(mock_get_content.called)
    
    def test_process_invalid_urls(self):
        """Test processing invalid URLs"""
        invalid_urls = [
            "not_a_url",
            "http://invalid.",
            "ftp://unsupported.com"
        ]
        
        with self.assertRaises(GPAgentException) as context:
            WebContentProcessor.process_urls(invalid_urls)
            
        self.assertIn("No valid URLs found", str(context.exception))
    
    def test_process_mixed_urls(self):
        """Test processing mix of web and Frappe URLs"""
        urls = [
            "https://example.com/1",
            "http://localhost:8000/app/task/TASK-2024-00001",
            "https://frappe.io/docs"
        ]
        
        result = WebContentProcessor.process_urls(urls)
        self.assertIn('by_type', result['stats'])
        self.assertIn('web', result['stats']['by_type'])
        self.assertEqual(result['stats']['total_urls'], 3)
    
    def test_process_single_url(self):
        """Test processing single URL string"""
        url = "https://example.com/1"
        result = WebContentProcessor.process_urls(url)
        self.assertEqual(result['stats']['total_urls'], 1)
    
    def test_process_text_with_urls(self):
        """Test processing text containing URLs"""
        text = """
        Check these links:
        https://example.com/1
        And http://localhost:8000/app/task/TASK-2024-00001
        """
        
        result = WebContentProcessor.process_urls(text)
        self.assertEqual(result['stats']['total_urls'], 2)
    
    def test_error_handling(self):
        """Test handling processor errors"""
        with self.assertRaises(GPAgentException):
            WebContentProcessor.process_urls(None) 
    
    @patch('frappe.get_doc')
    def test_process_frappe_urls(self, mock_get_doc):
        """Test processing Frappe URLs"""
        # Setup mock Frappe doc
        mock_doc = MagicMock()
        mock_doc.doctype = "Task"
        mock_doc.name = "TASK-2024-00001"
        mock_doc.modified = "2024-01-07 20:45:30"
        mock_doc.modified_by = "Administrator"
        mock_doc.as_markdown.return_value = "# Task Details\n\nThis is a test task."
        mock_get_doc.return_value = mock_doc
        
        # Test URL
        frappe_url = "http://localhost:8000/app/task/TASK-2024-00001"
        
        # Process URL
        result = WebContentProcessor.process_urls(frappe_url)
        
        # Check structure
        self.assertIn('successful_results', result)
        self.assertIn(frappe_url, result['successful_results'])
        
        # Check content
        content = result['successful_results'][frappe_url]
        self.assertEqual(content['title'], "Task: TASK-2024-00001")
        self.assertEqual(content['content'], "# Task Details\n\nThis is a test task.")
        self.assertEqual(content['metadata']['doctype'], "Task")
        self.assertEqual(content['metadata']['docname'], "TASK-2024-00001")
        
        # Verify mock was called correctly
        mock_get_doc.assert_called_once_with("task", "TASK-2024-00001")
    
    def test_process_invalid_frappe_url(self):
        """Test processing invalid Frappe URL format"""
        invalid_url = "http://localhost:8000/wrong/format"
        result = WebContentProcessor.process_urls(invalid_url)
        self.assertIn(invalid_url, result['failed_urls'])
        self.assertEqual(result['failed_urls'][invalid_url], "Invalid Frappe URL format") 