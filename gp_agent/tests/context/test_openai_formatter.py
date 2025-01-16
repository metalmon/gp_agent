import unittest
from gp_agent.gameplan_ai_assistant.context.formatters.openai import OpenAIMessageFormatter
from gp_agent.gameplan_ai_assistant.context.base import Message

class TestOpenAIFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = OpenAIMessageFormatter()
        
    def test_format_regular_message(self):
        """Test formatting regular user/assistant messages"""
        message = Message(
            content="Hello world",
            tasks=[],
            context={},
            role="user"
        )
        
        formatted = self.formatter.format_to_model_messages([message])
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["role"], "user")
        # Content is formatted with a header
        self.assertTrue("Hello world" in formatted[0]["content"])
        
    def test_format_tool_call_message(self):
        """Test formatting assistant message with tool calls"""
        message = Message(
            content=None,
            tasks=[],
            context={},
            role="assistant",
            tool_calls=[{
                "id": "call_test",
                "name": "test_tool",
                "arguments": '{"arg": "value"}'
            }]
        )
        
        formatted = self.formatter.format_to_model_messages([message])
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["role"], "assistant")
        self.assertIsNone(formatted[0]["content"])
        self.assertEqual(len(formatted[0]["tool_calls"]), 1)
        self.assertEqual(formatted[0]["tool_calls"][0]["function"]["name"], "test_tool")
        self.assertEqual(formatted[0]["tool_calls"][0]["function"]["arguments"], '{"arg": "value"}')
        
    def test_format_tool_response_message(self):
        """Test formatting tool response message"""
        message = Message(
            content="Tool result",
            tasks=[],
            context={},
            role="tool",
            tool_name="test_tool",
            tool_call_id="call_test"
        )
        
        formatted = self.formatter.format_to_model_messages([message])
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["role"], "tool")
        self.assertEqual(formatted[0]["content"], "Tool result")
        self.assertEqual(formatted[0]["name"], "test_tool")
        self.assertEqual(formatted[0]["tool_call_id"], "call_test")
        
    def test_parse_regular_message(self):
        """Test parsing regular assistant message (pre-processed by schema)"""
        message = {
            "role": "assistant",
            "content": "Hello world"
        }
        
        parsed = self.formatter.parse_model_response(message)
        self.assertEqual(parsed.role, "assistant")
        # Content is converted to HTML
        self.assertTrue("<p>Hello world</p>" in parsed.content)
        self.assertIsNone(parsed.tool_calls)
        
    def test_parse_tool_call_message(self):
        """Test parsing tool call message (pre-processed by schema)"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_test",
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "arguments": '{"arg": "value"}'
                }
            }]
        }
        
        parsed = self.formatter.parse_model_response(message)
        self.assertEqual(parsed.role, "assistant")
        self.assertIsNone(parsed.content)
        self.assertEqual(len(parsed.tool_calls), 1)
        self.assertEqual(parsed.tool_name, "test_tool")
        self.assertEqual(parsed.tool_call_id, "call_test")
        
    def test_parse_tool_response_message(self):
        """Test parsing tool response message (pre-processed by schema)"""
        message = {
            "role": "tool",
            "content": "Tool result",
            "name": "test_tool",
            "tool_call_id": "call_test"
        }
        
        parsed = self.formatter.parse_model_response(message)
        self.assertEqual(parsed.role, "tool")
        self.assertEqual(parsed.content, "Tool result")  # No HTML conversion for tool responses
        self.assertEqual(parsed.tool_name, "test_tool")
        self.assertEqual(parsed.tool_call_id, "call_test") 