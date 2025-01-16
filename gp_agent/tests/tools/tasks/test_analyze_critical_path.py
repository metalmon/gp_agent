import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.analyze_critical_path import AnalyzeCriticalPathTool
from gp_agent.gameplan_ai_assistant.utils.task_analytics import analyze_critical_path as analyze_critical_path_impl


class TestAnalyzeCriticalPathTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.project_id = "project-123"
        self.tool = AnalyzeCriticalPathTool()
        self.test_data = {
            "project_id": self.project_id
        }
        
        # Mock project data
        self.project = {
            "name": self.project_id,
            "title": "Test Project",
            "status": "In Progress"
        }
        
        # Mock critical path data
        base_date = datetime.now()
        self.critical_path_data = {
            "critical_path": [
                {
                    "task_id": "task-1",
                    "title": "Setup Infrastructure",
                    "duration_hours": 20,
                    "dependencies": []
                },
                {
                    "task_id": "task-2",
                    "title": "Implement Core Features",
                    "duration_hours": 40,
                    "dependencies": ["task-1"]
                },
                {
                    "task_id": "task-3",
                    "title": "Testing and Deployment",
                    "duration_hours": 15,
                    "dependencies": ["task-2"]
                }
            ],
            "total_duration_hours": 75,
            "estimated_completion_date": (base_date + timedelta(days=10)).isoformat(),
            "risk_factors": [
                {
                    "type": "dependency_chain",
                    "description": "Long chain of dependent tasks",
                    "impact": "high"
                },
                {
                    "type": "resource_constraint",
                    "description": "Limited resources for parallel tasks",
                    "impact": "medium"
                }
            ]
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "analyze_critical_path")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("project_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("project_id", params["properties"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.analyze_critical_path')
    async def test_analyze_critical_path_with_data(self, mock_analyze_impl, mock_api_class):
        """Test analyzing critical path with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = self.project
        mock_api_class.return_value = mock_api
        
        # Setup analysis mock
        mock_analyze_impl.return_value = self.critical_path_data
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_project.assert_called_once_with(self.project_id)
        mock_analyze_impl.assert_called_once_with(self.project_id)
        
        # Verify result structure
        self.assertEqual(result["project_id"], self.project_id)
        self.assertEqual(result["project_title"], self.project["title"])
        
        # Verify critical path data
        self.assertIn("critical_path", result)
        critical_path = result["critical_path"]
        self.assertEqual(len(critical_path), 3)
        
        # Verify first task in path
        first_task = critical_path[0]
        self.assertEqual(first_task["task_id"], "task-1")
        self.assertEqual(first_task["title"], "Setup Infrastructure")
        self.assertEqual(first_task["duration_hours"], 20)
        self.assertEqual(len(first_task["dependencies"]), 0)
        
        # Verify total duration and completion date
        self.assertEqual(result["total_duration_hours"], 75)
        self.assertTrue(result["estimated_completion_date"])
        
        # Verify risk factors
        self.assertIn("risk_factors", result)
        risks = result["risk_factors"]
        self.assertEqual(len(risks), 2)
        
        dependency_risk = next(r for r in risks if r["type"] == "dependency_chain")
        self.assertEqual(dependency_risk["impact"], "high")
        
        resource_risk = next(r for r in risks if r["type"] == "resource_constraint")
        self.assertEqual(resource_risk["impact"], "medium")

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_analyze_critical_path_project_not_found(self, mock_api_class):
        """Test analyzing critical path for non-existent project"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = None
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_project.assert_called_once_with(self.project_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn(self.project_id, result["error"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.analyze_critical_path')
    async def test_analyze_critical_path_empty_path(self, mock_analyze_impl, mock_api_class):
        """Test analyzing critical path with no tasks in path"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = self.project
        mock_api_class.return_value = mock_api
        
        # Setup analysis mock with empty critical path
        empty_result = {
            "critical_path": [],
            "total_duration_hours": 0,
            "estimated_completion_date": None,
            "risk_factors": []
        }
        mock_analyze_impl.return_value = empty_result
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_project.assert_called_once_with(self.project_id)
        mock_analyze_impl.assert_called_once_with(self.project_id)
        
        # Verify result structure
        self.assertEqual(result["project_id"], self.project_id)
        self.assertEqual(result["project_title"], self.project["title"])
        self.assertEqual(len(result["critical_path"]), 0)
        self.assertEqual(result["total_duration_hours"], 0)
        self.assertIsNone(result["estimated_completion_date"])
        self.assertEqual(len(result["risk_factors"]), 0) 