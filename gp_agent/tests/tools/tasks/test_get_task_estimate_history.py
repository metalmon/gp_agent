import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime
from gp_agent.gameplan_ai_assistant.tools.tasks.get_task_estimate_history import GetTaskEstimateHistoryTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate

class TestGetTaskEstimateHistoryTool(unittest.TestCase):
    def setUp(self):
        self.task_id = "task-123"
        self.tool = GetTaskEstimateHistoryTool()
        self.test_data = {
            "task_id": self.task_id
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
        
        self.history = [self.initial_estimate, self.updated_estimate]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_task_estimate_history")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        
    @patch.object(GPTaskEstimate, "get_latest_estimate")
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_get_task_estimate_history_with_data(self, mock_get_history, mock_get_latest):
        """Test getting task estimate history with data"""
        # Setup mocks
        mock_get_latest.return_value = self.updated_estimate
        mock_get_history.return_value = self.history
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify mocks were called
        mock_get_latest.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        
        # Verify current estimate
        current = result["current_estimate"]
        self.assertEqual(current["estimated_hours"], 15.0)
        self.assertEqual(current["remaining_hours"], 8.0)
        self.assertEqual(current["confidence_level"], "Medium")
        self.assertEqual(current["last_updated"], "2024-01-02 10:00:00")
        
        # Verify history
        history = result["history"]
        self.assertEqual(len(history), 2)
        
        first = history[0]
        self.assertEqual(first["timestamp"], "2024-01-01 10:00:00")
        self.assertEqual(first["user"], "john@example.com")
        self.assertEqual(first["estimated_hours"], 10.0)
        self.assertEqual(first["remaining_hours"], 10.0)
        self.assertEqual(first["confidence_level"], "High")
        self.assertEqual(first["note"], "Initial estimate")
        
        # Verify analysis
        analysis = result["analysis"]
        self.assertEqual(analysis["initial_estimate"], 10.0)
        self.assertEqual(analysis["current_estimate"], 15.0)
        self.assertEqual(analysis["total_adjustment"], 5.0)
        self.assertEqual(analysis["completion_percentage"], 20.0)  # (10-8)/10 * 100
        
    @patch.object(GPTaskEstimate, "get_latest_estimate")
    @patch.object(GPTaskEstimate, "get_estimate_history")    
    async def test_get_task_estimate_history_no_data(self, mock_get_history, mock_get_latest):
        """Test getting estimate history for task without any estimates"""
        # Setup mocks
        mock_get_latest.return_value = None
        mock_get_history.return_value = []
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify mocks were called
        mock_get_latest.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify empty result
        self.assertEqual(result["task_id"], self.task_id)
        self.assertIsNone(result["current_estimate"])
        self.assertEqual(result["history"], [])
        self.assertIsNone(result["analysis"]) 