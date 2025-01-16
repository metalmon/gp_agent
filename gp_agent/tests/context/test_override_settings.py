import unittest
from unittest.mock import Mock, patch
from ...gameplan_ai_assistant.context.builder import GameplanContextBuilder
from ...gameplan_ai_assistant.gameplan_api import GameplanAPI

class TestOverrideSettings(unittest.TestCase):
    def setUp(self):
        """Setup test environment with mock API"""
        self.api = Mock(spec=GameplanAPI)
        self.base_settings = {
            'system_prompt': 'Base prompt',
            'chat_memory': 10,
            'context_depth': 'Discussion Only',
            'agent_user': 'agent@test.com',
            'model': 'gpt-4'
        }
        self.builder = GameplanContextBuilder(self.api, self.base_settings)
        
        # Test IDs
        self.team_id = "TEAM-1"
        self.project_id = "PROJ-1"
        self.discussion_id = "DISC-1"
        
    def test_no_overrides(self):
        """Test when no overrides are present"""
        # Setup API to return no overrides
        self.api.get_team_settings_override.return_value = None
        self.api.get_project_settings_override.return_value = None
        self.api.get_discussion_settings_override.return_value = None
        
        settings = self.builder.get_override_settings(
            self.team_id,
            self.project_id,
            self.discussion_id
        )
        
        # Should return base settings unchanged
        self.assertEqual(settings, self.base_settings)
        
        # Verify all override methods were called
        self.api.get_team_settings_override.assert_called_once_with(self.team_id)
        self.api.get_project_settings_override.assert_called_once_with(self.project_id)
        self.api.get_discussion_settings_override.assert_called_once_with(self.discussion_id)
        
    def test_team_override(self):
        """Test team-level override"""
        team_override = {
            'system_prompt': 'Team prompt',
            'chat_memory': 20
        }
        self.api.get_team_settings_override.return_value = team_override
        self.api.get_project_settings_override.return_value = None
        self.api.get_discussion_settings_override.return_value = None
        
        settings = self.builder.get_override_settings(
            self.team_id,
            self.project_id,
            self.discussion_id
        )
        
        # Base settings should be updated with team override
        expected = self.base_settings.copy()
        expected.update(team_override)
        self.assertEqual(settings, expected)
        
    def test_project_override(self):
        """Test project-level override takes precedence over team"""
        team_override = {
            'system_prompt': 'Team prompt',
            'chat_memory': 20
        }
        project_override = {
            'system_prompt': 'Project prompt',
            'context_depth': 'Project Wide'
        }
        self.api.get_team_settings_override.return_value = team_override
        self.api.get_project_settings_override.return_value = project_override
        self.api.get_discussion_settings_override.return_value = None
        
        settings = self.builder.get_override_settings(
            self.team_id,
            self.project_id,
            self.discussion_id
        )
        
        # Project override should take precedence over team
        expected = self.base_settings.copy()
        expected.update(team_override)
        expected.update(project_override)
        self.assertEqual(settings, expected)
        self.assertEqual(settings['system_prompt'], 'Project prompt')  # Project wins
        self.assertEqual(settings['chat_memory'], 20)  # From team
        self.assertEqual(settings['context_depth'], 'Project Wide')  # From project
        
    def test_discussion_override(self):
        """Test discussion-level override takes highest precedence"""
        team_override = {
            'system_prompt': 'Team prompt',
            'chat_memory': 20
        }
        project_override = {
            'system_prompt': 'Project prompt',
            'context_depth': 'Project Wide'
        }
        discussion_override = {
            'system_prompt': 'Discussion prompt',
            'model': 'gpt-3.5-turbo'
        }
        self.api.get_team_settings_override.return_value = team_override
        self.api.get_project_settings_override.return_value = project_override
        self.api.get_discussion_settings_override.return_value = discussion_override
        
        settings = self.builder.get_override_settings(
            self.team_id,
            self.project_id,
            self.discussion_id
        )
        
        # Discussion override should take highest precedence
        expected = self.base_settings.copy()
        expected.update(team_override)
        expected.update(project_override)
        expected.update(discussion_override)
        self.assertEqual(settings, expected)
        self.assertEqual(settings['system_prompt'], 'Discussion prompt')  # Discussion wins
        self.assertEqual(settings['chat_memory'], 20)  # From team
        self.assertEqual(settings['context_depth'], 'Project Wide')  # From project
        self.assertEqual(settings['model'], 'gpt-3.5-turbo')  # From discussion
        
    def test_override_in_system_context(self):
        """Test that system context builder uses override settings"""
        discussion_override = {
            'system_prompt': 'Discussion prompt',
            'chat_memory': 5,
            'context_depth': 'Team Wide'
        }
        self.api.get_team_settings_override.return_value = None
        self.api.get_project_settings_override.return_value = None
        self.api.get_discussion_settings_override.return_value = discussion_override
        
        # Mock other API calls needed by build_system_context
        self.api.get_discussion.return_value = {'owner': 'user1'}
        self.api.get_discussion_comments.return_value = []
        self.api.get_project_tasks.return_value = []
        self.api.get_team_projects.return_value = []
        
        context = self.builder.build_system_context(
            self.discussion_id,
            self.project_id,
            self.team_id
        )
        
        # Verify override settings were used
        self.assertEqual(context.base_instructions, 'Discussion prompt')
        
        # Verify API calls used overridden chat_memory
        self.api.get_project_tasks.assert_called_with(self.project_id, limit=5)
        
    def test_override_in_messages_context(self):
        """Test that messages context builder uses override settings"""
        project_override = {
            'chat_memory': 3
        }
        self.api.get_team_settings_override.return_value = None
        self.api.get_project_settings_override.return_value = project_override
        self.api.get_discussion_settings_override.return_value = None
        
        # Mock API responses
        self.api.get_discussion.return_value = {
            'content': 'Discussion content',
            'owner': 'user1',
            'creation': '2024-01-01'
        }
        self.api.get_user.return_value = {
            'full_name': 'Test User',
            'email': 'test@example.com'
        }
        self.api.get_discussion_comments.return_value = [
            {
                'content': f'Comment {i}',
                'owner': f'user{i}',
                'creation': f'2024-01-0{i+1}'
            }
            for i in range(5)  # More comments than chat_memory
        ]
        
        messages = self.builder.build_messages_context(
            self.discussion_id,
            self.project_id,
            self.team_id
        )
        
        # Verify override chat_memory was used for all API calls
        self.api.get_discussion_comments.assert_called_with(self.discussion_id, limit=3)
        
        # Verify get_user_tasks was called for each user with correct chat_memory
        for i in range(5):
            self.api.get_user_tasks.assert_any_call(f'user{i}', project_id=self.project_id, limit=3)
        
    def test_related_content_discussion_only(self):
        """Test related content with Discussion Only depth"""
        settings = self.base_settings.copy()
        settings['context_depth'] = 'Discussion Only'
        settings['chat_memory'] = 5
        
        # Mock API responses
        self.api.get_project_pages.return_value = [
            {'id': 'page1', 'title': 'Page 1'},
            {'id': 'page2', 'title': 'Page 2'}
        ]
        
        project_pages, related_discussions, related_tasks, related_pages, related_messages = (
            self.builder._get_related_content(
                self.discussion_id,
                self.project_id,
                self.team_id,
                settings
            )
        )
        
        # Should return current project pages but no related content
        self.assertEqual(len(project_pages), 2)
        self.assertEqual(len(related_discussions), 0)
        self.assertEqual(len(related_tasks), 0)
        self.assertEqual(len(related_pages), 0)
        self.assertEqual(len(related_messages), 0)
        
        # Verify API calls
        self.api.get_project_pages.assert_called_once_with(self.project_id, limit=5)
        self.api.get_project_discussions.assert_not_called()
        self.api.get_team_projects.assert_not_called()
        
    def test_related_content_project_wide(self):
        """Test related content with Project Wide depth"""
        settings = self.base_settings.copy()
        settings['context_depth'] = 'Project Wide'
        settings['chat_memory'] = 5
        
        # Mock API responses
        self.api.get_project_pages.return_value = [
            {'id': 'page1', 'title': 'Page 1'}
        ]
        self.api.get_project_discussions.return_value = [
            {
                'name': 'disc1',
                'title': 'Discussion 1',
                'content': 'Content 1',
                'owner': 'user1',
                'creation': '2024-01-01',
                'modified': '2024-01-02'
            },
            {
                'name': self.discussion_id,  # Should be skipped
                'title': 'Current Discussion'
            }
        ]
        self.api.get_discussion_comments.return_value = [
            {
                'content': 'Comment 1',
                'owner': 'user2',
                'creation': '2024-01-03'
            }
        ]
        
        project_pages, related_discussions, related_tasks, related_pages, related_messages = (
            self.builder._get_related_content(
                self.discussion_id,
                self.project_id,
                self.team_id,
                settings
            )
        )
        
        # Should return current project pages and related discussions
        self.assertEqual(len(project_pages), 1)
        self.assertEqual(len(related_discussions), 1)
        self.assertEqual(related_discussions[0]['title'], 'Discussion 1')
        self.assertEqual(len(related_messages), 1)
        self.assertEqual(related_messages[0]['author'], 'user2')
        
        # No tasks or pages from other projects
        self.assertEqual(len(related_tasks), 0)
        self.assertEqual(len(related_pages), 0)
        
        # Verify API calls
        self.api.get_project_pages.assert_called_once_with(self.project_id, limit=5)
        self.api.get_project_discussions.assert_called_once_with(self.project_id, limit=5)
        self.api.get_team_projects.assert_not_called()
        
    def test_related_content_team_wide(self):
        """Test related content with Team Wide depth"""
        settings = self.base_settings.copy()
        settings['context_depth'] = 'Team Wide'
        settings['chat_memory'] = 5
        
        # Mock API responses
        self.api.get_project_pages.side_effect = [
            # Current project pages
            [{'id': 'page1', 'title': 'Current Page'}],
            # Other project pages
            [{'id': 'page2', 'title': 'Other Page'}],
            # Add one more response for the current project check
            [{'id': 'page3', 'title': 'Skip Page'}]
        ]
        
        other_proj = Mock(name='other_proj')
        other_proj.name = 'other_proj'
        current_proj = Mock(name=self.project_id)
        current_proj.name = self.project_id
        
        self.api.get_team_projects.return_value = [
            other_proj,  # Different project
            current_proj  # Current project, should be skipped
        ]
        self.api.get_project_discussions.return_value = [
            {
                'name': 'disc1',
                'title': 'Discussion 1',
                'content': 'Content 1',
                'owner': 'user1',
                'creation': '2024-01-01',
                'modified': '2024-01-02'
            }
        ]
        self.api.get_discussion_comments.return_value = [
            {
                'content': 'Comment 1',
                'owner': 'user2',
                'creation': '2024-01-03'
            }
        ]
        self.api.get_project_tasks.return_value = [
            {
                'id': 'task1',
                'title': 'Task 1',
                'status': 'Open',
                'assigned_to': 'user1'
            }
        ]
        
        project_pages, related_discussions, related_tasks, related_pages, related_messages = (
            self.builder._get_related_content(
                self.discussion_id,
                self.project_id,
                self.team_id,
                settings
            )
        )
        
        # Should return content from all levels
        self.assertEqual(len(project_pages), 1)
        self.assertEqual(project_pages[0]['title'], 'Current Page')
        
        self.assertEqual(len(related_discussions), 1)
        self.assertEqual(related_discussions[0]['title'], 'Discussion 1')
        self.assertEqual(related_discussions[0]['project'], 'other_proj')  # From other project
        
        self.assertEqual(len(related_messages), 1)
        self.assertEqual(related_messages[0]['author'], 'user2')
        self.assertEqual(related_messages[0]['project'], 'other_proj')  # From other project
        
        self.assertEqual(len(related_tasks), 1)
        self.assertEqual(related_tasks[0]['title'], 'Task 1')
        self.assertEqual(related_tasks[0]['project'], 'other_proj')  # From other project
        
        self.assertEqual(len(related_pages), 1)
        self.assertEqual(related_pages[0]['title'], 'Other Page')
        self.assertEqual(related_pages[0]['project'], 'other_proj')  # From other project
        
        # Verify API calls
        self.assertEqual(self.api.get_project_pages.call_count, 2)  # Current + other project
        self.api.get_team_projects.assert_called_once_with(self.team_id)
        self.api.get_project_discussions.assert_called_once_with('other_proj', limit=5) 