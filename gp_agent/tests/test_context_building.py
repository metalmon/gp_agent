import unittest
import frappe
import json
from unittest.mock import patch, MagicMock
from .test_base import GPAgentTestCase
from gp_agent.gameplan_ai_assistant.context.factory import ContextFactory
from gp_agent.gameplan_ai_assistant.utils.tool_caller import get_available_functions
from gp_agent.gameplan_ai_assistant.utils.naming import get_tool_log_name

class TestContextBuilding(GPAgentTestCase):
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

    def test_basic_context_without_functions(self):
        """Test basic context building without functions"""
        test_id = frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S%f')
        # Create a log with only messages
        basic_log = frappe.get_doc({
            "doctype": "GP Agent Log",
            "discussion_id": f"test_discussion_{test_id}",
            "model": "gpt-4",
            "status": "Queued",
            "creation_timestamp": frappe.utils.now_datetime(),
            "default_user": "Administrator",
            "team_id": f"test_team_{test_id}",
            "project_id": f"test_project_{test_id}",
            "last_messages": json.dumps({"xml": "<message>Test message</message>"})
        }).insert()
        
        try:
            # Build context using new builder and formatter
            system_context = self.builder.build_system_context(
                discussion_id=basic_log.discussion_id,
                team_id=basic_log.team_id,
                project_id=basic_log.project_id
            )
            
            messages_context = self.builder.build_messages_context(
                discussion_id=basic_log.discussion_id,
                team_id=basic_log.team_id,
                project_id=basic_log.project_id
            )
            
            formatted_context = self.formatter.format_context(system_context, messages_context)
            
            # Basic structure checks
            self.assertIsNotNone(formatted_context)
            self.assertIn("Test system prompt", formatted_context)
            
            # Should contain message but not other sections
            self.assertIn("Test message", formatted_context)
            
        finally:
            basic_log.delete()

    def test_full_context(self):
        """Test context building with all possible sections"""
        # Build context using new builder and formatter
        system_context = self.builder.build_system_context(
            discussion_id=self.test_log.discussion_id,
            team_id=self.test_log.team_id,
            project_id=self.test_log.project_id
        )
        
        messages_context = self.builder.build_messages_context(
            discussion_id=self.test_log.discussion_id,
            team_id=self.test_log.team_id,
            project_id=self.test_log.project_id
        )
        
        formatted_context = self.formatter.format_context(system_context, messages_context)
        
        # Check that context contains all necessary information
        self.assertIsNotNone(formatted_context)
        self.assertIn("Test system prompt", formatted_context)
        self.assertIn("Test message", formatted_context)
        
        # Check that tools are included
        tools = self.builder.get_tools_info()
        for tool in tools:
            self.assertIn(tool['name'], formatted_context)
            self.assertIn(tool['description'], formatted_context)
        
    def test_empty_sections_handling(self):
        """Test handling of empty or None sections"""
        test_id = frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S%f')
        empty_log = frappe.get_doc({
            "doctype": "GP Agent Log",
            "discussion_id": f"test_discussion_{test_id}",
            "model": "gpt-4",
            "status": "Queued",
            "creation_timestamp": frappe.utils.now_datetime(),
            "default_user": "Administrator",
            "team_id": f"test_team_{test_id}",
            "project_id": f"test_project_{test_id}"
        }).insert()
        
        try:
            # Build context using new builder and formatter
            system_context = self.builder.build_system_context(
                discussion_id=empty_log.discussion_id,
                team_id=empty_log.team_id,
                project_id=empty_log.project_id
            )
            
            messages_context = self.builder.build_messages_context(
                discussion_id=empty_log.discussion_id,
                team_id=empty_log.team_id,
                project_id=empty_log.project_id
            )
            
            formatted_context = self.formatter.format_context(system_context, messages_context)
            
            # Check that context still contains system prompt and tools
            self.assertIsNotNone(formatted_context)
            self.assertIn("Test system prompt", formatted_context)
            
            # Check that tools are included
            tools = self.builder.get_tools_info()
            for tool in tools:
                self.assertIn(tool['name'], formatted_context)
                self.assertIn(tool['description'], formatted_context)
            
        finally:
            empty_log.delete() 