import os
import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from ..profiler import ModelProfiler
import frappe

class TestModelProfiler(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_results"
        
        # Mock GP Agent Settings
        self.settings_mock = MagicMock()
        self.settings_mock.get_password.return_value = "test_key"
        self.settings_mock.base_url = "https://test.api/v1"
        self.settings_mock.model = "test-model"
        self.settings_mock.temperature = 0.7
        self.settings_mock.max_tokens = 1000
        self.settings_mock.top_p = 1.0
        self.settings_mock.max_retries = 3
        self.settings_mock.retry_delay = 0
        self.settings_mock.request_timeout = 30
        
        # Patch frappe.get_doc to return our mock
        self.get_doc_patcher = patch('frappe.get_doc')
        self.mock_get_doc = self.get_doc_patcher.start()
        self.mock_get_doc.return_value = self.settings_mock
        
        self.profiler = ModelProfiler(output_dir=self.test_dir)
        
        # Create test directory
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
    
    def tearDown(self):
        # Remove test files and directory
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)
        
        # Stop patching frappe.get_doc
        self.get_doc_patcher.stop()
    
    @patch('requests.post')
    def test_make_request_success(self, mock_post):
        # Prepare successful response mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": "test response"}]}
        mock_post.return_value = mock_response
        
        response = self.profiler._make_request("test system prompt", "test user prompt")
        
        # Check that request was made with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['headers']['Authorization'], f"Bearer test_key")
        self.assertEqual(kwargs['json']['messages'][0]['content'], "test system prompt")
        self.assertEqual(kwargs['json']['messages'][1]['content'], "test user prompt")
        self.assertEqual(kwargs['json']['model'], "test-model")
        self.assertEqual(kwargs['json']['temperature'], 0.7)
        self.assertEqual(kwargs['json']['max_tokens'], 1000)
        self.assertEqual(kwargs['json']['top_p'], 1.0)
        
        # Check response
        self.assertEqual(response, {"choices": [{"message": "test response"}]})

    @patch('requests.post')
    def test_make_request_rate_limit(self, mock_post):
        # Prepare sequence of responses: rate limit first, then success
        mock_rate_limit = MagicMock()
        mock_rate_limit.status_code = 429
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"choices": [{"message": "test response"}]}
        
        mock_post.side_effect = [mock_rate_limit, mock_success]
        
        response = self.profiler._make_request("test system prompt", "test user prompt")
        
        # Check that there were two attempts
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response, {"choices": [{"message": "test response"}]})
    
    @patch('requests.post')
    def test_make_request_max_retries(self, mock_post):
        # Prepare mock for constant errors
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        response = self.profiler._make_request("test system prompt", "test user prompt")
        
        # Check that correct number of attempts was made
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(response, {"error": "Max retries exceeded"})

    def test_save_result(self):
        # Prepare test data
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis"
        }
        system_prompt = "test system prompt"
        user_prompt = "test user prompt"
        response = {"choices": [{"message": "test response"}]}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save result
        self.profiler._save_result(hypothesis, system_prompt, user_prompt, response, timestamp)
        
        # Check that file was created and contains correct data
        filename = f"{self.test_dir}/test_hypothesis_{timestamp}.json"
        self.assertTrue(os.path.exists(filename))
        
        with open(filename, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            
        self.assertEqual(saved_data['hypothesis'], hypothesis)
        self.assertEqual(saved_data['system_prompt'], system_prompt)
        self.assertEqual(saved_data['user_prompt'], user_prompt)
        self.assertEqual(saved_data['response'], response)
        self.assertEqual(saved_data['timestamp'], timestamp)
    
    @patch.object(ModelProfiler, '_make_request')
    @patch.object(ModelProfiler, '_save_result')
    def test_test_hypothesis(self, mock_save, mock_request):
        # Prepare test hypothesis
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis",
            "system_prompts": ["test system prompt"]
        }
        
        # Prepare test prompts
        test_prompts = ["test user prompt"]
        
        # Prepare mock response
        mock_request.return_value = {"choices": [{"message": "test response"}]}
        
        # Run hypothesis testing
        self.profiler.test_hypothesis(hypothesis, test_prompts)
        
        # Check that request and save were called
        mock_request.assert_called_once_with("test system prompt", "test user prompt", mock.ANY, mock.ANY)
        mock_save.assert_called_once()
        
        # Check save parameters
        args, _ = mock_save.call_args
        expected_hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis",
            "system_prompts": ["test system prompt"]
        }
        self.assertEqual(args[0], expected_hypothesis)
        self.assertEqual(args[1], "test system prompt")
        self.assertEqual(args[2], "test user prompt")
        self.assertEqual(args[3], {"choices": [{"message": "test response"}]})

    def test_make_request_includes_functions(self):
        """Test that request includes functions by default"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": "test response"}]}
            mock_post.return_value = mock_response
            
            response = self.profiler._make_request("test system prompt", "test user prompt", "current prompt")
            
            # Check that functions were included in request
            args, kwargs = mock_post.call_args
            self.assertIn("functions", kwargs["json"])
            self.assertGreater(len(kwargs["json"]["functions"]), 0)
            self.assertEqual(kwargs["json"]["function_call"], "auto")
            
            # Check that all required functions are present
            function_names = {f["name"] for f in kwargs["json"]["functions"]}
            required_functions = {
                "list_tasks", "get_task_details", "update_task",
                "create_task_dependency", "get_task_dependencies",
                "analyze_critical_path", "find_similar_tasks",
                "web_search", "get_webpage_content", "list_pages",
                "get_page_content", "get_discussion_comments"
            }
            self.assertEqual(function_names, required_functions)
            
            # Check that functions have correct structure
            for function in kwargs["json"]["functions"]:
                self.assertIn("name", function)
                self.assertIn("description", function)
                self.assertIn("parameters", function)
                self.assertEqual(function["parameters"]["type"], "object")
                self.assertIn("properties", function["parameters"])

    def test_analyze_function_usage(self):
        # Prepare test response with function calls
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "test_func",
                        "arguments": '{"param": "value"}'
                    }
                }
            }]
        }
        
        # Analyze function usage
        analysis = self.profiler._analyze_function_usage(response)
        
        # Check analysis results
        self.assertEqual(analysis["total_calls"], 1)
        self.assertEqual(len(analysis["function_calls"]), 1)
        self.assertEqual(analysis["function_calls"][0]["name"], "test_func")
        self.assertEqual(analysis["function_calls"][0]["arguments"], {"param": "value"})
        self.assertEqual(analysis["unique_functions"], ["test_func"])
        self.assertEqual(len(analysis["errors"]), 0)

    def test_analyze_function_usage_with_invalid_json(self):
        # Prepare test response with invalid JSON in arguments
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "test_func",
                        "arguments": "invalid json"
                    }
                }
            }]
        }
        
        # Analyze function usage
        analysis = self.profiler._analyze_function_usage(response)
        
        # Check analysis results
        self.assertEqual(analysis["total_calls"], 1)
        self.assertEqual(len(analysis["function_calls"]), 1)
        self.assertEqual(analysis["function_calls"][0]["name"], "test_func")
        self.assertEqual(analysis["function_calls"][0]["arguments"], "invalid json")
        self.assertEqual(len(analysis["errors"]), 1)
        self.assertTrue("Failed to parse arguments" in analysis["errors"][0])

    def test_save_result_with_function_analysis(self):
        # Prepare test data
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis"
        }
        system_prompt = "test system prompt"
        user_prompt = "test user prompt"
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "test_func",
                        "arguments": '{"param": "value"}'
                    }
                }
            }]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save result
        self.profiler._save_result(hypothesis, system_prompt, user_prompt, response, timestamp)
        
        # Check that file was created and contains correct data
        filename = f"{self.test_dir}/test_hypothesis_{timestamp}.json"
        self.assertTrue(os.path.exists(filename))
        
        with open(filename, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            
        self.assertIn("function_analysis", saved_data)
        self.assertEqual(saved_data["function_analysis"]["total_calls"], 1)
        self.assertEqual(len(saved_data["function_analysis"]["function_calls"]), 1)
        self.assertEqual(saved_data["function_analysis"]["function_calls"][0]["name"], "test_func")

    def test_analyze_function_usage_multiple_calls(self):
        # Prepare test response with multiple function calls
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "list_tasks",
                        "arguments": '{"status": "In Progress"}'
                    }
                }
            }, {
                "message": {
                    "function_call": {
                        "name": "get_task_details",
                        "arguments": '{"task_id": "123"}'
                    }
                }
            }]
        }
        
        # Analyze function usage
        analysis = self.profiler._analyze_function_usage(response)
        
        # Check analysis results
        self.assertEqual(analysis["total_calls"], 2)
        self.assertEqual(len(analysis["function_calls"]), 2)
        self.assertEqual(len(analysis["unique_functions"]), 2)
        self.assertEqual(analysis["function_calls"][0]["name"], "list_tasks")
        self.assertEqual(analysis["function_calls"][1]["name"], "get_task_details")
        self.assertEqual(len(analysis["errors"]), 0)

    def test_analyze_function_usage_with_errors(self):
        # Prepare test response with various error cases
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "invalid_function",
                        "arguments": '{"param": "value"}'
                    }
                }
            }, {
                "message": {
                    "function_call": None
                }
            }, {
                "message": {
                    "function_call": {
                        "name": "list_tasks",
                        "arguments": "invalid json here"
                    }
                }
            }]
        }
        
        # Analyze function usage
        analysis = self.profiler._analyze_function_usage(response)
        
        # Check analysis results
        self.assertEqual(analysis["total_calls"], 2)  # Only count actual function calls
        self.assertEqual(len(analysis["function_calls"]), 2)
        self.assertTrue(len(analysis["errors"]) > 0)
        self.assertTrue(any("Failed to parse arguments" in error for error in analysis["errors"]))

    def test_save_result_with_multiple_function_analysis(self):
        # Prepare test data with multiple function calls
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis"
        }
        system_prompt = "test system prompt"
        user_prompt = "test user prompt"
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "list_tasks",
                        "arguments": '{"status": "In Progress"}'
                    }
                }
            }, {
                "message": {
                    "function_call": {
                        "name": "get_task_details",
                        "arguments": '{"task_id": "123"}'
                    }
                }
            }]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save result
        self.profiler._save_result(hypothesis, system_prompt, user_prompt, response, timestamp)
        
        # Check that file was created and contains correct data
        filename = f"{self.test_dir}/test_hypothesis_{timestamp}.json"
        self.assertTrue(os.path.exists(filename))
        
        with open(filename, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            
        self.assertIn("function_analysis", saved_data)
        self.assertEqual(saved_data["function_analysis"]["total_calls"], 2)
        self.assertEqual(len(saved_data["function_analysis"]["function_calls"]), 2)
        self.assertEqual(len(saved_data["function_analysis"]["unique_functions"]), 2)
        self.assertEqual(saved_data["function_analysis"]["function_calls"][0]["name"], "list_tasks")
        self.assertEqual(saved_data["function_analysis"]["function_calls"][1]["name"], "get_task_details")

    def test_save_result_updates_stats(self):
        """Test that save_result updates function usage statistics"""
        from ..run_profiling import TestStats
        
        # Prepare test data
        stats = TestStats()
        profiler = ModelProfiler(output_dir=self.test_dir, stats=stats)
        
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis"
        }
        system_prompt = "test system prompt"
        user_prompt = "test user prompt"
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "list_tasks",
                        "arguments": '{"status": "In Progress"}'
                    }
                }
            }, {
                "message": {
                    "function_call": {
                        "name": "get_task_details",
                        "arguments": '{"task_id": "123"}'
                    }
                }
            }]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save result
        profiler._save_result(hypothesis, system_prompt, user_prompt, response, timestamp)
        
        # Check that statistics were updated
        self.assertEqual(stats.total_function_calls, 2)
        self.assertEqual(len(stats.unique_functions_used), 2)
        self.assertEqual(stats.function_calls_by_name["list_tasks"], 1)
        self.assertEqual(stats.function_calls_by_name["get_task_details"], 1)
        self.assertEqual(len(stats.function_errors), 0)

    def test_save_result_updates_stats_with_errors(self):
        """Test that save_result updates function error statistics"""
        from ..run_profiling import TestStats
        
        # Prepare test data
        stats = TestStats()
        profiler = ModelProfiler(output_dir=self.test_dir, stats=stats)
        
        hypothesis = {
            "name": "test_hypothesis",
            "description": "Test hypothesis"
        }
        system_prompt = "test system prompt"
        user_prompt = "test user prompt"
        response = {
            "choices": [{
                "message": {
                    "function_call": {
                        "name": "list_tasks",
                        "arguments": "invalid json"
                    }
                }
            }]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save result
        profiler._save_result(hypothesis, system_prompt, user_prompt, response, timestamp)
        
        # Check that error statistics were updated
        self.assertEqual(stats.total_function_calls, 1)
        self.assertEqual(len(stats.unique_functions_used), 1)
        self.assertEqual(stats.function_calls_by_name["list_tasks"], 1)
        self.assertEqual(len(stats.function_errors), 1)
        self.assertEqual(stats.function_errors["parse_error"], 1)

if __name__ == '__main__':
    unittest.main() 