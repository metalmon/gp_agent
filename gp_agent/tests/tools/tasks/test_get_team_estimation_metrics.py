import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.get_team_estimation_metrics import GetTeamEstimationMetricsTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestGetTeamEstimationMetricsTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.team_id = "team-123"
        self.tool = GetTeamEstimationMetricsTool()
        self.test_data = {
            "team_id": self.team_id,
            "time_period": "1 month"
        }
        
        # Mock team data
        self.team = {
            "name": self.team_id,
            "title": "Engineering Team",
            "status": "Active"
        }
        
        # Mock project data
        self.projects = [
            {
                "name": "project-1",
                "title": "Project A",
                "status": "In Progress"
            },
            {
                "name": "project-2",
                "title": "Project B",
                "status": "In Progress"
            }
        ]
        
        # Mock task data
        base_date = datetime.now()
        self.tasks = [
            {
                "name": "task-1",
                "title": "Task 1",
                "status": "Done",
                "is_completed": True,
                "modified": base_date - timedelta(days=15)
            },
            {
                "name": "task-2",
                "title": "Task 2",
                "status": "In Progress",
                "is_completed": False,
                "modified": base_date - timedelta(days=10)
            },
            {
                "name": "task-3",
                "title": "Task 3",
                "status": "Done",
                "is_completed": True,
                "modified": base_date - timedelta(days=5)
            }
        ]
        
        # Mock estimate data
        self.estimates = {
            "task-1": [
                frappe._dict({
                    "task": "task-1",
                    "estimated_hours": 20.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=15)
                }),
                frappe._dict({
                    "task": "task-1",
                    "estimated_hours": 15.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=20)
                })
            ],
            "task-2": [
                frappe._dict({
                    "task": "task-2",
                    "estimated_hours": 30.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=10)
                }),
                frappe._dict({
                    "task": "task-2",
                    "estimated_hours": 25.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=15)
                })
            ],
            "task-3": [
                frappe._dict({
                    "task": "task-3",
                    "estimated_hours": 10.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=5)
                }),
                frappe._dict({
                    "task": "task-3",
                    "estimated_hours": 8.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=10)
                })
            ]
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_team_estimation_metrics")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("team_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("team_id", params["properties"])
        self.assertIn("time_period", params["properties"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_get_team_estimation_metrics_with_data(self, mock_get_history, mock_api_class):
        """Test getting team estimation metrics with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team_projects.return_value = self.projects
        mock_api.get_all_project_tasks.return_value = self.tasks
        mock_api_class.return_value = mock_api
        
        # Setup estimate history mock
        def get_history_for_task(task_id):
            return self.estimates.get(task_id, [])
        
        mock_get_history.side_effect = get_history_for_task
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_team_projects.assert_called_once_with(self.team_id)
        self.assertEqual(mock_api.get_all_project_tasks.call_count, len(self.projects))
        
        # Verify result structure
        self.assertEqual(result["time_period"], "1 month")
        self.assertEqual(result["total_tasks"], len(self.tasks))
        self.assertEqual(result["tasks_with_estimates"], len(self.estimates))
        
        # Verify accuracy metrics
        self.assertIn("accuracy_metrics", result)
        accuracy = result["accuracy_metrics"]
        self.assertIn("average_accuracy", accuracy)
        self.assertIn("accuracy_distribution", accuracy)
        
        # Verify confidence metrics
        self.assertIn("confidence_metrics", result)
        confidence = result["confidence_metrics"]
        self.assertIn("confidence_distribution", confidence)
        self.assertIn("total_estimates", confidence)
        
        # Verify trend metrics
        self.assertIn("trend_metrics", result)
        trends = result["trend_metrics"]
        self.assertIn("estimate_trends", trends)
        
        # Verify completion metrics
        self.assertIn("completion_metrics", result)
        completion = result["completion_metrics"]
        self.assertEqual(completion["total_tasks"], len(self.tasks))
        self.assertEqual(completion["total_completed"], 2)  # Tasks 1 and 3
        
        # Verify performance metrics
        self.assertIn("performance_metrics", result)
        performance = result["performance_metrics"]
        self.assertIn("total_estimated_hours", performance)
        self.assertIn("total_final_hours", performance)
        self.assertIn("estimation_ratio", performance)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_team_estimation_metrics_no_projects(self, mock_api_class):
        """Test getting metrics when team has no projects"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team_projects.return_value = []
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_team_projects.assert_called_once_with(self.team_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn("No projects found", result["error"])
        self.assertEqual(result["time_period"], "1 month")

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_get_team_estimation_metrics_no_tasks(self, mock_api_class):
        """Test getting metrics when projects have no tasks"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team_projects.return_value = self.projects
        mock_api.get_all_project_tasks.return_value = []
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_team_projects.assert_called_once_with(self.team_id)
        self.assertEqual(mock_api.get_all_project_tasks.call_count, len(self.projects))
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn("No tasks found", result["error"])
        self.assertEqual(result["time_period"], "1 month")

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_get_team_estimation_metrics_no_estimates(self, mock_get_history, mock_api_class):
        """Test getting metrics when tasks have no estimates"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team_projects.return_value = self.projects
        mock_api.get_all_project_tasks.return_value = self.tasks
        mock_api_class.return_value = mock_api
        
        # Setup estimate history mock to return no estimates
        mock_get_history.return_value = []
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_team_projects.assert_called_once_with(self.team_id)
        self.assertEqual(mock_api.get_all_project_tasks.call_count, len(self.projects))
        
        # Verify result structure with zero/empty metrics
        self.assertEqual(result["tasks_with_estimates"], 0)
        self.assertEqual(result["accuracy_metrics"]["average_accuracy"], 0)
        self.assertEqual(result["confidence_metrics"]["total_estimates"], 0)
        self.assertEqual(sum(result["trend_metrics"]["estimate_trends"].values()), 0)
        self.assertEqual(result["performance_metrics"]["total_estimated_hours"], 0) 