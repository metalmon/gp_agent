import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.find_similar_tasks import FindSimilarTasksTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestFindSimilarTasksTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.task_id = "task-123"
        self.tool = FindSimilarTasksTool()
        self.test_data = {
            "task_id": self.task_id
        }
        
        # Mock task data
        self.task = {
            "id": self.task_id,
            "title": "Implement User Authentication",
            "description": "Add user login and registration functionality",
            "project": "project-1",
            "tags": ["backend", "security"],
            "is_completed": False
        }
        
        # Mock similar tasks
        base_date = datetime.now()
        self.similar_tasks = [
            {
                "id": "task-1",
                "title": "Implement Admin Authentication",
                "description": "Add admin login functionality",
                "project": "project-1",
                "tags": ["backend", "security"],
                "is_completed": True
            },
            {
                "id": "task-2",
                "title": "User Session Management",
                "description": "Handle user session and tokens",
                "project": "project-1",
                "tags": ["backend", "security"],
                "is_completed": True
            },
            {
                "id": "task-3",
                "title": "Database Migration",
                "description": "Migrate data to new schema",
                "project": "project-1",
                "tags": ["backend", "database"],
                "is_completed": True
            }
        ]
        
        # Mock estimate data
        self.estimates = {
            "task-1": [
                frappe._dict({
                    "task": "task-1",
                    "estimated_hours": 20.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=15)
                }),
                frappe._dict({
                    "task": "task-1",
                    "estimated_hours": 15.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=20)
                })
            ],
            "task-2": [
                frappe._dict({
                    "task": "task-2",
                    "estimated_hours": 30.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=10)
                }),
                frappe._dict({
                    "task": "task-2",
                    "estimated_hours": 25.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=15)
                })
            ],
            "task-3": [
                frappe._dict({
                    "task": "task-3",
                    "estimated_hours": 10.0,
                    "confidence_level": "High",
                    "creation": base_date - timedelta(days=5)
                }),
                frappe._dict({
                    "task": "task-3",
                    "estimated_hours": 8.0,
                    "confidence_level": "Medium",
                    "creation": base_date - timedelta(days=10)
                })
            ]
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "find_similar_tasks")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("task_id", params["properties"])

    def test_calculate_text_similarity(self):
        """Test text similarity calculation"""
        # Test exact match
        similarity = self.tool._calculate_text_similarity(
            "implement user auth",
            "implement user auth"
        )
        self.assertEqual(similarity, 1.0)
        
        # Test partial match
        similarity = self.tool._calculate_text_similarity(
            "implement user auth",
            "implement admin auth"
        )
        self.assertTrue(0.5 <= similarity < 1.0)
        
        # Test no match
        similarity = self.tool._calculate_text_similarity(
            "implement user auth",
            "database migration"
        )
        self.assertTrue(similarity < 0.3)
        
        # Test empty strings
        similarity = self.tool._calculate_text_similarity("", "test")
        self.assertEqual(similarity, 0.0)
        similarity = self.tool._calculate_text_similarity("test", "")
        self.assertEqual(similarity, 0.0)
        similarity = self.tool._calculate_text_similarity("", "")
        self.assertEqual(similarity, 0.0)

    def test_calculate_tags_similarity(self):
        """Test tags similarity calculation"""
        # Test exact match
        similarity = self.tool._calculate_tags_similarity(
            ["backend", "security"],
            ["backend", "security"]
        )
        self.assertEqual(similarity, 1.0)
        
        # Test partial match
        similarity = self.tool._calculate_tags_similarity(
            ["backend", "security"],
            ["backend", "database"]
        )
        self.assertEqual(similarity, 1/3)  # One common tag out of three unique tags
        
        # Test no match
        similarity = self.tool._calculate_tags_similarity(
            ["backend", "security"],
            ["frontend", "ui"]
        )
        self.assertEqual(similarity, 0.0)
        
        # Test empty tags
        similarity = self.tool._calculate_tags_similarity([], ["test"])
        self.assertEqual(similarity, 0.0)
        similarity = self.tool._calculate_tags_similarity(["test"], [])
        self.assertEqual(similarity, 0.0)
        similarity = self.tool._calculate_tags_similarity([], [])
        self.assertEqual(similarity, 0.0)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_find_similar_tasks_with_data(self, mock_get_history, mock_api_class):
        """Test finding similar tasks with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.list_tasks.return_value = self.similar_tasks
        mock_api_class.return_value = mock_api
        
        # Setup estimate history mock
        def get_history_for_task(task_id):
            return self.estimates.get(task_id, [])
        
        mock_get_history.side_effect = get_history_for_task
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_api.list_tasks.assert_called_once_with(self.task["project"])
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["task_title"], self.task["title"])
        
        # Verify similar tasks
        self.assertIn("similar_tasks", result)
        similar_tasks = result["similar_tasks"]
        self.assertTrue(len(similar_tasks) > 0)
        
        # Verify first similar task
        first_similar = similar_tasks[0]
        self.assertIn("id", first_similar)
        self.assertIn("title", first_similar)
        self.assertIn("similarity_score", first_similar)
        self.assertIn("estimation_history", first_similar)
        
        # Verify estimation patterns
        self.assertIn("estimation_patterns", result)
        patterns = result["estimation_patterns"]
        self.assertIn("average_changes", patterns)
        self.assertIn("common_initial_confidence", patterns)
        self.assertIn("common_final_confidence", patterns)
        self.assertIn("average_change_percent", patterns)
        self.assertIn("accuracy_distribution", patterns)
        
        # Verify historical accuracy
        self.assertIn("historical_accuracy", result)
        accuracy = result["historical_accuracy"]
        self.assertIn("overall_accuracy", accuracy)
        self.assertIn("average_changes_per_task", accuracy)
        self.assertIn("accuracy_distribution", accuracy)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_find_similar_tasks_task_not_found(self, mock_api_class):
        """Test finding similar tasks when task not found"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = None
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn(self.task_id, result["error"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_find_similar_tasks_no_similar_found(self, mock_api_class):
        """Test finding similar tasks when no similar tasks found"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.list_tasks.return_value = []
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_api.list_tasks.assert_called_once_with(self.task["project"])
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["task_title"], self.task["title"])
        self.assertEqual(result["similar_tasks"], [])
        self.assertIsNone(result["estimation_patterns"])
        self.assertIsNone(result["historical_accuracy"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_find_similar_tasks_no_estimates(self, mock_get_history, mock_api_class):
        """Test finding similar tasks when tasks have no estimates"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.list_tasks.return_value = self.similar_tasks
        mock_api_class.return_value = mock_api
        
        # Setup estimate history mock to return no estimates
        mock_get_history.return_value = []
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_api.list_tasks.assert_called_once_with(self.task["project"])
        
        # Verify similar tasks have empty estimation history
        for task in result["similar_tasks"]:
            history = task["estimation_history"]
            self.assertIsNone(history["initial_estimate"])
            self.assertIsNone(history["final_estimate"])
            self.assertEqual(history["total_changes"], 0)
            self.assertIsNone(history["accuracy"]) 