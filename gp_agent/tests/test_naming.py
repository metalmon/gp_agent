import unittest
import frappe
from gp_agent.gameplan_ai_assistant.utils.naming import get_short_id, get_tool_log_name

class TestNaming(unittest.TestCase):
    def test_get_short_id(self):
        """Test short ID generation"""
        # Test with default length
        self.assertEqual(len(get_short_id("LOG-test-123456789")), 8)
        self.assertEqual(get_short_id("LOG-test-123456789"), "23456789")
        
        # Test with custom length
        self.assertEqual(len(get_short_id("LOG-test-123456789", 4)), 4)
        self.assertEqual(get_short_id("LOG-test-123456789", 4), "6789")
        
        # Test with empty input
        self.assertEqual(get_short_id(""), "")
        self.assertEqual(get_short_id("", 4), "")
        
        # Test with input shorter than length
        short = "123"
        self.assertEqual(get_short_id(short, 8), short)
        
    def test_get_tool_log_name(self):
        """Test tool log name generation"""
        parent_log = "LOG-test-123456789"
        tool_name = "test_tool"
        
        # First tool log for this parent/tool combination
        name1 = get_tool_log_name(parent_log, tool_name)
        self.assertTrue(name1.startswith("TOOL-"))
        self.assertIn("23456789", name1)  # Short ID
        self.assertIn("test_tool", name1)
        self.assertTrue(name1.endswith("-0001"))  # Counter
        
        # Create a tool log to test counter increment
        frappe.get_doc({
            "doctype": "GP Agent Tool Log",
            "parent_log": parent_log,
            "tool_name": tool_name,
            "status": "Completed"
        }).insert()
        
        # Second tool log should have incremented counter
        name2 = get_tool_log_name(parent_log, tool_name)
        self.assertTrue(name2.endswith("-0002"))
        
        # Different tool name should start counter from 1
        other_name = get_tool_log_name(parent_log, "other_tool")
        self.assertTrue(other_name.endswith("-0001"))
        
        # Clean up
        frappe.db.sql("DELETE FROM `tabGP Agent Tool Log` WHERE parent_log = %s", parent_log)
        frappe.db.commit() 