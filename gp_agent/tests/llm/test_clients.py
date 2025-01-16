import unittest
from unittest.mock import Mock, patch
import frappe
import requests
from gp_agent.gameplan_ai_assistant.llm.base import BaseLLMClient
from gp_agent.gameplan_ai_assistant.llm.openai import OpenAIClient
from gp_agent.gameplan_ai_assistant.llm.schema import OpenAISchema

class TestBaseLLMClient(unittest.TestCase):
    """Test cases for BaseLLMClient"""
    
    def setUp(self):
        """Set up test environment"""
        self.settings_mock = Mock()
        self.settings_mock.model = "test-model"
        self.settings_mock.temperature = 0.7
        self.settings_mock.max_tokens = 1000
        self.settings_mock.top_p = 0.95
        
    def test_init_with_settings_override(self):
        """Test initialization with settings override"""
        class TestClient(BaseLLMClient):
            def chat_completion(self, *args, **kwargs):
                pass
                
        settings = {"test": "value"}
        client = TestClient(settings_override=settings)
        self.assertEqual(client.settings, settings)
        
    @patch('frappe.get_single')
    def test_init_without_settings_override(self, mock_get_single):
        """Test initialization without settings override"""
        class TestClient(BaseLLMClient):
            def chat_completion(self, *args, **kwargs):
                pass
                
        mock_get_single.return_value = self.settings_mock
        client = TestClient()
        self.assertEqual(client.settings, self.settings_mock)


class TestOpenAIClient(unittest.TestCase):
    """Test cases for OpenAIClient"""
    
    def setUp(self):
        """Set up test environment"""
        self.settings_mock = Mock()
        self.settings_mock.model = "test-model"
        self.settings_mock.temperature = 0.7
        self.settings_mock.max_tokens = 1000
        self.settings_mock.top_p = 0.95
        self.settings_mock.base_url = "https://test.api"
        self.settings_mock.get_password.return_value = "test-key"
        
        with patch('frappe.get_single', return_value=self.settings_mock):
            self.client = OpenAIClient()
            
    def test_get_headers(self):
        """Test header generation"""
        with patch('frappe.utils.get_url', return_value="http://test.local"):
            headers = self.client._get_headers()
            self.assertEqual(headers["Authorization"], "Bearer test-key")
            self.assertEqual(headers["HTTP-Referer"], "http://test.local")
            self.assertEqual(headers["Content-Type"], "application/json")
            
    @patch('requests.post')
    def test_chat_completion_success(self, mock_post):
        """Test successful chat completion request"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value = mock_response
        
        # Test request
        messages = [{"role": "user", "content": "test"}]
        response = self.client.chat_completion(messages)
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://test.api/chat/completions")
        
        # Verify request data
        request_data = call_args[1]["json"]
        self.assertEqual(request_data["model"], "test-model")
        self.assertEqual(request_data["temperature"], 0.7)
        self.assertEqual(request_data["max_tokens"], 1000)
        self.assertEqual(request_data["top_p"], 0.95)
        
        # Verify response
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["content"], "Test response")
        self.assertIsNone(response["tool_calls"])
        
    @patch('requests.post')
    def test_chat_completion_with_tools(self, mock_post):
        """Test chat completion with tools"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "test_tool",
                            "arguments": "{}"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }
        mock_post.return_value = mock_response
        
        # Test request with tools
        messages = [{"role": "user", "content": "test"}]
        tools = [{
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "Test tool",
                "parameters": {"type": "object", "properties": {}}
            }
        }]
        
        response = self.client.chat_completion(messages, tools=tools)
        
        # Verify tool_choice was set
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        self.assertEqual(request_data["tool_choice"], "auto")
        self.assertEqual(request_data["tools"], tools)
        
        # Verify response parsing
        self.assertEqual(response["type"], "tool_call")
        self.assertIsNone(response["content"])
        self.assertEqual(len(response["tool_calls"]), 1)
        self.assertEqual(response["tool_calls"][0]["function"]["name"], "test_tool")
        
    @patch('requests.post')
    def test_chat_completion_errors(self, mock_post):
        """Test error handling in chat completion"""
        messages = [{"role": "user", "content": "test"}]
        
        # Test 404 error
        mock_post.reset_mock()
        mock_response = Mock(status_code=404)
        exc = requests.exceptions.RequestException(response=mock_response)
        mock_post.side_effect = exc
        
        print("\nTesting 404 error:")
        print(f"Mock response status code: {mock_response.status_code}")
        print(f"Exception response: {exc.response}")
        print(f"Exception response status code: {exc.response.status_code}")
        
        try:
            self.client.chat_completion(messages)
            print("No exception was raised!")
        except Exception as e:
            print(f"Caught exception: {type(e)}")
            print(f"Exception message: {str(e)}")
            print(f"Exception cause: {e.__cause__}")
            
        # Test 429 error
        mock_post.reset_mock()
        mock_response = Mock(status_code=429)
        exc = requests.exceptions.RequestException(response=mock_response)
        mock_post.side_effect = exc
        
        print("\nTesting 429 error:")
        print(f"Mock response status code: {mock_response.status_code}")
        print(f"Exception response: {exc.response}")
        print(f"Exception response status code: {exc.response.status_code}")
        
        try:
            self.client.chat_completion(messages)
            print("No exception was raised!")
        except Exception as e:
            print(f"Caught exception: {type(e)}")
            print(f"Exception message: {str(e)}")
            print(f"Exception cause: {e.__cause__}")
            
        # Test refusal
        mock_post.reset_mock()
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": None,
                    "refusal": "Test refusal"
                },
                "finish_reason": "stop"
            }]
        }
        def raise_for_status():
            pass
        mock_response.raise_for_status = raise_for_status
        mock_post.side_effect = None
        mock_post.return_value = mock_response
        
        print("\nTesting refusal:")
        print(f"Mock response: {mock_response.json()}")
        print(f"Mock response status code: {mock_response.status_code}")
        
        try:
            self.client.chat_completion(messages)
            print("No exception was raised!")
        except Exception as e:
            print(f"Caught exception: {type(e)}")
            print(f"Exception message: {str(e)}")
            print(f"Exception cause: {e.__cause__}")
            
        # Now let's add assertions
        with self.assertRaises(frappe.exceptions.ValidationError) as cm:
            self.client.chat_completion(messages)
        self.assertEqual(str(cm.exception), "Model refused to respond: Test refusal") 