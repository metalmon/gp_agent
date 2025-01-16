import unittest
import frappe
import json
from unittest.mock import patch, MagicMock
from .test_base import GPAgentTestCase
from gp_agent.gameplan_ai_assistant.context.factory import ContextFactory
from gp_agent.gameplan_ai_assistant.utils.tool_caller import get_available_functions
from gp_agent.gameplan_ai_assistant.utils.naming import get_tool_log_name

class TestSchedulerJobs(GPAgentTestCase):
    def setUp(self):
        super().setUp()
        self.test_id = frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S%f')
        # Create a test GP Agent Log
        self.test_log = frappe.get_doc({
            "doctype": "GP Agent Log",
            "discussion_id": f"test_discussion_{self.test_id}",
            "model": "gpt-4",
            "status": "Queued",
            "creation_timestamp": frappe.utils.now_datetime(),
            "default_user": "Administrator",
            "team_id": f"test_team_{self.test_id}",
            "project_id": f"test_project_{self.test_id}",
            "last_messages": json.dumps({"xml": "<message>Test message</message>"}),
            "tasks": json.dumps({"xml": "<task>Test task</task>"}),
            "pages": json.dumps({"xml": "<page>Test page</page>"}),
            "polls": json.dumps({"xml": "<poll>Test poll</poll>"})
        }).insert()
        
        # Setup settings for context builder
        self.settings = {
            'api_schema': 'openai',
            'context_builder': 'default',
            'system_prompt': 'Test system prompt',
            'chat_memory': 10,
            'context_depth': 'Discussion Only',
            'default_user': 'Administrator'
        }
        
        # Create context builder and formatter
        self.builder, self.formatter = ContextFactory.create(self.settings)
    
    def tearDown(self):
        if hasattr(self, 'test_log'):
            self.test_log.delete()
        super().tearDown()

    @patch('gp_agent.gameplan_ai_assistant.scheduler_jobs.get_llm_client')
    def test_process_single_response(self, mock_get_llm_client):
        """Test processing a single agent response"""
        # Setup mock LLM client
        mock_client = MagicMock()
        mock_client.schema.parse_response.return_value = {
            "type": "message",
            "content": "Test response"
        }
        mock_client.get_token_usage.return_value = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
        mock_get_llm_client.return_value = mock_client
        
        # Process response
        from gp_agent.gameplan_ai_assistant.scheduler_jobs import process_single_response
        process_single_response(
            response_data={"test": "data"},
            log=self.test_log,
            llm_client=mock_client
        )
        
        # Reload log to get fresh state
        self.test_log.reload()
        
        # Verify response was processed
        self.assertEqual(self.test_log.status, "Completed")
        self.assertEqual(json.loads(self.test_log.response), {"test": "data"})
        self.assertEqual(self.test_log.prompt_tokens, 100)
        self.assertEqual(self.test_log.completion_tokens, 50)
        self.assertEqual(self.test_log.total_tokens, 150)
        
        # Verify client was created with correct settings
        mock_get_llm_client.assert_called_once_with({
            "model": self.test_log.model,
            "temperature": self.test_log.temperature,
            "max_tokens": self.test_log.max_tokens,
            "top_p": self.test_log.top_p
        })

    @patch('gp_agent.gameplan_ai_assistant.scheduler_jobs.get_llm_client')
    def test_process_tool_call_response(self, mock_get_llm_client):
        """Test processing a tool call response"""
        # Setup mock LLM client
        mock_client = MagicMock()
        mock_client.schema.parse_response.return_value = {
            "type": "tool_call",
            "tool_calls": [{
                "function": {
                    "name": "test_tool",
                    "arguments": json.dumps({"param": "value"})
                }
            }]
        }
        mock_client.get_token_usage.return_value = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
        mock_get_llm_client.return_value = mock_client
        
        # Process response
        from gp_agent.gameplan_ai_assistant.scheduler_jobs import process_single_response
        process_single_response(
            response_data={"test": "data"},
            log=self.test_log,
            llm_client=mock_client
        )
        
        # Reload log to get fresh state
        self.test_log.reload()
        
        # Verify response was processed
        self.assertEqual(self.test_log.status, "Completed")
        self.assertEqual(json.loads(self.test_log.response), {"test": "data"})
        self.assertEqual(self.test_log.prompt_tokens, 100)
        self.assertEqual(self.test_log.completion_tokens, 50)
        self.assertEqual(self.test_log.total_tokens, 150)
        
        # Verify tool log was created
        tool_log = frappe.get_doc("GP Agent Tool Log", {"parent_log": self.test_log.name})
        self.assertEqual(tool_log.tool_name, "test_tool")
        self.assertEqual(json.loads(tool_log.tool_parameters), {"param": "value"})
        self.assertEqual(tool_log.status, "Queued")
        
        # Verify client was created with correct settings
        mock_get_llm_client.assert_called_once_with({
            "model": self.test_log.model,
            "temperature": self.test_log.temperature,
            "max_tokens": self.test_log.max_tokens,
            "top_p": self.test_log.top_p
        }) 