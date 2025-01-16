import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.tasks.update_task import UpdateTaskTool

class TestUpdateTaskTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_1"
        self.tool = UpdateTaskTool()
        self.test_data = {
            "task_id": self.task_id,
            "status": "In Progress",
            "description": "# Updated Content\nThis is an updated task.",
            "priority": "High",
            "assigned_to": "test_user",
            "start_date": "2024-01-24",
            "due_date": "2024-01-30"
        }
        self.test_task = MagicMock(
            name=self.task_id,
            title="Test Task",
            description="<h1>Updated Content</h1>\n<p>This is an updated task.</p>",
            status="In Progress",
            priority="High",
            assigned_to="test_user",
            start_date="2024-01-24",
            due_date="2024-01-30",
            project="test_project",
            creation=datetime(2024, 1, 24, 12, 0),
            modified=datetime(2024, 1, 24, 13, 0)
        )
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "update_task")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        
        # Verify enums
        self.assertEqual(
            params["properties"]["status"]["enum"],
            ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
        )
        self.assertEqual(
            params["properties"]["priority"]["enum"],
            ["Urgent", "High", "Medium", "Low"]
        )
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_update_task_full(self, mock_api_class):
        """Test updating all task fields"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.update_task.return_value = self.test_task
        mock_api.get_project.return_value = {"title": "Test Project"}
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.update_task.assert_called_once_with(
            task_id=self.task_id,
            status="In Progress",
            description=self.test_task.description,  # HTML version
            start_date="2024-01-24",
            due_date="2024-01-30",
            priority="High",
            assigned_to="test_user"
        )
        
        # Verify result format
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["status"], "In Progress")
        self.assertEqual(result["description"], self.test_data["description"])  # Original markdown
        self.assertEqual(result["priority"], "High")
        self.assertEqual(result["assignee"], "test_user")
        self.assertEqual(result["project_title"], "Test Project")
        self.assertTrue(result["updated"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_update_task_partial(self, mock_api_class):
        """Test updating only some task fields"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.update_task.return_value = self.test_task
        mock_api.get_project.return_value = {"title": "Test Project"}
        mock_api_class.return_value = mock_api
        
        # Setup partial update data
        partial_data = {
            "task_id": self.task_id,
            "status": "Done"
        }
        
        # Execute tool
        result = await self.tool.execute(partial_data)
        
        # Verify API call with only specified fields
        mock_api.update_task.assert_called_once_with(
            task_id=self.task_id,
            status="Done",
            description=None,
            start_date=None,
            due_date=None,
            priority=None,
            assigned_to=None
        )
        
        # Verify result
        self.assertEqual(result["status"], "In Progress")
        self.assertTrue(result["updated"]) 