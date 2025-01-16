import frappe
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from gp_agent.gameplan_ai_assistant.tools.discussion.get_comments import GetCommentsDiscussionTool

class TestGetCommentsDiscussionTool(unittest.TestCase):
    def setUp(self):
        self.discussion_id = "test_discussion_1"
        self.tool = GetCommentsDiscussionTool()
        self.test_data = {
            "discussion_id": self.discussion_id
        }
        self.test_comments = [
            MagicMock(
                name="comment_1",
                owner="user1",
                creation=datetime(2024, 1, 24, 12, 0),
                content="First comment"
            ),
            MagicMock(
                name="comment_2",
                owner="user2",
                creation=datetime(2024, 1, 24, 13, 0),
                content="Second comment"
            ),
            MagicMock(
                name="comment_3",
                owner="user3",
                creation=datetime(2024, 1, 24, 14, 0),
                content="Third comment"
            )
        ]
        
    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "get_discussion_comments")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("discussion_id", params["required"])
        self.assertIn("limit", params["properties"])
        self.assertIn("before_id", params["properties"])
        self.assertIn("after_id", params["properties"])
        
    @patch('gp_agent.gameplan_ai_assistant.tools.discussion.base.frappe')
    async def test_validate_access(self, mock_frappe):
        """Test access validation"""
        # Setup mocks
        mock_discussion = MagicMock()
        mock_discussion.project = "test_project"
        mock_project = MagicMock()
        mock_project.has_permission.return_value = True
        mock_frappe.get_doc.side_effect = [mock_discussion, mock_project]
        
        # Test successful validation
        self.tool.validate_access(self.discussion_id)
        mock_project.has_permission.assert_called_once_with("read")
        
        # Test permission error
        mock_project.has_permission.return_value = False
        mock_frappe.PermissionError = Exception
        with self.assertRaises(Exception):
            self.tool.validate_access(self.discussion_id)
            
    @patch('gp_agent.gameplan_ai_assistant.tools.discussion.base.frappe')
    @patch('gp_agent.gameplan_ai_assistant.tools.discussion.base.GameplanAPI')
    async def test_get_comments_basic(self, mock_api_class, mock_frappe):
        """Test basic comment retrieval"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_discussion_comments.return_value = self.test_comments
        mock_api_class.return_value = mock_api
        
        # Setup permission mock
        mock_discussion = MagicMock()
        mock_discussion.project = "test_project"
        mock_project = MagicMock()
        mock_project.has_permission.return_value = True
        mock_frappe.get_doc.side_effect = [mock_discussion, mock_project]
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_discussion_comments.assert_called_once_with(
            discussion_id=self.discussion_id,
            limit=10
        )
        
        # Verify result format
        self.assertIn("messages", result)
        messages = result["messages"]
        self.assertEqual(len(messages), 3)
        
        first_message = messages[0]
        self.assertEqual(first_message["id"], "comment_1")
        self.assertEqual(first_message["author"], "user1")
        self.assertEqual(first_message["content"], "First comment")
        self.assertEqual(first_message["timestamp"], str(datetime(2024, 1, 24, 12, 0))) 