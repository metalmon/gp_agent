import unittest
from gp_agent.gameplan_ai_assistant.context.formatters.anthropic import AnthropicMessageFormatter
from gp_agent.gameplan_ai_assistant.context.base import Message

class TestAnthropicFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = AnthropicMessageFormatter()
        
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
        self.assertEqual(formatted[0]["tool_calls"][0]["function"]["parameters"], '{"arg": "value"}')  # Note: parameters instead of arguments
        
    def test_format_tool_response_message(self):
        """Test formatting tool response message (converted to assistant for Anthropic)"""
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
        self.assertEqual(formatted[0]["role"], "assistant")  # Note: tool role converted to assistant
        self.assertEqual(formatted[0]["content"], "Tool result")
        
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
                    "parameters": '{"arg": "value"}'  # Note: parameters instead of arguments
                }
            }]
        }
        
        parsed = self.formatter.parse_model_response(message)
        self.assertEqual(parsed.role, "assistant")
        self.assertIsNone(parsed.content)
        self.assertEqual(len(parsed.tool_calls), 1)
        self.assertEqual(parsed.tool_name, "test_tool")
        self.assertEqual(parsed.tool_call_id, "call_test")
        
    def test_role_conversion(self):
        """Test role conversion methods"""
        # Test _convert_role
        self.assertEqual(self.formatter._convert_role("user"), "user")
        self.assertEqual(self.formatter._convert_role("assistant"), "assistant")
        self.assertEqual(self.formatter._convert_role("tool"), "assistant")  # tool converted to assistant
        self.assertEqual(self.formatter._convert_role("system"), "system")
        
        # Test _convert_role_back
        self.assertEqual(self.formatter._convert_role_back("user"), "user")
        self.assertEqual(self.formatter._convert_role_back("assistant"), "assistant")
        self.assertEqual(self.formatter._convert_role_back("system"), "system") 