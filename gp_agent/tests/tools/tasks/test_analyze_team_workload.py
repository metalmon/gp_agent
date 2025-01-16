import unittest
from unittest.mock import patch, MagicMock
import frappe
from datetime import datetime, timedelta

from gp_agent.gameplan_ai_assistant.tools.tasks.analyze_team_workload import AnalyzeTeamWorkloadTool
from gp_agent.gameplan_ai_assistant.utils.task_analytics import analyze_team_workload as analyze_workload_impl


class TestAnalyzeTeamWorkloadTool(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.team_id = "team-123"
        self.tool = AnalyzeTeamWorkloadTool()
        self.test_data = {
            "team_id": self.team_id
        }
        
        # Mock team data
        self.team = {
            "name": self.team_id,
            "title": "Engineering Team",
            "status": "Active"
        }
        
        # Mock workload data
        self.workload_data = {
            "workloads": {
                "user-1": {
                    "user": {
                        "name": "user-1",
                        "full_name": "John Developer"
                    },
                    "total_hours": 35,
                    "tasks": [
                        {
                            "task_id": "task-1",
                            "title": "Implement Feature",
                            "status": "In Progress",
                            "priority": "High",
                            "due_date": datetime.now() + timedelta(days=5),
                            "remaining_hours": 20
                        },
                        {
                            "task_id": "task-2",
                            "title": "Code Review",
                            "status": "Todo",
                            "priority": "Medium",
                            "due_date": datetime.now() + timedelta(days=3),
                            "remaining_hours": 15
                        }
                    ],
                    "overloaded": False,
                    "available_capacity": 5
                },
                "user-2": {
                    "user": {
                        "name": "user-2",
                        "full_name": "Jane Engineer"
                    },
                    "total_hours": 45,
                    "tasks": [
                        {
                            "task_id": "task-3",
                            "title": "System Design",
                            "status": "In Progress",
                            "priority": "High",
                            "due_date": datetime.now() + timedelta(days=7),
                            "remaining_hours": 30
                        },
                        {
                            "task_id": "task-4",
                            "title": "Documentation",
                            "status": "Todo",
                            "priority": "Low",
                            "due_date": datetime.now() + timedelta(days=4),
                            "remaining_hours": 15
                        }
                    ],
                    "overloaded": True,
                    "available_capacity": 0
                }
            },
            "team_capacity": {
                "total_assigned_hours": 80,
                "total_available_hours": 5,
                "bottlenecks": [
                    {
                        "user": "Jane Engineer",
                        "total_hours": 45,
                        "overload_hours": 5
                    }
                ]
            }
        }

    def test_tool_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "analyze_team_workload")
        self.assertTrue(self.tool.description)
        
        # Test parameter schema
        params = self.tool.get_parameters()
        self.assertEqual(params["type"], "object")
        self.assertIn("team_id", params["required"])
        self.assertEqual(len(params["required"]), 1)
        self.assertIn("team_id", params["properties"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.analyze_team_workload')
    async def test_analyze_team_workload_with_data(self, mock_analyze_impl, mock_api_class):
        """Test analyzing team workload with data"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team.return_value = self.team
        mock_api_class.return_value = mock_api
        
        # Setup analysis mock
        mock_analyze_impl.return_value = self.workload_data
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_team.assert_called_once_with(self.team_id)
        mock_analyze_impl.assert_called_once_with(self.team_id)
        
        # Verify result structure
        self.assertEqual(result["team_id"], self.team_id)
        self.assertEqual(result["team_name"], self.team["name"])
        
        # Verify workload data
        self.assertIn("workloads", result)
        workloads = result["workloads"]
        self.assertEqual(len(workloads), 2)
        
        # Verify first user workload
        user1_workload = workloads["user-1"]
        self.assertEqual(user1_workload["user"]["full_name"], "John Developer")
        self.assertEqual(user1_workload["total_hours"], 35)
        self.assertEqual(len(user1_workload["tasks"]), 2)
        self.assertFalse(user1_workload["overloaded"])
        self.assertEqual(user1_workload["available_capacity"], 5)
        
        # Verify team capacity
        self.assertIn("team_capacity", result)
        capacity = result["team_capacity"]
        self.assertEqual(capacity["total_assigned_hours"], 80)
        self.assertEqual(capacity["total_available_hours"], 5)
        
        # Verify bottlenecks
        bottlenecks = capacity["bottlenecks"]
        self.assertEqual(len(bottlenecks), 1)
        self.assertEqual(bottlenecks[0]["user"], "Jane Engineer")
        self.assertEqual(bottlenecks[0]["overload_hours"], 5)

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    async def test_analyze_team_workload_team_not_found(self, mock_api_class):
        """Test analyzing workload for non-existent team"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team.return_value = None
        mock_api_class.return_value = mock_api
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API call
        mock_api.get_team.assert_called_once_with(self.team_id)
        
        # Verify error response
        self.assertIn("error", result)
        self.assertIn(self.team_id, result["error"])

    @patch('gp_agent.gameplan_ai_assistant.tools.tasks.base.GameplanAPI')
    @patch('gp_agent.gameplan_ai_assistant.utils.task_analytics.analyze_team_workload')
    async def test_analyze_team_workload_empty_team(self, mock_analyze_impl, mock_api_class):
        """Test analyzing workload for team with no members"""
        # Setup API mock
        mock_api = MagicMock()
        mock_api.get_team.return_value = self.team
        mock_api_class.return_value = mock_api
        
        # Setup analysis mock with empty data
        empty_result = {
            "workloads": {},
            "team_capacity": {
                "total_assigned_hours": 0,
                "total_available_hours": 0,
                "bottlenecks": []
            }
        }
        mock_analyze_impl.return_value = empty_result
        
        # Execute tool
        result = await self.tool.execute(self.test_data)
        
        # Verify API calls
        mock_api.get_team.assert_called_once_with(self.team_id)
        mock_analyze_impl.assert_called_once_with(self.team_id)
        
        # Verify result structure
        self.assertEqual(result["team_id"], self.team_id)
        self.assertEqual(result["team_name"], self.team["name"])
        self.assertEqual(len(result["workloads"]), 0)
        self.assertEqual(result["team_capacity"]["total_assigned_hours"], 0)
        self.assertEqual(result["team_capacity"]["total_available_hours"], 0)
        self.assertEqual(len(result["team_capacity"]["bottlenecks"]), 0) 