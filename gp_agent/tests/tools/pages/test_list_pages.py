import frappe
import unittest
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.pages.list_pages import ListPagesTool

class TestListPages(unittest.TestCase):
    def setUp(self):
        self.project_id = "test_project"
        self.tool = ListPagesTool()
        
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.list_pages.GameplanAPI')
    async def test_list_pages(self, mock_api_class):
        # Setup API mock
        mock_api = MagicMock()
        expected_pages = [
            {
                "id": "page_1",
                "title": "Test Page 1",
                "url": f"/project/{self.project_id}/page/page_1",
                "created_by": "test_user",
                "created_at": "2024-01-24 12:00:00",
                "modified_at": "2024-01-24 12:00:00"
            },
            {
                "id": "page_2",
                "title": "Test Page 2",
                "url": f"/project/{self.project_id}/page/page_2",
                "created_by": "test_user",
                "created_at": "2024-01-24 13:00:00",
                "modified_at": "2024-01-24 13:00:00"
            }
        ]
        mock_api.list_pages.return_value = expected_pages
        mock_api_class.return_value = mock_api
        
        # Mock process_result to return result without LLM processing
        async def mock_process_result(result, format_prompt):
            return result
        self.tool.process_result = mock_process_result
        
        # Call the tool
        result = await self.tool.execute({"project_id": self.project_id})
        
        # Verify pages were listed via API
        mock_api.list_pages.assert_called_once_with(self.project_id)
        
        # Verify returned data structure
        self.assertEqual(result["project_id"], self.project_id)
        self.assertEqual(result["pages"], expected_pages)
        self.assertEqual(result["total_count"], len(expected_pages))
        
    def test_get_parameters(self):
        """Test parameter schema definition"""
        params = self.tool.get_parameters()
        
        # Verify schema structure
        self.assertEqual(params["type"], "object")
        self.assertIn("project_id", params["properties"])
        self.assertIn("required", params)
        self.assertIn("project_id", params["required"])
        
        # Verify project_id parameter
        project_id_param = params["properties"]["project_id"]
        self.assertEqual(project_id_param["type"], "string")
        self.assertIn("description", project_id_param)
        
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.list_pages.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.tools.pages.list_pages.frappe')
    async def test_validate_access(self, mock_frappe, mock_api_class):
        """Test project access validation"""
        # Setup mocks
        mock_project = MagicMock()
        mock_project.has_permission.return_value = False
        mock_frappe.get_doc.return_value = mock_project
        
        # Try to execute with no access
        with self.assertRaises(frappe.PermissionError):
            await self.tool.execute({"project_id": self.project_id})
            
        # Verify permission was checked
        mock_project.has_permission.assert_called_once_with("read") 