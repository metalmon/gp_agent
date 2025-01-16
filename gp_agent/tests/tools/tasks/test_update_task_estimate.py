import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime

from gp_agent.gameplan_ai_assistant.tools.tasks.update_task_estimate import UpdateTaskEstimateTool


class TestUpdateTaskEstimateTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.task_id = "task-123"
        self.tool = UpdateTaskEstimateTool()
        self.test_data = {
            "task_id": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 15.0,
            "confidence_level": "High",
            "note": "Updated estimate after analysis"
        }
        
        # Mock estimate data
        self.estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 15.0,
            "confidence_level": "High",
            "note": "Updated estimate after analysis",
            "creation": datetime.now().isoformat(),
            "owner": "test@example.com"
        })

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "update_task_estimate")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        self.assertIn("estimated_hours", params["required"])
        self.assertEqual(len(params["required"]), 2)
        
        # Test parameter properties
        properties = params["properties"]
        self.assertIn("task_id", properties)
        self.assertIn("estimated_hours", properties)
        self.assertIn("remaining_hours", properties)
        self.assertIn("confidence_level", properties)
        self.assertIn("note", properties)
        
        # Test confidence level enum
        confidence_levels = properties["confidence_level"]["enum"]
        self.assertEqual(set(confidence_levels), {"High", "Medium", "Low"})

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.update_task_estimate.frappe')
    async def test_update_task_estimate_with_all_fields(self, mock_frappe):
        """Test updating task estimate with all fields"""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.insert.return_value = self.estimate
        mock_frappe.get_doc.return_value = mock_doc
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify frappe calls
        mock_frappe.get_doc.assert_called_once_with({
            "doctype": "GP Task Estimate",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 15.0,
            "confidence_level": "High",
            "note": "Updated estimate after analysis"
        })
        mock_doc.insert.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["id"], self.estimate.name)
        self.assertEqual(result["task_id"], self.estimate.task)
        self.assertEqual(result["estimated_hours"], self.estimate.estimated_hours)
        self.assertEqual(result["remaining_hours"], self.estimate.remaining_hours)
        self.assertEqual(result["confidence_level"], self.estimate.confidence_level)
        self.assertEqual(result["note"], self.estimate.note)
        self.assertEqual(result["created_at"], self.estimate.creation)
        self.assertEqual(result["created_by"], self.estimate.owner)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.update_task_estimate.frappe')
    async def test_update_task_estimate_minimal_fields(self, mock_frappe):
        """Test updating task estimate with only required fields"""
        # Setup test data with minimal fields
        minimal_data = {
            "task_id": self.task_id,
            "estimated_hours": 20.0
        }
        
        # Setup mock
        minimal_estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 20.0,  # Should default to estimated_hours
            "confidence_level": None,
            "note": None,
            "creation": datetime.now().isoformat(),
            "owner": "test@example.com"
        })
        
        mock_doc = MagicMock()
        mock_doc.insert.return_value = minimal_estimate
        mock_frappe.get_doc.return_value = mock_doc
        
        # Execute tool
        result = await self.tool.execute(minimal_data)
        
        # Verify frappe calls
        mock_frappe.get_doc.assert_called_once_with({
            "doctype": "GP Task Estimate",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "remaining_hours": 20.0,  # Should default to estimated_hours
            "confidence_level": None,
            "note": None
        })
        mock_doc.insert.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["id"], minimal_estimate.name)
        self.assertEqual(result["task_id"], minimal_estimate.task)
        self.assertEqual(result["estimated_hours"], minimal_estimate.estimated_hours)
        self.assertEqual(result["remaining_hours"], minimal_estimate.remaining_hours)
        self.assertIsNone(result["confidence_level"])
        self.assertIsNone(result["note"])
        self.assertEqual(result["created_at"], minimal_estimate.creation)
        self.assertEqual(result["created_by"], minimal_estimate.owner)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.update_task_estimate.frappe')
    async def test_update_task_estimate_with_zero_hours(self, mock_frappe):
        """Test updating task estimate with zero hours"""
        # Setup test data with zero hours
        zero_hours_data = {
            "task_id": self.task_id,
            "estimated_hours": 0.0,
            "remaining_hours": 0.0
        }
        
        # Setup mock
        zero_hours_estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 0.0,
            "remaining_hours": 0.0,
            "confidence_level": None,
            "note": None,
            "creation": datetime.now().isoformat(),
            "owner": "test@example.com"
        })
        
        mock_doc = MagicMock()
        mock_doc.insert.return_value = zero_hours_estimate
        mock_frappe.get_doc.return_value = mock_doc
        
        # Execute tool
        result = await self.tool.execute(zero_hours_data)
        
        # Verify frappe calls
        mock_frappe.get_doc.assert_called_once_with({
            "doctype": "GP Task Estimate",
            "task": self.task_id,
            "estimated_hours": 0.0,
            "remaining_hours": 0.0,
            "confidence_level": None,
            "note": None
        })
        mock_doc.insert.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["estimated_hours"], 0.0)
        self.assertEqual(result["remaining_hours"], 0.0) 