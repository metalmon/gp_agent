from unittest.mock import patch, MagicMock
import unittest
import json
from gp_agent.gameplan_ai_assistant.scheduler_jobs import process_single_response
from gp_agent.gameplan_ai_assistant.utils.tool_caller import get_available_functions
from gp_agent.gameplan_ai_assistant.llm.schema import OpenAISchema

class TestSchemaResponseParsing(unittest.TestCase):
    def setUp(self):
        self.schema = OpenAISchema()
        
    def test_parse_function_call_in_code_block(self):
        """Test parsing function call from code block"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "<thoughts>\nNeed to call test function\n</thoughts>\n<response>\n```json\n{\"function_call\": {\"name\": \"test_function\", \"arguments\": {\"project_id\": \"123\"}}}\n```\n</response>"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "tool_call")
        self.assertIsNotNone(result["tool_calls"])
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "test_function")
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"])["project_id"], "123")
        
    def test_parse_function_call_direct_json(self):
        """Test parsing function call from direct JSON"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "<thoughts>\nNeed to call test function\n</thoughts>\n<response>\n{\"function_call\": {\"name\": \"test_function\", \"arguments\": {\"project_id\": \"123\"}}}\n</response>"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "tool_call")
        self.assertIsNotNone(result["tool_calls"])
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "test_function")
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"])["project_id"], "123")
        
    def test_parse_regular_response(self):
        """Test parsing regular response without function call"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "<thoughts>\nRegular response\n</thoughts>\n<response>\nThis is a regular response\n</response>"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"].strip(), "This is a regular response")
        
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON in response"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "<thoughts>\nInvalid JSON\n</thoughts>\n<response>\n```json\n{\"function_call\": {\"name\": \"test_function\", \"arguments\": {\"project_id\": }}\n```\n</response>"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertIsNotNone(result["content"])
        
    def test_parse_google_format(self):
        """Test parsing response in Google format"""
        response_data = {
            "candidates": [{
                "content": "<thoughts>\nNeed to call test function\n</thoughts>\n<response>\n```json\n{\"function_call\": {\"name\": \"test_function\", \"arguments\": {\"project_id\": \"123\"}}}\n```\n</response>"
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "tool_call")
        self.assertIsNotNone(result["tool_calls"])
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "test_function")
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"])["project_id"], "123")
        
    def test_parse_no_response_tag(self):
        """Test parsing response without <response> tag"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "Just a regular message without XML tags"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"].strip(), "Just a regular message without XML tags")
        
    def test_parse_empty_response(self):
        """Test parsing empty response"""
        response_data = {
            "choices": [{
                "message": {
                    "content": ""
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"].strip(), "")
        
    def test_parse_invalid_response_format(self):
        """Test parsing response with invalid format"""
        response_data = {
            "invalid": "format"
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"].strip(), "")
        
    def test_parse_multiple_response_tags(self):
        """Test parsing response with multiple <response> tags"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "<thoughts>\nMultiple responses\n</thoughts>\n<response>\nFirst response\n</response>\n<response>\n{\"function_call\": {\"name\": \"test_function\", \"arguments\": {\"project_id\": \"123\"}}}\n</response>"
                }
            }]
        }
        
        result = self.schema.parse_response(response_data)
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"].strip(), "First response") 