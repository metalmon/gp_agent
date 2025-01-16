import unittest
import frappe
import json
from unittest.mock import patch
from .test_base import GPAgentTestCase
from gp_agent.gameplan_ai_assistant.utils.naming import get_tool_log_name

class TestGPAgentToolLog(GPAgentTestCase):
    def setUp(self):
        super().setUp()
        # Create a test GP Agent Log
        self.test_log = frappe.get_doc({
            "doctype": "GP Agent Log",
            "discussion_id": "test_discussion",
            "model": "gpt-4",
            "status": "Queued",
            "creation_timestamp": frappe.utils.now_datetime(),
            "default_user": "Administrator",
            "team_id": "test_team",
            "project_id": "test_project"
        }).insert()
        
    def tearDown(self):
        if hasattr(self, 'test_log'):
            self.test_log.delete()
        super().tearDown()
        
    def test_status_transitions(self):
        """Test normal status transitions"""
        # Create tool log
        tool_log = frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": self.test_log.name,
            "tool_name": "test_tool",
            "tool_parameters": json.dumps({"param": "value"}),
            "status": "Queued"
        }).insert()
        
        try:
            # Check initial state
            self.assertEqual(tool_log.status, "Queued")
            self.assertTrue(tool_log.creation_timestamp)
            self.assertFalse(tool_log.processing_timestamp)
            self.assertFalse(tool_log.completion_timestamp)
            
            # Start processing
            tool_log.start_processing()
            self.assertEqual(tool_log.status, "Processing")
            self.assertTrue(tool_log.processing_timestamp)
            
            # Mark completed
            response = {"result": "success"}
            tool_log.mark_completed(response)
            self.assertEqual(tool_log.status, "Completed")
            self.assertTrue(tool_log.completion_timestamp)
            self.assertEqual(json.loads(tool_log.tool_response), response)
            
        finally:
            tool_log.delete()
            
    def test_error_handling_and_retries(self):
        """Test error handling and retry logic"""
        tool_log = frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": self.test_log.name,
            "tool_name": "test_tool",
            "tool_parameters": json.dumps({"param": "value"}),
            "status": "Queued"
        }).insert()
        
        try:
            # First error
            tool_log.mark_error("Test error 1")
            self.assertEqual(tool_log.status, "Error")
            self.assertEqual(tool_log.retry_count, 1)
            self.assertEqual(tool_log.error, "Test error 1")
            
            # Second error
            tool_log.mark_error("Test error 2")
            self.assertEqual(tool_log.status, "Error")
            self.assertEqual(tool_log.retry_count, 2)
            
            # Third error should mark as failed (max_retries = 3)
            tool_log.mark_error("Test error 3")
            self.assertEqual(tool_log.status, "Failed")
            self.assertEqual(tool_log.retry_count, 3)
            
        finally:
            tool_log.delete()
            
    def test_parent_log_status_updates(self):
        """Test parent log status updates based on tool logs"""
        # Create multiple tool logs
        tool_log1 = frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": self.test_log.name,
            "tool_name": "test_tool_1",
            "tool_parameters": json.dumps({"param": "value1"}),
            "status": "Queued"
        }).insert()
        
        tool_log2 = frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": self.test_log.name,
            "tool_name": "test_tool_2",
            "tool_parameters": json.dumps({"param": "value2"}),
            "status": "Queued"
        }).insert()
        
        try:
            # When one tool completes and one errors
            tool_log1.mark_completed({"result": "success"})
            tool_log2.mark_error("Test error")
            self.test_log.reload()
            self.assertEqual(self.test_log.status, "Error")
            
            # When one tool fails
            tool_log2.mark_error("Test error")  # Second error
            tool_log2.mark_error("Test error")  # Third error -> Failed
            self.test_log.reload()
            self.assertEqual(self.test_log.status, "Failed")
            
            # Create new tool logs to test all completed
            tool_log1.delete()
            tool_log2.delete()
            
            tool_log3 = frappe.get_doc({
                "doctype": "GP Agent Tool Log",
                "parent_log": self.test_log.name,
                "tool_name": "test_tool_3",
                "tool_parameters": json.dumps({"param": "value3"}),
                "status": "Queued"
            }).insert()
            
            tool_log4 = frappe.get_doc({
                "doctype": "GP Agent Tool Log",
                "parent_log": self.test_log.name,
                "tool_name": "test_tool_4",
                "tool_parameters": json.dumps({"param": "value4"}),
                "status": "Queued"
            }).insert()
            
            # When all tools complete successfully
            tool_log3.mark_completed({"result": "success3"})
            tool_log4.mark_completed({"result": "success4"})
            self.test_log.reload()
            self.assertEqual(self.test_log.status, "Completed")
            
        finally:
            if frappe.db.exists("GP Agent Tool Log", tool_log1.name):
                tool_log1.delete()
            if frappe.db.exists("GP Agent Tool Log", tool_log2.name):
                tool_log2.delete()
            if frappe.db.exists("GP Agent Tool Log", tool_log3.name):
                tool_log3.delete()
            if frappe.db.exists("GP Agent Tool Log", tool_log4.name):
                tool_log4.delete()
                
    def test_content_field_sync(self):
        """Test synchronization of JSON and content fields"""
        tool_log = frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": self.test_log.name,
            "tool_name": "test_tool",
            "tool_parameters": json.dumps({"param": "value"}),
            "status": "Queued"
        }).insert()
        
        try:
            # Check parameters sync
            self.assertTrue(tool_log.tool_parameters_content)
            self.assertIn("param", tool_log.tool_parameters_content)
            self.assertIn("value", tool_log.tool_parameters_content)
            
            # Check response sync
            response = {"result": "success", "data": {"key": "value"}}
            tool_log.mark_completed(response)
            self.assertTrue(tool_log.tool_response_content)
            self.assertIn("result", tool_log.tool_response_content)
            self.assertIn("success", tool_log.tool_response_content)
            
            # Test invalid JSON handling
            tool_log.tool_parameters = "invalid json"
            tool_log.sync_content_fields()
            self.assertEqual(tool_log.tool_parameters_content, "invalid json")
            
        finally:
            tool_log.delete() 