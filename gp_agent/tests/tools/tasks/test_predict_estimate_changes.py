import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.predict_estimate_changes import PredictEstimateChangesTool
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class TestPredictEstimateChangesTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.task_id = "task-123"
        self.tool = PredictEstimateChangesTool()
        self.test_data = {
            "task_id": self.task_id
        }
        
        # Mock task data
        self.task = {
            "name": self.task_id,
            "title": "Implement user authentication",
            "description": "Add user login and registration functionality",
            "status": "In Progress",
            "dependencies": ["task-456"]
        }
        
        # Mock estimates with decreasing confidence
        base_date = datetime.now()
        self.initial_estimate = frappe._dict({
            "name": "est-1",
            "task": self.task_id,
            "estimated_hours": 10.0,
            "confidence_level": "High",
            "note": "Initial estimate",
            "creation": base_date - timedelta(days=14),
            "owner": "john@example.com"
        })
        
        self.second_estimate = frappe._dict({
            "name": "est-2",
            "task": self.task_id,
            "estimated_hours": 15.0,
            "confidence_level": "Medium",
            "note": "Found additional complexity",
            "creation": base_date - timedelta(days=7),
            "owner": "john@example.com"
        })
        
        self.current_estimate = frappe._dict({
            "name": "est-3",
            "task": self.task_id,
            "estimated_hours": 20.0,
            "confidence_level": "Low",
            "note": "Dependencies causing delays",
            "creation": base_date - timedelta(days=1),
            "owner": "jane@example.com"
        })
        
        self.history = [
            self.current_estimate,
            self.second_estimate,
            self.initial_estimate
        ]
        
        # Mock similar tasks
        self.similar_task_1 = {
            "name": "similar-1",
            "title": "Implement admin authentication",
            "description": "Add admin login functionality",
            "status": "Completed"
        }
        
        self.similar_task_2 = {
            "name": "similar-2",
            "title": "User session management",
            "description": "Handle user session and tokens",
            "status": "Completed"
        }
        
        self.similar_tasks = [self.similar_task_1, self.similar_task_2]
        
        # Mock similar task histories
        self.similar_task_1_history = [
            frappe._dict({
                "name": "est-s1-2",
                "task": "similar-1",
                "estimated_hours": 25.0,
                "confidence_level": "Medium",
                "creation": base_date - timedelta(days=30)
            }),
            frappe._dict({
                "name": "est-s1-1",
                "task": "similar-1",
                "estimated_hours": 12.0,
                "confidence_level": "High",
                "creation": base_date - timedelta(days=45)
            })
        ]
        
        self.similar_task_2_history = [
            frappe._dict({
                "name": "est-s2-2",
                "task": "similar-2",
                "estimated_hours": 18.0,
                "confidence_level": "Low",
                "creation": base_date - timedelta(days=15)
            }),
            frappe._dict({
                "name": "est-s2-1",
                "task": "similar-2",
                "estimated_hours": 8.0,
                "confidence_level": "High",
                "creation": base_date - timedelta(days=30)
            })
        ]

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "predict_estimate_changes")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("task_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("task_id", params["properties"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_predict_estimate_changes_with_data(self, mock_get_history, mock_api_class):
        """Test predicting estimate changes with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.get_similar_tasks.return_value = self.similar_tasks
        mock_api_class.return_value = mock_api
        
        # Setup history mock to return different estimates for each task
        def get_history_for_task(task_id):
            if task_id == self.task_id:
                return self.history
            elif task_id == "similar-1":
                return self.similar_task_1_history
            elif task_id == "similar-2":
                return self.similar_task_2_history
            return []
        
        mock_get_history.side_effect = get_history_for_task
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_api.get_similar_tasks.assert_called_once_with(self.task_id)
        
        # Verify result structure
        self.assertEqual(result["task_id"], self.task_id)
        self.assertEqual(result["task_title"], self.task["title"])
        
        # Verify change likelihood
        likelihood = result["change_likelihood"]
        self.assertIn("score", likelihood)
        self.assertIn("level", likelihood)
        self.assertIn("confidence", likelihood)
        self.assertTrue(0 <= likelihood["score"] <= 1)
        self.assertIn(likelihood["level"], ["high", "medium", "low"])
        
        # Given our test data, likelihood should be high
        self.assertEqual(likelihood["level"], "high")
        
        # Verify predictions
        predictions = result["predictions"]
        self.assertIn("expected_changes", predictions)
        self.assertIn("timeline", predictions)
        self.assertIn("magnitude", predictions)
        
        # Given our test data with frequent changes
        self.assertEqual(predictions["timeline"], "within_week")
        self.assertIn(predictions["magnitude"], ["major", "significant"])
        
        # Verify expected changes
        changes = predictions["expected_changes"]
        self.assertTrue(len(changes) > 0)
        self.assertTrue(any(
            change["type"] == "increase" 
            for change in changes
        ))
        
        # Verify risk factors
        risk_factors = result["risk_factors"]
        self.assertIn("high", risk_factors)
        self.assertIn("medium", risk_factors)
        self.assertIn("low", risk_factors)
        
        # Given our test data
        self.assertIn("decreasing_confidence", risk_factors["high"])
        self.assertIn("has_dependencies", risk_factors["medium"])
        
        # Verify recommendations
        recommendations = result["recommendations"]
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(any(
            "confidence" in rec.lower()
            for rec in recommendations
        ))

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch.object(GPTaskEstimate, "get_estimate_history")
    async def test_predict_estimate_changes_no_history(self, mock_get_history, mock_api_class):
        """Test predicting estimate changes without history"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_task_details.return_value = self.task
        mock_api.get_similar_tasks.return_value = []
        mock_api_class.return_value = mock_api
        
        # Setup history mock
        mock_get_history.return_value = []
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_task_details.assert_called_once_with(self.task_id)
        mock_get_history.assert_called_once_with(self.task_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["task_title"], self.task["title"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_predict_estimate_changes_task_not_found(self, mock_api_class):
        """Test predicting estimate changes for non-existent task"""
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

    def test_analyze_confidence_trend(self):
        """Test confidence trend analysis"""
        # Test decreasing confidence
        trend = self.tool._analyze_confidence_trend(self.history)
        self.assertEqual(trend, "decreasing")
        
        # Test stable confidence
        stable_history = [
            frappe._dict({"confidence_level": "High"}),
            frappe._dict({"confidence_level": "High"})
        ]
        trend = self.tool._analyze_confidence_trend(stable_history)
        self.assertEqual(trend, "stable")
        
        # Test fluctuating confidence
        fluctuating_history = [
            frappe._dict({"confidence_level": "High"}),
            frappe._dict({"confidence_level": "Low"}),
            frappe._dict({"confidence_level": "High"})
        ]
        trend = self.tool._analyze_confidence_trend(fluctuating_history)
        self.assertEqual(trend, "fluctuating")

    def test_calculate_change_likelihood(self):
        """Test change likelihood calculation"""
        historical_patterns = {
            "volatility": "high",
            "change_frequency": 1.5,
            "trend": "increasing",
            "average_change": 30.0
        }
        
        similar_patterns = {
            "average_changes": 4.0,
            "common_patterns": ["major_increase"]
        }
        
        risk_factors = {
            "high": ["decreasing_confidence"],
            "medium": ["has_dependencies"],
            "low": ["missing_description"]
        }
        
        likelihood = self.tool._calculate_change_likelihood(
            historical_patterns,
            similar_patterns,
            risk_factors
        )
        
        self.assertIn("score", likelihood)
        self.assertIn("level", likelihood)
        self.assertIn("confidence", likelihood)
        self.assertTrue(0 <= likelihood["score"] <= 1)
        
        # Given our test data, should indicate high likelihood
        self.assertEqual(likelihood["level"], "high")
        self.assertEqual(likelihood["confidence"], "high") 