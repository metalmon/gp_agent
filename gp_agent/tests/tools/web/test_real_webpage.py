import frappe
from gp_agent.gameplan_ai_assistant.tools.web.get_webpage_content import get_webpage_content

def test_real_webpage():
    """Test get_webpage_content with real webpages"""
    from ...tools.web.get_webpage_content import get_webpage_content
    
    # Test URLs
    urls = [
        "https://docs.python.org/3/tutorial/index.html",
        "https://github.com/python/cpython/blob/main/README.rst",
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://docs.frappe.io/",
        "http://localhost:8000/desk#Form/GP%20Task/TASK-1"  # Local Frappe document
    ]
    
    for url in urls:
        print(f"\nTesting URL: {url}")
        result = get_webpage_content(url)
        
        # Print results in detail
        print(f"URL: {result.get('url')}")
        print(f"Final URL: {result.get('final_url', '')}")
        print(f"Title: {result.get('title')}")
        print("\nMetadata:")
        for key, value in result.get('metadata', {}).items():
            print(f"  {key}: {value}")
        
        if result.get('error'):
            print(f"\nError: {result.get('error')}")
        else:
            # Print first 1000 chars of content with proper formatting
            content_preview = result.get('content', '')[:1000]
            print("\nContent preview:")
            print("-" * 40)
            print(content_preview)
            if len(result.get('content', '')) > 1000:
                print("...")

if __name__ == "__main__":
    test_real_webpage() 