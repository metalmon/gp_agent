import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.tasks.create_task_dependency import CreateTaskDependencyTool

class TestCreateTaskDependencyTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_1"
        self.depends_on_task_id = "test_task_2"
        self.tool = CreateTaskDependencyTool()
        self.test_data = {
            "task_id": self.task_id,
            "depends_on_task_id": self.depends_on_task_id,
            "dependency_type": "Blocks",
            "analysis_reason": "Task 2 must be completed before Task 1"
        }
        self.test_dependency = {
            "name": "dep_1",
            "task": self.task_id,
            "depends_on": self.depends_on_task_id,
            "dependency_type": "Blocks",
            "created_by": "test_user",
            "creation_timestamp": datetime(2024, 1, 24, 12, 0)
        }
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "create_task_dependency")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        required_params = ["task_id", "depends_on_task_id", "dependency_type"]
        for param in required_params:
            self.assertIn(param, params["required"])
        
        # Verify dependency type enum
        self.assertEqual(
            params["properties"]["dependency_type"]["enum"],
            ["Blocks", "Is Blocked By"]
        )
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_create_dependency(self, mock_api_class):
        """Test creating task dependency"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.create_task_dependency.return_value = self.test_dependency
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.create_task_dependency.assert_called_once_with(
            task_id=self.task_id,
            depends_on_task_id=self.depends_on_task_id,
            dependency_type="Blocks",
            analysis_reason="Task 2 must be completed before Task 1"
        )
        
        # Verify result format
        self.assertEqual(result["id"], "dep_1")
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["depends_on_task_id"], self.depends_on_task_id)
        self.assertEqual(result["dependency_type"], "Blocks")
        self.assertEqual(result["created_by"], "test_user")
        self.assertEqual(result["creation_timestamp"], str(datetime(2024, 1, 24, 12, 0)))
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_create_dependency_minimal(self, mock_api_class):
        """Test creating task dependency with minimal parameters"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.create_task_dependency.return_value = self.test_dependency
        mock_api_class.return_value = mock_api
        
        # Setup minimal test data
        minimal_data = {
            "task_id": self.task_id,
            "depends_on_task_id": self.depends_on_task_id,
            "dependency_type": "Is Blocked By"
        }
        
        # Execute tool
        result = await self.tool.execute(minimal_data)
        
        # Verify API call with empty analysis reason
        mock_api.create_task_dependency.assert_called_once_with(
            task_id=self.task_id,
            depends_on_task_id=self.depends_on_task_id,
            dependency_type="Is Blocked By",
            analysis_reason=""
        )
        
        # Verify result
        self.assertEqual(result["dependency_type"], "Is Blocked By") 