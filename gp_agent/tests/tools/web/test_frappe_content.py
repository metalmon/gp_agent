import frappe
import unittest
from ....gameplan_ai_assistant.tools.web.get_webpage_content import get_webpage_content

class TestFrappeContent(unittest.TestCase):
    def setUp(self):
        # Create a test task
        self.task = frappe.get_doc({
            "doctype": "GP Task",
            "title": "Test Task for Content Fetching",
            "description": "This is a test task created to verify content fetching functionality",
            "status": "Todo",
            "priority": "Medium"
        }).insert()
    
    def tearDown(self):
        # Delete the test task
        if hasattr(self, 'task'):
            self.task.delete()
    
    def test_frappe_document_content(self):
        """Test fetching content from a Frappe document"""
        # Test different URL formats
        urls = [
            f"http://localhost:8000/desk#Form/GP_Task/{self.task.name}",
            f"http://localhost:8000/app/gp_task/{self.task.name}",
            f"/app/gp_task/{self.task.name}"
        ]
        
        for url in urls:
            print(f"\nTesting URL: {url}")
            result = get_webpage_content(url)
            
            # Verify no error
            self.assertNotIn('error', result, f"Error fetching content from {url}: {result.get('error')}")
            
            # Verify basic structure
            self.assertIn('url', result)
            self.assertIn('title', result)
            self.assertIn('content', result)
            self.assertIn('metadata', result)
            
            # Verify content includes task details
            content = result['content']
            self.assertIn(self.task.title, content)
            self.assertIn(self.task.description, content)
            self.assertIn(self.task.status, content)
            
            # Verify metadata
            metadata = result['metadata']
            self.assertEqual(metadata['doctype'], 'GP Task')
            self.assertEqual(metadata['name'], self.task.name)
            
            # Print results for inspection
            print(f"Title: {result['title']}")
            print("\nMetadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            print("\nContent preview:")
            print("-" * 40)
            print(content[:500])
            if len(content) > 500:
                print("...") 