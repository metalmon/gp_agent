import unittest
from unittest.mock import Mock
from ...gameplan_ai_assistant.context.builder import GameplanContextBuilder
from ...gameplan_ai_assistant.context.base import Message, SystemContext

class TestGameplanContextBuilder(unittest.TestCase):
    def setUp(self):
        # Setup mock API
        self.api = Mock()
        self.api.get_discussion.return_value = {
            'name': 'DISC-1',
            'content': 'Test discussion',
            'owner': 'user1',
            'creation': '2024-01-01 10:00:00'
        }
        self.api.get_discussion_comments.return_value = [
            {
                'name': 'COMMENT-1',
                'content': 'Test comment',
                'owner': 'user2',
                'creation': '2024-01-01 10:01:00'
            }
        ]
        self.api.get_user.return_value = {
            'full_name': 'Test User',
            'email': 'test@example.com'
        }
        self.api.get_user_tasks.return_value = [
            {
                'id': 'TASK-1',
                'title': 'Test task'
            }
        ]

        # Setup settings
        self.settings = {
            'agent_user': 'agent1',
            'tools_prompt': 'Test tool instructions',
            'system_prompt': 'Test system prompt',
            'chat_memory': 10,
            'context_depth': 'Discussion Only',
            'registered_tools': {
                'test_tool': Mock(
                    description='Test tool description',
                    parameters={'param1': 'str'}
                )
            }
        }

        self.builder = GameplanContextBuilder(self.api, self.settings)

    def test_build_messages_context_with_last_message(self):
        """Test building messages context with last message having tool instructions"""
        messages = self.builder.build_messages_context(
            'DISC-1', 'PROJ-1', 'TEAM-1', 'COMMENT-1'
        )
        
        self.assertEqual(len(messages), 2)  # Discussion content + 1 comment
        
        # Check first message (discussion)
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[0].content, 'Test discussion')
        self.assertEqual(messages[0].context['user_metadata']['author'], 'user1')
        self.assertEqual(messages[0].context['user_metadata']['timestamp'], '2024-01-01 10:00:00')
        self.assertNotIn('tool_instructions', messages[0].context)
        
        # Check second message (comment)
        self.assertEqual(messages[1].role, 'user')
        self.assertEqual(messages[1].content, 'Test comment')
        self.assertEqual(messages[1].context['user_metadata']['author'], 'user2')
        self.assertEqual(messages[1].context['user_metadata']['timestamp'], '2024-01-01 10:01:00')
        self.assertEqual(messages[1].context['tool_instructions'], 'Test tool instructions')

    def test_build_messages_context_no_comments(self):
        """Test building messages context with no comments"""
        self.api.get_discussion_comments.return_value = []
        
        messages = self.builder.build_messages_context(
            'DISC-1', 'PROJ-1', 'TEAM-1'
        )
        
        self.assertEqual(len(messages), 1)  # Only discussion content
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[0].context['user_metadata']['author'], 'user1')
        self.assertEqual(messages[0].context['user_metadata']['timestamp'], '2024-01-01 10:00:00')
        self.assertEqual(messages[0].context['tool_instructions'], 'Test tool instructions')

    def test_build_tool_call_message(self):
        """Test building tool call message"""
        tool_calls = [{'id': 'call1', 'name': 'test_tool'}]
        message = self.builder.build_tool_call_message(
            tool_calls, 'agent1', '2024-01-01 10:00:00'
        )
        
        self.assertEqual(message.role, 'assistant')
        self.assertIsNone(message.content)
        self.assertEqual(message.tool_calls, tool_calls)
        self.assertEqual(message.context['user_metadata']['author'], 'agent1')
        self.assertEqual(message.context['user_metadata']['timestamp'], '2024-01-01 10:00:00')

    def test_get_available_tools(self):
        """Test getting available tools info"""
        tools = self.builder.get_available_tools()
        
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]['name'], 'test_tool')
        self.assertEqual(tools[0]['description'], 'Test tool description')
        self.assertEqual(tools[0]['parameters'], {'param1': 'str'})

    def test_build_tool_response_message(self):
        """Test building tool response message"""
        message = self.builder.build_tool_response_message(
            content='{"status": "success"}',
            tool_name='test_tool',
            tool_call_id='call1',
            timestamp='2024-01-01 10:00:00'
        )
        
        self.assertEqual(message.role, 'tool')
        self.assertEqual(message.content, '{"status": "success"}')
        self.assertEqual(message.tool_name, 'test_tool')
        self.assertEqual(message.tool_call_id, 'call1')
        self.assertEqual(message.context['user_metadata']['author'], 'agent1')
        self.assertEqual(message.context['user_metadata']['timestamp'], '2024-01-01 10:00:00')

    def test_get_override_settings(self):
        """Test getting override settings with correct precedence"""
        # Setup mock API responses for different levels
        self.api.get_team_settings_override.return_value = {
            'model': 'team-model',
            'temperature': 0.5,
            'top_p': 0.8
        }
        self.api.get_project_settings_override.return_value = {
            'model': 'project-model',
            'temperature': 0.6
        }
        self.api.get_discussion_settings_override.return_value = {
            'model': 'discussion-model'
        }

        # Get override settings
        settings = self.builder.get_override_settings(
            team_id='TEAM-1',
            project_id='PROJ-1',
            discussion_id='DISC-1'
        )

        # Check that settings are overridden with correct precedence
        self.assertEqual(settings['model'], 'discussion-model')  # From discussion
        self.assertEqual(settings['temperature'], 0.6)  # From project
        self.assertEqual(settings['top_p'], 0.8)  # From team
        self.assertEqual(settings['system_prompt'], 'Test system prompt')  # From base settings

        # Verify API calls
        self.api.get_team_settings_override.assert_called_once_with('TEAM-1')
        self.api.get_project_settings_override.assert_called_once_with('PROJ-1')
        self.api.get_discussion_settings_override.assert_called_once_with('DISC-1') 