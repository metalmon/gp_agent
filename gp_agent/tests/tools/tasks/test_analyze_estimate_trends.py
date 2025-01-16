import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime

from gp_agent.gameplan_ai_assistant.tools.tasks.analyze_estimate_trends import AnalyzeEstimateTrendsTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestAnalyzeEstimateTrendsTool(unittest.TestCase):
    def setUp(self):
        self.project_id = "project-123"
        self.tool = AnalyzeEstimateTrendsTool()
        self.test_data = {
            "project_id": self.project_id
        }
        
        # Mock tasks
        self.tasks = [
            {
                "name": "task-1",
                "title": "Task 1",
                "status": "In Progress"
            },
            {
                "name": "task-2",
                "title": "Task 2",
                "status": "Completed"
            },
            {
                "name": "task-3",
                "title": "Task 3",
                "status": "In Progress"
            }
        ]
        
        # Mock estimates for task 1 (increasing trend)
        self.task1_estimates = [
            frappe._dict({
                "name": "est-1-3",
                "task": "task-1",
                "estimated_hours": 20.0,
                "confidence_level": "Medium",
                "creation": "2024-01-03 10:00:00"
            }),
            frappe._dict({
                "name": "est-1-2",
                "task": "task-1",
                "estimated_hours": 15.0,
                "confidence_level": "High",
                "creation": "2024-01-02 10:00:00"
            }),
            frappe._dict({
                "name": "est-1-1",
                "task": "task-1",
                "estimated_hours": 10.0,
                "confidence_level": "High",
                "creation": "2024-01-01 10:00:00"
            })
        ]
        
        # Mock estimates for task 2 (decreasing trend)
        self.task2_estimates = [
            frappe._dict({
                "name": "est-2-3",
                "task": "task-2",
                "estimated_hours": 5.0,
                "confidence_level": "Low",
                "creation": "2024-01-03 10:00:00"
            }),
            frappe._dict({
                "name": "est-2-2",
                "task": "task-2",
                "estimated_hours": 8.0,
                "confidence_level": "Medium",
                "creation": "2024-01-02 10:00:00"
            }),
            frappe._dict({
                "name": "est-2-1",
                "task": "task-2",
                "estimated_hours": 12.0,
                "confidence_level": "High",
                "creation": "2024-01-01 10:00:00"
            })
        ]
        
        # Mock estimates for task 3 (stable)
        self.task3_estimates = [
            frappe._dict({
                "name": "est-3-2",
                "task": "task-3",
                "estimated_hours": 8.0,
                "confidence_level": "High",
                "creation": "2024-01-02 10:00:00"
            }),
            frappe._dict({
                "name": "est-3-1",
                "task": "task-3",
                "estimated_hours": 8.0,
                "confidence_level": "High",
                "creation": "2024-01-01 10:00:00"
            })
        ]
        
        self.task_estimates = {
            "task-1": self.task1_estimates,
            "task-2": self.task2_estimates,
            "task-3": self.task3_estimates
        }
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "analyze_estimate_trends")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("project_id", params["required"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_trends_with_data(self, mock_get_history, mock_api_class):
        """Test analyzing estimate trends with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project_tasks.return_value = self.tasks
        mock_api_class.return_value = mock_api
        
        # Setup history mock to return different estimates for each task
        def get_history_for_task(task_id):
            return self.task_estimates.get(task_id, [])
        mock_get_history.side_effect = get_history_for_task
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_project_tasks.assert_called_once_with(self.project_id)
        self.assertEqual(mock_get_history.call_count, 3)  # Called for each task
        
        # Verify result structure
        self.assertIn("project_metrics", result)
        self.assertIn("task_trends", result)
        self.assertIn("insights", result)
        self.assertIn("recommendations", result)
        
        # Verify project metrics
        metrics = result["project_metrics"]
        self.assertEqual(metrics["total_initial_hours"], 30.0)  # 10 + 12 + 8
        self.assertEqual(metrics["total_current_hours"], 33.0)  # 20 + 5 + 8
        self.assertIsInstance(metrics["total_change_percentage"], float)
        
        # Verify task trends
        trends = result["task_trends"]
        self.assertEqual(len(trends), 3)
        
        # Verify task 1 (increasing trend)
        task1 = next(t for t in trends if t["task_id"] == "task-1")
        self.assertEqual(task1["initial_estimate"], 10.0)
        self.assertEqual(task1["current_estimate"], 20.0)
        self.assertEqual(task1["confidence_trend"], "Decreasing")
        
        # Verify task 2 (decreasing trend)
        task2 = next(t for t in trends if t["task_id"] == "task-2")
        self.assertEqual(task2["initial_estimate"], 12.0)
        self.assertEqual(task2["current_estimate"], 5.0)
        self.assertEqual(task2["confidence_trend"], "Decreasing")
        
        # Verify task 3 (stable)
        task3 = next(t for t in trends if t["task_id"] == "task-3")
        self.assertEqual(task3["initial_estimate"], 8.0)
        self.assertEqual(task3["current_estimate"], 8.0)
        self.assertEqual(task3["confidence_trend"], "Stable")
        
        # Verify insights and recommendations
        self.assertIsInstance(result["insights"], list)
        self.assertTrue(len(result["insights"]) > 0)
        self.assertIsInstance(result["recommendations"], list)
        self.assertTrue(len(result["recommendations"]) > 0)
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_trends_no_tasks(self, mock_get_history, mock_api_class):
        """Test analyzing estimate trends without tasks"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project_tasks.return_value = []
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_project_tasks.assert_called_once_with(self.project_id)
        mock_get_history.assert_not_called()
        
        # Verify empty result
        self.assertEqual(result["project_metrics"]["total_initial_hours"], 0)
        self.assertEqual(result["project_metrics"]["total_current_hours"], 0)
        self.assertEqual(result["project_metrics"]["total_change_percentage"], 0)
        self.assertEqual(result["task_trends"], [])
        self.assertEqual(result["insights"], [])
        self.assertEqual(result["recommendations"], []) 