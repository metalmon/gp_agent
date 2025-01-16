"""Tests for LLM-powered tools"""

import unittest
from unittest.mock import patch, Mock
import json
from typing import Dict, Any
from gp_agent.gameplan_ai_assistant.tools.base.openai_tool import OpenAITool
from gp_agent.gameplan_ai_assistant.tools.base.llm_response_tool import LLMResponseTool
from gp_agent.gameplan_ai_assistant.tools.examples.weather import WeatherTool
from gp_agent.gameplan_ai_assistant.llm.base import BaseLLMClient
from gp_agent.gameplan_ai_assistant.llm.openai import OpenAIClient


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing"""
    
    def chat_completion(self, messages, tools=None, **kwargs):
        """Mock chat completion that returns test response"""
        return {
            "type": "message",
            "content": "Mock response",
            "tool_calls": None
        }


class TestResponseTool(LLMResponseTool):
    """Concrete tool implementation for testing LLMResponseTool"""
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get test parameters schema"""
        return {
            "type": "object",
            "properties": {
                "test_param": {
                    "type": "string",
                    "description": "Test parameter"
                }
            }
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test tool"""
        result = {"value": "test_value"}
        return await self.process_result(
            result=result,
            format_prompt="Test value is {value}"
        )


class TestTool(OpenAITool):
    """Concrete tool implementation for testing OpenAITool"""
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get test parameters schema"""
        return {
            "type": "object",
            "properties": {
                "test_param": {
                    "type": "string",
                    "description": "Test parameter"
                }
            }
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test tool"""
        return {"result": "test_result"}


class TestLLMResponseTool(unittest.TestCase):
    """Test LLMResponseTool functionality"""
    
    def setUp(self):
        """Set up test tool"""
        self.tool = TestResponseTool(
            name="test_tool",
            description="Test tool description"
        )
    
    def test_init_default_prompt(self):
        """Test tool initialization with default system prompt"""
        self.assertEqual(self.tool.name, "test_tool")
        self.assertEqual(self.tool.description, "Test tool description")
        self.assertIn("helpful assistant", self.tool.system_prompt)
        
    def test_init_custom_prompt(self):
        """Test tool initialization with custom system prompt"""
        prompt = "Custom system prompt"
        tool = TestResponseTool(
            name="test_tool",
            description="Test tool description",
            system_prompt=prompt
        )
        self.assertEqual(tool.system_prompt, prompt)
    
    @patch('gp_agent.gameplan_ai_assistant.llm.openai.OpenAIClient.chat_completion')
    async def test_process_result(self, mock_chat_completion):
        """Test result processing with LLM"""
        result = {"value": "test_value"}
        mock_response = {
            "type": "message",
            "content": "Test value is test_value",
            "tool_calls": None
        }
        mock_chat_completion.return_value = mock_response
        
        processed = await self.tool.process_result(
            result=result,
            format_prompt="Test value is {value}"
        )
        
        self.assertEqual(processed["value"], "test_value")
        self.assertEqual(processed["description"], mock_response["content"])
        
        # Verify LLM was called with correct messages
        mock_chat_completion.assert_called_once()
        call_args = mock_chat_completion.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Test value is test_value")
    
    @patch('gp_agent.gameplan_ai_assistant.llm.openai.OpenAIClient.chat_completion')
    async def test_execute(self, mock_chat_completion):
        """Test tool execution with result processing"""
        mock_response = {
            "type": "message",
            "content": "Test value is test_value",
            "tool_calls": None
        }
        mock_chat_completion.return_value = mock_response
        
        result = await self.tool.execute({"test_param": "test"})
        
        self.assertEqual(result["value"], "test_value")
        self.assertEqual(result["description"], mock_response["content"])


class TestOpenAITool(unittest.TestCase):
    """Test OpenAITool functionality"""
    
    def setUp(self):
        """Set up test tool"""
        self.tool = TestTool(
            name="test_tool",
            description="Test tool description"
        )
    
    def test_init_default_client(self):
        """Test tool initialization with default client"""
        self.assertEqual(self.tool.name, "test_tool")
        self.assertEqual(self.tool.description, "Test tool description")
        self.assertIsInstance(self.tool.llm_client, OpenAIClient)
        
    def test_init_custom_client(self):
        """Test tool initialization with custom client"""
        tool = TestTool(
            name="test_tool",
            description="Test tool description",
            client_class=MockLLMClient
        )
        self.assertIsInstance(tool.llm_client, MockLLMClient)
        
    def test_init_with_settings(self):
        """Test tool initialization with client settings"""
        settings = {"test_setting": "test_value"}
        tool = TestTool(
            name="test_tool",
            description="Test tool description",
            client_settings=settings
        )
        self.assertEqual(tool.llm_client.settings_override, settings)
    
    def test_get_schema_openai(self):
        """Test getting OpenAI schema"""
        schema = self.tool.get_schema("OpenAI")
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "test_tool")
        self.assertEqual(schema["function"]["description"], "Test tool description")
        self.assertIn("test_param", schema["function"]["parameters"]["properties"])
        
    def test_get_schema_unsupported(self):
        """Test getting unsupported schema type"""
        with self.assertRaises(ValueError) as cm:
            self.tool.get_schema("Anthropic")
        self.assertIn("only supports OpenAI schema type", str(cm.exception))
        
    def test_parse_call_openai(self):
        """Test parsing OpenAI tool call"""
        params = {"test_param": "test_value"}
        call_data = {
            "function": {
                "arguments": json.dumps(params)
            }
        }
        parsed = self.tool.parse_call("OpenAI", call_data)
        self.assertEqual(parsed, params)
        
    def test_parse_call_unsupported(self):
        """Test parsing unsupported call format"""
        with self.assertRaises(ValueError) as cm:
            self.tool.parse_call("Anthropic", {})
        self.assertIn("only supports OpenAI schema type", str(cm.exception))
    
    @patch('gp_agent.gameplan_ai_assistant.llm.openai.OpenAIClient.chat_completion')
    async def test_chat_completion(self, mock_chat_completion):
        """Test chat completion method"""
        messages = [{"role": "user", "content": "test"}]
        mock_response = {
            "type": "message",
            "content": "Test response",
            "tool_calls": None
        }
        mock_chat_completion.return_value = mock_response
        
        response = await self.tool.chat_completion(messages)
        
        mock_chat_completion.assert_called_once_with(
            messages=messages,
            tools=None
        )
        self.assertEqual(response, mock_response)
        
    async def test_chat_completion_custom_client(self):
        """Test chat completion with custom client"""
        tool = TestTool(
            name="test_tool",
            description="Test tool description",
            client_class=MockLLMClient
        )
        messages = [{"role": "user", "content": "test"}]
        
        response = await tool.chat_completion(messages)
        
        self.assertEqual(response["content"], "Mock response")
        
    async def test_execute(self):
        """Test tool execution"""
        params = {"test_param": "test_value"}
        result = await self.tool.execute(params)
        self.assertEqual(result["result"], "test_result")


class TestWeatherTool(unittest.TestCase):
    """Test WeatherTool functionality"""
    
    def setUp(self):
        """Set up test tool"""
        self.tool = WeatherTool()
    
    def test_init(self):
        """Test tool initialization"""
        self.assertEqual(self.tool.name, "get_weather")
        self.assertIn("weather", self.tool.description.lower())
        self.assertIn("weather assistant", self.tool.system_prompt)
    
    def test_parameters(self):
        """Test parameters schema"""
        params = self.tool.get_parameters()
        self.assertIn("location", params["properties"])
        self.assertIn("units", params["properties"])
        self.assertIn("location", params["required"])
        
    def test_get_schema(self):
        """Test getting tool schema"""
        schema = self.tool.get_schema("OpenAI")
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "get_weather")
        self.assertIn("location", schema["function"]["parameters"]["properties"])
    
    @patch('gp_agent.gameplan_ai_assistant.llm.openai.OpenAIClient.chat_completion')
    async def test_execute(self, mock_chat_completion):
        """Test weather tool execution"""
        params = {"location": "London", "units": "celsius"}
        mock_response = {
            "type": "message",
            "content": "The weather in London is sunny with 22°C",
            "tool_calls": None
        }
        mock_chat_completion.return_value = mock_response
        
        result = await self.tool.execute(params)
        
        self.assertEqual(result["location"], "London")
        self.assertEqual(result["temperature"], 22)
        self.assertEqual(result["units"], "celsius")
        self.assertEqual(result["condition"], "sunny")
        self.assertEqual(result["description"], mock_response["content"])
        
        # Verify LLM was called with correct messages
        mock_chat_completion.assert_called_once()
        call_args = mock_chat_completion.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("London", messages[1]["content"])
        
    async def test_execute_custom_client(self):
        """Test weather tool execution with custom client"""
        tool = WeatherTool()
        tool.llm_client = MockLLMClient()
        params = {"location": "London", "units": "celsius"}
        
        result = await tool.execute(params)
        
        self.assertEqual(result["location"], "London")
        self.assertEqual(result["temperature"], 22)
        self.assertEqual(result["units"], "celsius")
        self.assertEqual(result["condition"], "sunny")
        self.assertEqual(result["description"], "Mock response") 