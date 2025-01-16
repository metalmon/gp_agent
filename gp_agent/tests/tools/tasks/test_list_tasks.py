import unittest
import frappe
from unittest.mock import patch, MagicMock
from datetime import datetime

from ....gameplan_ai_assistant.tools.tasks.list_tasks import list_tasks
from ...test_base import GPAgentTestCase

class TestListTasks(GPAgentTestCase):
    def setUp(self):
        super().setUp()
        self.test_project_id = "test_project_123"
        self.mock_tasks = [
            {
                "name": "task_1",
                "title": "Task 1",
                "description": "<p>Task 1 description</p>",
                "status": "Todo",
                "priority": "High",
                "start_date": "2024-01-24",
                "due_date": "2024-02-01",
                "is_completed": 0,
                "assigned_to": "user_1",
                "comments_count": 2,
                "idx": 1,
                "modified": "2024-01-24T12:00:00"
            },
            {
                "name": "task_2",
                "title": "Task 2",
                "description": "<p>Task 2 description</p>",
                "status": "In Progress",
                "priority": "Medium",
                "start_date": None,
                "due_date": None,
                "is_completed": 0,
                "assigned_to": "user_2",
                "comments_count": 0,
                "idx": 2,
                "modified": "2024-01-24T12:00:00"
            }
        ]
        
    def test_list_tasks_no_filters(self):
        """Test listing tasks without filters"""
        with patch("gp_agent.gameplan_ai_assistant.gameplan_api.frappe") as mock_frappe:
            # Mock get_all to return our test tasks
            mock_tasks = []
            for task in self.mock_tasks:
                mock_task = MagicMock()
                for key, value in task.items():
                    setattr(mock_task, key, value)
                mock_tasks.append(mock_task)
            mock_frappe.get_all.return_value = mock_tasks
            
            # Call the function
            result = list_tasks(self.test_project_id)
            
            # Verify frappe.get_all was called correctly
            mock_frappe.get_all.assert_called_once()
            call_args = mock_frappe.get_all.call_args[1]
            self.assertEqual(call_args["filters"], {"project": self.test_project_id})
            
            # Verify the result
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["id"], "task_1")
            self.assertEqual(result[1]["id"], "task_2")
            
    def test_list_tasks_with_status_filter(self):
        """Test listing tasks with status filter"""
        with patch("gp_agent.gameplan_ai_assistant.gameplan_api.frappe") as mock_frappe:
            # Mock get_all to return filtered tasks
            filtered_tasks = [task for task in self.mock_tasks if task["status"] == "Todo"]
            mock_tasks = []
            for task in filtered_tasks:
                mock_task = MagicMock()
                for key, value in task.items():
                    setattr(mock_task, key, value)
                mock_tasks.append(mock_task)
            mock_frappe.get_all.return_value = mock_tasks
            
            # Call the function with status filter
            result = list_tasks(self.test_project_id, status=["Todo"])
            
            # Verify frappe.get_all was called correctly
            mock_frappe.get_all.assert_called_once()
            call_args = mock_frappe.get_all.call_args[1]
            self.assertEqual(
                call_args["filters"],
                {"project": self.test_project_id, "status": ["in", ["Todo"]]}
            )
            
            # Verify the result
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "task_1")
            self.assertEqual(result[0]["status"], "Todo")
            
    def test_list_tasks_with_assignee_filter(self):
        """Test listing tasks with assignee filter"""
        with patch("gp_agent.gameplan_ai_assistant.gameplan_api.frappe") as mock_frappe:
            # Mock get_all to return filtered tasks
            filtered_tasks = [task for task in self.mock_tasks if task["assigned_to"] == "user_1"]
            mock_tasks = []
            for task in filtered_tasks:
                mock_task = MagicMock()
                for key, value in task.items():
                    setattr(mock_task, key, value)
                mock_tasks.append(mock_task)
            mock_frappe.get_all.return_value = mock_tasks
            
            # Call the function with assignee filter
            result = list_tasks(self.test_project_id, assigned_to="user_1")
            
            # Verify frappe.get_all was called correctly
            mock_frappe.get_all.assert_called_once()
            call_args = mock_frappe.get_all.call_args[1]
            self.assertEqual(
                call_args["filters"],
                {"project": self.test_project_id, "assigned_to": "user_1"}
            )
            
            # Verify the result
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "task_1")
            self.assertEqual(result[0]["assigned_to"], "user_1")
            
    def test_list_tasks_with_invalid_status(self):
        """Test listing tasks with invalid status filter"""
        with patch("gp_agent.gameplan_ai_assistant.gameplan_api.frappe") as mock_frappe:
            # Mock get_all to return all tasks since invalid status should be ignored
            mock_tasks = []
            for task in self.mock_tasks:
                mock_task = MagicMock()
                for key, value in task.items():
                    setattr(mock_task, key, value)
                mock_tasks.append(mock_task)
            mock_frappe.get_all.return_value = mock_tasks
            
            # Call the function with invalid status
            result = list_tasks(self.test_project_id, status=["Invalid Status"])
            
            # Verify frappe.get_all was called correctly
            mock_frappe.get_all.assert_called_once()
            call_args = mock_frappe.get_all.call_args[1]
            self.assertEqual(call_args["filters"], {"project": self.test_project_id})
            
            # Verify all tasks are returned
            self.assertEqual(len(result), 2) 