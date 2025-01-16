import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.predict_completion_dates import PredictCompletionDatesTool
from gp_agent.gameplan_ai_assistant.utils.task_analytics import predict_completion_dates as predict_dates_impl


class TestPredictCompletionDatesTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.project_id = "project-123"
        self.tool = PredictCompletionDatesTool()
        self.test_data = {
            "project_id": self.project_id
        }
        
        # Mock project data
        self.project = {
            "name": self.project_id,
            "title": "Test Project",
            "status": "In Progress"
        }
        
        # Mock prediction data
        base_date = datetime.now()
        self.prediction_data = {
            "task_predictions": [
                {
                    "task_id": "task-1",
                    "title": "Setup Infrastructure",
                    "predicted_completion": (base_date + timedelta(days=3)).isoformat(),
                    "confidence": 0.85,
                    "risk_level": "low"
                },
                {
                    "task_id": "task-2",
                    "title": "Implement Core Features",
                    "predicted_completion": (base_date + timedelta(days=7)).isoformat(),
                    "confidence": 0.75,
                    "risk_level": "medium"
                },
                {
                    "task_id": "task-3",
                    "title": "Testing and Deployment",
                    "predicted_completion": (base_date + timedelta(days=10)).isoformat(),
                    "confidence": 0.65,
                    "risk_level": "high"
                }
            ],
            "overall_completion": (base_date + timedelta(days=10)).isoformat(),
            "overall_confidence": 0.70,
            "risk_factors": [
                {
                    "type": "resource_availability",
                    "description": "Limited developer availability",
                    "impact": "high"
                },
                {
                    "type": "complexity",
                    "description": "Complex integration requirements",
                    "impact": "medium"
                }
            ]
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "predict_completion_dates")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("project_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("project_id", params["properties"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.predict_completion_dates')
    async def test_predict_completion_dates_with_data(self, mock_predict_impl, mock_api_class):
        """Test predicting completion dates with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = self.project
        mock_api_class.return_value = mock_api
        
        # Setup prediction mock
        mock_predict_impl.return_value = self.prediction_data
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_project.assert_called_once_with(self.project_id)
        mock_predict_impl.assert_called_once_with(self.project_id)
        
        # Verify result structure
        self.assertEqual(result["project_id"], self.project_id)
        self.assertEqual(result["project_title"], self.project["title"])
        
        # Verify task predictions
        self.assertIn("task_predictions", result)
        predictions = result["task_predictions"]
        self.assertEqual(len(predictions), 3)
        
        # Verify first task prediction
        first_pred = predictions[0]
        self.assertEqual(first_pred["task_id"], "task-1")
        self.assertEqual(first_pred["title"], "Setup Infrastructure")
        self.assertTrue(first_pred["predicted_completion"])
        self.assertEqual(first_pred["confidence"], 0.85)
        self.assertEqual(first_pred["risk_level"], "low")
        
        # Verify overall predictions
        self.assertTrue(result["overall_completion"])
        self.assertEqual(result["overall_confidence"], 0.70)
        
        # Verify risk factors
        self.assertIn("risk_factors", result)
        risks = result["risk_factors"]
        self.assertEqual(len(risks), 2)
        
        resource_risk = next(r for r in risks if r["type"] == "resource_availability")
        self.assertEqual(resource_risk["impact"], "high")
        
        complexity_risk = next(r for r in risks if r["type"] == "complexity")
        self.assertEqual(complexity_risk["impact"], "medium")

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_predict_completion_dates_project_not_found(self, mock_api_class):
        """Test predicting completion dates for non-existent project"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = None
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_project.assert_called_once_with(self.project_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn(self.project_id, result["error"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.predict_completion_dates')
    async def test_predict_completion_dates_no_tasks(self, mock_predict_impl, mock_api_class):
        """Test predicting completion dates with no tasks"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_project.return_value = self.project
        mock_api_class.return_value = mock_api
        
        # Setup prediction mock with empty data
        empty_result = {
            "task_predictions": [],
            "overall_completion": None,
            "overall_confidence": 0,
            "risk_factors": []
        }
        mock_predict_impl.return_value = empty_result
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_project.assert_called_once_with(self.project_id)
        mock_predict_impl.assert_called_once_with(self.project_id)
        
        # Verify result structure
        self.assertEqual(result["project_id"], self.project_id)
        self.assertEqual(result["project_title"], self.project["title"])
        self.assertEqual(len(result["task_predictions"]), 0)
        self.assertIsNone(result["overall_completion"])
        self.assertEqual(result["overall_confidence"], 0)
        self.assertEqual(len(result["risk_factors"]), 0) 