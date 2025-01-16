import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime

from gp_agent.gameplan_ai_assistant.tools.tasks.analyze_estimate_quality import AnalyzeEstimateQualityTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestAnalyzeEstimateQualityTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "task-123"
        self.tool = AnalyzeEstimateQualityTool()
        self.test_data = {
            "task_id": self.task_id
        }
        
        # Mock task data
        self.task = {
            "id": self.task_id,
            "title": "Test Task",
            "is_completed": False
        }
        
        # Mock estimates
        self.initial_estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 10.0,
            "remaining_hours": 10.0,
            "confidence_level": "High",
            "note": "Initial estimate",
            "creation": "2024-01-01 10:00:00",
            "owner": "john@example.com"
        })
        
        self.updated_estimate = frappe._dict({
            "name": "est-2",
            "task": self.task_id,
            "estimated_hours": 15.0,
            "remaining_hours": 8.0,
            "confidence_level": "Medium",
            "note": "Updated after analysis",
            "creation": "2024-01-02 10:00:00",
            "owner": "jane@example.com"
        })
        
        self.final_estimate = frappe._dict({
            "name": "est-3",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 5.0,
            "confidence_level": "Low",
            "note": "Final update",
            "creation": "2024-01-03 10:00:00",
            "owner": "bob@example.com"
        })
        
        self.history = [self.final_estimate, self.updated_estimate, self.initial_estimate]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "analyze_estimate_quality")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_quality_with_data(self, mock_get_history, mock_api_class):
        """Test analyzing estimate quality with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api_class.return_value = mock_api
        
        # Setup history mock
        mock_get_history.return_value = self.history
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["task_title"], self.task["title"])
        self.assertIsInstance(result["quality_score"], float)
        self.assertGreaterEqual(result["quality_score"], 0)
        self.assertLessEqual(result["quality_score"], 100)
        
        # Verify estimate changes analysis
        changes = result["estimate_changes"]
        self.assertEqual(changes["total_changes"], 2)
        self.assertIn("stability", changes)
        self.assertIn("average_change_percent", changes)
        self.assertIn("largest_change", changes)
        
        # Verify confidence analysis
        confidence = result["confidence_analysis"]
        self.assertEqual(confidence["current_level"], "Low")
        self.assertEqual(confidence["initial_level"], "High")
        self.assertIn("trend", confidence)
        self.assertIn("consistency", confidence)
        
        # Verify time accuracy analysis
        accuracy = result["time_accuracy"]
        self.assertIn("accuracy", accuracy)
        self.assertIn("deviation_percent", accuracy)
        self.assertEqual(accuracy["initial_estimate"], 10.0)
        self.assertEqual(accuracy["current_estimate"], 20.0)
        
        # Verify recommendations
        self.assertIsInstance(result["recommendations"], list)
        self.assertTrue(len(result["recommendations"]) > 0)
        
    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_analyze_estimate_quality_no_history(self, mock_get_history, mock_api_class):
        """Test analyzing estimate quality without history"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
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
    async def test_analyze_estimate_quality_task_not_found(self, mock_api_class):
        """Test analyzing estimate quality for non-existent task"""
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