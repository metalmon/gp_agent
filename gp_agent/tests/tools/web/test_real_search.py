import unittest
import frappe
from gp_agent.gameplan_ai_assistant.tools.web.web_search import web_search

class TestRealWebSearch(unittest.TestCase):
    def test_real_search_python(self):
        """Test real search for Python programming language"""
        results = web_search("Python programming language official website", num_results=3)
        
        print("\nPython Search Results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['link']}")
            print(f"   Source: {result['source']}")
            print(f"   Snippet: {result['snippet']}")
        
        # Verify we got results
        self.assertTrue(len(results) > 0)
        
        # Verify structure of results
        first_result = results[0]
        self.assertIn("title", first_result)
        self.assertIn("link", first_result)
        self.assertIn("snippet", first_result)
        self.assertIn("source", first_result)
        
        # Verify content relevance
        python_related = False
        for result in results:
            if "python" in result["title"].lower() or "python" in result["snippet"].lower():
                python_related = True
                break
        self.assertTrue(python_related, "No Python-related results found")

    def test_real_search_frappe(self):
        """Test real search for Frappe Framework"""
        results = web_search("Frappe Framework open source low code", num_results=3)
        
        print("\nFrappe Search Results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['link']}")
            print(f"   Source: {result['source']}")
            print(f"   Snippet: {result['snippet']}")
        
        # Verify we got results
        self.assertTrue(len(results) > 0)
        
        # Verify content relevance
        frappe_related = False
        for result in results:
            if "frappe" in result["title"].lower() or "frappe" in result["snippet"].lower():
                frappe_related = True
                break
        self.assertTrue(frappe_related, "No Frappe-related results found") 