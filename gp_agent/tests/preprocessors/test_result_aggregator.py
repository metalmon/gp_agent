import unittest
from gp_agent.gameplan_ai_assistant.preprocessors.result_aggregator import ResultAggregator, BatchResult
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException

class TestResultAggregator(unittest.TestCase):
    def test_successful_aggregation(self):
        """Test aggregating results with both successful and failed URLs"""
        batch_results = [
            BatchResult(
                successful_results={
                    "https://example.com/1": {"content": "test1"},
                    "https://example.com/2": {"content": "test2"}
                },
                failed_urls={
                    "https://example.com/3": "Connection error"
                },
                batch_type="web"
            ),
            BatchResult(
                successful_results={
                    "http://localhost:8000/app/1": {"content": "frappe1"}
                },
                failed_urls={},
                batch_type="frappe"
            )
        ]
        
        result = ResultAggregator.aggregate_results(batch_results)
        
        # Check structure
        self.assertIn('successful_results', result)
        self.assertIn('failed_urls', result)
        self.assertIn('stats', result)
        
        # Check counts
        self.assertEqual(result['stats']['total_urls'], 4)
        self.assertEqual(result['stats']['successful'], 3)
        self.assertEqual(result['stats']['failed'], 1)
        
        # Check type-specific stats
        self.assertEqual(result['stats']['by_type']['web']['total'], 3)
        self.assertEqual(result['stats']['by_type']['web']['successful'], 2)
        self.assertEqual(result['stats']['by_type']['web']['failed'], 1)
        
        self.assertEqual(result['stats']['by_type']['frappe']['total'], 1)
        self.assertEqual(result['stats']['by_type']['frappe']['successful'], 1)
        self.assertEqual(result['stats']['by_type']['frappe']['failed'], 0)
        
    def test_empty_results(self):
        """Test aggregating empty batch results"""
        batch_results = [
            BatchResult(
                successful_results={},
                failed_urls={},
                batch_type="web"
            )
        ]
        
        result = ResultAggregator.aggregate_results(batch_results)
        self.assertEqual(result['stats']['total_urls'], 0)
        self.assertEqual(result['stats']['successful'], 0)
        self.assertEqual(result['stats']['failed'], 0)
        
    def test_all_failed(self):
        """Test aggregating results where all URLs failed"""
        batch_results = [
            BatchResult(
                successful_results={},
                failed_urls={
                    "https://example.com/1": "Error 1",
                    "https://example.com/2": "Error 2"
                },
                batch_type="web"
            )
        ]
        
        result = ResultAggregator.aggregate_results(batch_results)
        self.assertEqual(result['stats']['total_urls'], 2)
        self.assertEqual(result['stats']['successful'], 0)
        self.assertEqual(result['stats']['failed'], 2)
        self.assertEqual(len(result['failed_urls']), 2)
        
    def test_multiple_batch_types(self):
        """Test aggregating results from multiple batch types"""
        batch_results = [
            BatchResult(
                successful_results={"https://example.com/1": {"content": "web"}},
                failed_urls={},
                batch_type="web"
            ),
            BatchResult(
                successful_results={"http://localhost:8000/1": {"content": "frappe"}},
                failed_urls={},
                batch_type="frappe"
            )
        ]
        
        result = ResultAggregator.aggregate_results(batch_results)
        self.assertEqual(len(result['stats']['by_type']), 2)
        self.assertIn('web', result['stats']['by_type'])
        self.assertIn('frappe', result['stats']['by_type'])
        
    def test_error_handling(self):
        """Test handling invalid input"""
        with self.assertRaises(GPAgentException):
            ResultAggregator.aggregate_results(None) 