import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.tasks.get_task_dependencies import GetTaskDependenciesTool

class TestGetTaskDependenciesTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_1"
        self.tool = GetTaskDependenciesTool()
        self.test_data = {
            "task_id": self.task_id
        }
        self.test_dependencies = [
            {
                "name": "dep_1",
                "task": "test_task_1",
                "depends_on_task": "test_task_2",
                "dependency_type": "Blocks",
                "creation": datetime(2024, 1, 24, 12, 0),
                "owner": "test_user"
            },
            {
                "name": "dep_2",
                "task": "test_task_3",
                "depends_on_task": "test_task_1",
                "dependency_type": "Is Blocked By",
                "creation": datetime(2024, 1, 24, 13, 0),
                "owner": "test_user"
            }
        ]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_task_dependencies")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_dependencies(self, mock_api_class):
        """Test getting task dependencies"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_dependencies.return_value = self.test_dependencies
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_task_dependencies.assert_called_once_with(
            task_id=self.task_id
        )
        
        # Verify result format
        self.assertEqual(len(result), 2)
        
        # Verify first dependency
        first_dep = result[0]
        self.assertEqual(first_dep["id"], "dep_1")
        self.assertEqual(first_dep["task_id"], "test_task_1")
        self.assertEqual(first_dep["depends_on_task_id"], "test_task_2")
        self.assertEqual(first_dep["dependency_type"], "Blocks")
        self.assertEqual(first_dep["created_by"], "test_user")
        self.assertEqual(first_dep["created_at"], str(datetime(2024, 1, 24, 12, 0)))
        
        # Verify second dependency
        second_dep = result[1]
        self.assertEqual(second_dep["id"], "dep_2")
        self.assertEqual(second_dep["task_id"], "test_task_3")
        self.assertEqual(second_dep["depends_on_task_id"], "test_task_1")
        self.assertEqual(second_dep["dependency_type"], "Is Blocked By")
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_dependencies_empty(self, mock_api_class):
        """Test getting dependencies for task without any"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_dependencies.return_value = []
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify empty result
        self.assertEqual(len(result), 0) 