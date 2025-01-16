import unittest
from gp_agent.gameplan_ai_assistant.preprocessors.url_batcher import URLBatcher, URLBatch
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException

class TestURLBatcher(unittest.TestCase):
    def test_single_domain_batch(self):
        """Test batching URLs from single domain"""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        batches = URLBatcher.create_batches(urls)
        
        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertEqual(batch.domain, "example.com")
        self.assertEqual(batch.batch_type, "web")
        self.assertEqual(batch.urls, urls)
        
    def test_multiple_domains(self):
        """Test batching URLs from different domains"""
        urls = [
            "https://example.com/page1",
            "https://test.com/page1",
            "https://example.com/page2"
        ]
        batches = URLBatcher.create_batches(urls)
        
        self.assertEqual(len(batches), 2)
        domains = {batch.domain for batch in batches}
        self.assertEqual(domains, {"example.com", "test.com"})
        
    def test_batch_size_limit(self):
        """Test respecting batch size limit"""
        urls = [f"https://example.com/page{i}" for i in range(7)]
        batches = URLBatcher.create_batches(urls, batch_size=3)
        
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0].urls), 3)
        self.assertEqual(len(batches[1].urls), 3)
        self.assertEqual(len(batches[2].urls), 1)
        
    def test_frappe_urls(self):
        """Test detecting Frappe URLs"""
        urls = [
            "http://localhost:8000/app/task/123",
            "https://example.com/page1",
            "https://frappe.io/docs"
        ]
        batches = URLBatcher.create_batches(urls)
        
        frappe_batches = [b for b in batches if b.batch_type == "frappe"]
        web_batches = [b for b in batches if b.batch_type == "web"]
        
        self.assertEqual(len(frappe_batches), 2)
        self.assertEqual(len(web_batches), 1)
        
    def test_empty_urls(self):
        """Test handling empty URL list"""
        with self.assertRaises(GPAgentException):
            URLBatcher.create_batches([])
            
    def test_invalid_batch_size(self):
        """Test handling invalid batch size"""
        urls = ["https://example.com/page1"]
        with self.assertRaises(GPAgentException):
            URLBatcher.create_batches(urls, batch_size=0) 