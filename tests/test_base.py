import unittest
import frappe
import json
from unittest.mock import patch

class GPAgentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test settings that will be used across all tests"""
        cls.settings = frappe.get_doc({
            "doctype": "GP Agent Settings",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "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",
            "request_timeout": 30,
            "max_retries": 3,
            "retry_delay": 30
        })
        
        # Mock frappe.get_single to return our test settings
        cls._patcher = patch('frappe.get_single', return_value=cls.settings)
        cls._patcher.start()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up class-level mocks"""
        cls._patcher.stop()
        
    def setUp(self):
        """Set up test data before each test"""
        self.sample_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        self.sample_function_call = {
            "choices": [{
                "message": {
                    "content": None,
                    "function_call": {
                        "name": "web_search",
                        "arguments": json.dumps({
                            "query": "test query"
                        })
                    }
                }
            }]
        }
        
        self.sample_normal_response = {
            "choices": [{
                "message": {
                    "content": "This is a test response",
                    "role": "assistant"
                }
            }]
        }
        
    def tearDown(self):
        """Clean up test data after each test"""
        # Clean up GP Agent Logs
        frappe.db.delete("GP Agent Log", {
            "discussion_id": "test_discussion"
        })
        
        # Clean up GP Agent Tool Logs
        frappe.db.delete("GP Agent Tool Log", {
            "parent_log": ["like", "%test%"]
        })
        
        frappe.db.commit() 