import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.tasks.get_user_tasks import GetUserTasksTool

class TestGetUserTasksTool(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_user"
        self.tool = GetUserTasksTool()
        self.test_data = {
            "user_id": self.user_id
        }
        self.test_tasks = [
            {
                "id": "task_1",
                "title": "Test Task 1",
                "status": "In Progress",
                "priority": "High",
                "due_date": "2024-01-30",
                "project": "test_project"
            },
            {
                "id": "task_2",
                "title": "Test Task 2",
                "status": "Todo",
                "priority": "Medium",
                "due_date": "2024-02-15",
                "project": "test_project"
            }
        ]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_user_tasks")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("user_id", params["required"])
        self.assertIn("status", params["properties"])
        self.assertIn("project_id", params["properties"])
        
        # Verify status enum
        status_enum = params["properties"]["status"]["items"]["enum"]
        self.assertEqual(
            status_enum,
            ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
        )
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_user_tasks_basic(self, mock_api_class):
        """Test getting user tasks without filters"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_user_tasks.return_value = self.test_tasks
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_user_tasks.assert_called_once_with(
            user_id=self.user_id,
            status=None,
            project_id=None
        )
        
        # Verify result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "task_1")
        self.assertEqual(result[1]["id"], "task_2")
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_user_tasks_with_filters(self, mock_api_class):
        """Test getting user tasks with status and project filters"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_user_tasks.return_value = [self.test_tasks[0]]  # Only first task
        mock_api_class.return_value = mock_api
        
        # Setup test data with filters
        self.test_data.update({
            "status": ["In Progress"],
            "project_id": "test_project"
        })
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call with filters
        mock_api.get_user_tasks.assert_called_once_with(
            user_id=self.user_id,
            status=["In Progress"],
            project_id="test_project"
        )
        
        # Verify filtered result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "task_1")
        self.assertEqual(result[0]["status"], "In Progress") 