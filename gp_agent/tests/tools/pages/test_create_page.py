import frappe
import unittest
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.pages.create_page import CreatePageTool

class TestCreatePage(unittest.TestCase):
    def setUp(self):
        self.project_id = "test_project"
        self.tool = CreatePageTool()
        self.test_data = {
            "project_id": self.project_id,
            "title": "Test Page",
            "content": "# Test Content\nThis is a test page."
        }
        
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.create_page.GameplanAPI')
    async def test_create_page(self, mock_api_class):
        # Setup API mock
        mock_api = MagicMock()
        expected_page = {
            "id": "page_1",
            "title": self.test_data["title"],
            "content": self.test_data["content"],
            "url": f"/project/{self.project_id}/page/page_1",
            "created_by": "test_user",
            "created_at": "2024-01-24 12:00:00",
            "modified_at": "2024-01-24 12:00:00"
        }
        mock_api.create_page.return_value = expected_page
        mock_api_class.return_value = mock_api
        
        # Mock process_result to return result without LLM processing
        async def mock_process_result(result, format_prompt):
            return result
        self.tool.process_result = mock_process_result
        
        # Call the tool
        result = await self.tool.execute(self.test_data)
        
        # Verify page was created via API
        mock_api.create_page.assert_called_once_with(
            self.project_id,
            self.test_data["title"],
            self.test_data["content"]
        )
        
        # Verify returned data structure
        self.assertEqual(result["page"], expected_page)
        
    def test_get_parameters(self):
        """Test parameter schema definition"""
        params = self.tool.get_parameters()
        
        # Verify schema structure
        self.assertEqual(params["type"], "object")
        required_params = ["project_id", "title", "content"]
        for param in required_params:
            self.assertIn(param, params["properties"])
            self.assertIn(param, params["required"])
        
        # Verify parameter types
        for param in required_params:
            self.assertEqual(params["properties"][param]["type"], "string")
            self.assertIn("description", params["properties"][param])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.create_page.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.create_page.frappe')
    async def test_validate_access(self, mock_frappe, mock_api_class):
        """Test project access validation"""
        # Setup mocks
        mock_project = MagicMock()
        mock_project.has_permission.return_value = False
        mock_frappe.get_doc.return_value = mock_project
        
        # Try to execute with no access
        with self.assertRaises(frappe.PermissionError):
            await self.tool.execute(self.test_data)
            
        # Verify permission was checked
        mock_project.has_permission.assert_called_once_with("write") 