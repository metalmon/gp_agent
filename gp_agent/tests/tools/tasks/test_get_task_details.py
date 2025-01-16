import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.tasks.get_task_details import GetTaskDetailsTool

class TestGetTaskDetailsTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_1"
        self.tool = GetTaskDetailsTool()
        self.test_data = {
            "task_id": self.task_id
        }
        self.test_task = MagicMock(
            name=self.task_id,
            title="Test Task",
            description="<h1>Test Content</h1>\n<p>This is a test task.</p>",
            status="In Progress",
            priority="High",
            assigned_to="test_user",
            due_date="2024-01-30",
            project="test_project",
            creation=datetime(2024, 1, 24, 12, 0),
            modified=datetime(2024, 1, 24, 13, 0)
        )
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_task_details")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        self.assertIn("format", params["properties"])
        self.assertEqual(params["properties"]["format"]["enum"], ["html", "markdown"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_task_details_html(self, mock_api_class):
        """Test getting task details in HTML format"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.test_task
        mock_api.get_project.return_value = {"title": "Test Project"}
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        
        # Verify result format
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["title"], "Test Task")
        self.assertEqual(result["description"], self.test_task.description)
        self.assertEqual(result["status"], "In Progress")
        self.assertEqual(result["priority"], "High")
        self.assertEqual(result["assignee"], "test_user")
        self.assertEqual(result["project_title"], "Test Project")
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_task_details_markdown(self, mock_api_class):
        """Test getting task details in markdown format"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.test_task
        mock_api.get_project.return_value = {"title": "Test Project"}
        mock_api_class.return_value = mock_api
        
        # Setup test data with markdown format
        self.test_data["format"] = "markdown"
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify markdown conversion was attempted
        self.assertNotEqual(result["description"], self.test_task.description)  # Should be converted to markdown 