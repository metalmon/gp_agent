import unittest
import frappe
import json
from gp_agent.gameplan_ai_assistant.llm.schema import OpenAISchema
from gp_agent.gameplan_ai_assistant.scheduler_jobs import process_single_response
from gp_agent.gameplan_ai_assistant.tools.registry import execute_tool
from .test_base import GPAgentTestCase

class TestToolCalling(GPAgentTestCase):
    def setUp(self):
        super().setUp()
        # Create a test GP Agent Log
        self.test_log = frappe.get_doc({
            "doctype": "GP Agent Log",
            "discussion_id": "test_discussion",
            "model": "gpt-4",
            "is_tool_call": 1,
            "status": "Pending"
        }).insert()
        
        # Create schema for parsing responses
        self.schema = OpenAISchema()
    
    def tearDown(self):
        if hasattr(self, 'test_log'):
            self.test_log.delete()
        super().tearDown()
            
    async def test_process_tool_call_response(self):
        """Test processing response with tool call"""
        # Raw API response
        api_response = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({
                                "query": "test query"
                            })
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }
        
        # Parse through schema
        parsed_response = self.schema.parse_response(api_response)
        
        # Process the response
        await process_single_response(parsed_response, self.test_log, None)
        
        # Check that tool log was created and completed
        tool_logs = frappe.get_list(
            "GP Agent Tool Log",
            filters={
                "parent_log": self.test_log.name,
                "tool_name": "web_search"
            },
            fields=["*"]
        )
        
        self.assertEqual(len(tool_logs), 1)
        tool_log = tool_logs[0]
        
        self.assertEqual(tool_log.tool_name, "web_search")
        self.assertEqual(json.loads(tool_log.tool_parameters), {"query": "test query"})
        self.assertEqual(tool_log.status, "Completed")
        
        # Clean up
        frappe.delete_doc("GP Agent Tool Log", tool_log.name)
        
    async def test_process_message_response(self):
        """Test processing response with message content"""
        # Raw API response
        api_response = {
            "choices": [{
                "message": {
                    "content": "Test response",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }]
        }
        
        # Parse through schema
        parsed_response = self.schema.parse_response(api_response)
        
        # Process the response
        await process_single_response(parsed_response, self.test_log, None)
        
        # Check that log was completed
        self.test_log.reload()
        self.assertEqual(self.test_log.status, "Completed")
        
    async def test_execute_tool(self):
        """Test executing a tool through registry"""
        tool_call = {
            "id": "test_call",
            "type": "function",
            "function": {
                "name": "web_search",
                "arguments": json.dumps({
                    "query": "test query"
                })
            }
        }
        
        result = await execute_tool(tool_call)
        
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("title", result[0])
        self.assertIn("url", result[0])
        self.assertIn("snippet", result[0])
        
    async def test_invalid_tool(self):
        """Test executing an invalid tool"""
        tool_call = {
            "id": "test_call",
            "type": "function",
            "function": {
                "name": "invalid_tool",
                "arguments": json.dumps({
                    "param": "test"
                })
            }
        }
        
        with self.assertRaises(ValueError):
            await execute_tool(tool_call) 