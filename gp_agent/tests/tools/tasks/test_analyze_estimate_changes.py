import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.analyze_estimate_changes import AnalyzeEstimateChangesTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestAnalyzeEstimateChangesTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "task-123"
        self.tool = AnalyzeEstimateChangesTool()
        self.test_data = {
            "task_id": self.task_id
        }
        
        # Mock task data
        self.task = {
            "id": self.task_id,
            "title": "Test Task",
            "status": "In Progress"
        }
        
        # Mock comments
        base_date = datetime.now()
        self.comments = [
            {
                "id": "comment-1",
                "content": "Found additional complexity in the implementation",
                "creation": base_date - timedelta(days=2),
                "owner": "john@example.com"
            },
            {
                "id": "comment-2",
                "content": "Need to wait for dependency task to complete",
                "creation": base_date - timedelta(days=1),
                "owner": "jane@example.com"
            }
        ]
        
        # Mock estimates
        self.initial_estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 10.0,
            "confidence_level": "High",
            "note": "Initial estimate",
            "creation": base_date - timedelta(days=3),
            "owner": "john@example.com"
        })
        
        self.second_estimate = frappe._dict({
            "name": "est-2",
            "task": self.task_id,
            "estimated_hours": 15.0,
            "confidence_level": "Medium",
            "note": "Additional complexity discovered",
            "creation": base_date - timedelta(days=2),
            "owner": "john@example.com"
        })
        
        self.final_estimate = frappe._dict({
            "name": "est-3",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "confidence_level": "Low",
            "note": "Blocked by dependency",
            "creation": base_date - timedelta(days=1),
            "owner": "jane@example.com"
        })
        
        self.history = [self.final_estimate, self.second_estimate, self.initial_estimate]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "analyze_estimate_changes")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_changes_with_data(self, mock_get_history, mock_api_class):
        """Test analyzing estimate changes with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.get_task_comments.return_value = self.comments
        mock_api_class.return_value = mock_api
        
        # Setup history mock
        mock_get_history.return_value = self.history
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_api.get_task_comments.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["task_title"], self.task["title"])
        
        # Verify timeline
        timeline = result["timeline"]
        self.assertEqual(len(timeline), 2)
        
        first_change = timeline[0]
        self.assertEqual(first_change["from_hours"], 15.0)
        self.assertEqual(first_change["to_hours"], 20.0)
        self.assertTrue(first_change["confidence_change"])
        
        second_change = timeline[1]
        self.assertEqual(second_change["from_hours"], 10.0)
        self.assertEqual(second_change["to_hours"], 15.0)
        self.assertTrue(second_change["confidence_change"])
        
        # Verify patterns
        patterns = result["patterns"]
        self.assertEqual(patterns["trend"], "consistently increasing")
        self.assertIn(patterns["frequency"], ["very frequent", "frequent"])
        self.assertTrue(len(patterns["common_adjustments"]) > 0)
        
        # Verify reasons
        reasons = result["reasons"]
        self.assertIn("counts", reasons)
        self.assertIn("percentages", reasons)
        self.assertIn("primary_reason", reasons)
        self.assertTrue(reasons["counts"]["complexity_discovered"] > 0)
        self.assertTrue(reasons["counts"]["dependencies"] > 0)
        
        # Verify impact
        impact = result["impact"]
        self.assertEqual(impact["schedule_impact"], "major")
        self.assertEqual(impact["confidence_impact"], "decreasing")
        self.assertEqual(impact["total_adjustment"], 10.0)
        self.assertEqual(impact["percent_change"], 100.0)
        
        # Verify recommendations
        self.assertIsInstance(result["recommendations"], list)
        self.assertTrue(len(result["recommendations"]) > 0)
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_changes_no_history(self, mock_get_history, mock_api_class):
        """Test analyzing estimate changes without history"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.get_task_comments.return_value = []
        mock_api_class.return_value = mock_api
        
        # Setup history mock
        mock_get_history.return_value = []
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["task_title"], self.task["title"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_analyze_estimate_changes_task_not_found(self, mock_api_class):
        """Test analyzing estimate changes for non-existent task"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = None
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn(self.task_id, result["error"]) 