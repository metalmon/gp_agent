import unittest
import frappe
import json
from unittest.mock import patch

class GPAgentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test settings that will be used across all tests"""
        print("\n=== Base Class setUpClass ===")
        super().setUpClass()
        
        # Use real settings directly
        print("Getting GP Agent Settings...")
        cls.settings = frappe.get_single("GP Agent Settings")
        print(f"Settings loaded: {cls.settings.name}")
        print(f"Settings base_url: {getattr(cls.settings, 'base_url', 'Not set')}")
        print(f"Settings enabled: {getattr(cls.settings, 'enabled', 'Not set')}")
        
        # Mock frappe.get_single to return the real settings
        print("Setting up frappe.get_single mock...")
        def mock_get_single(doctype, *args, **kwargs):
            print(f"Mock get_single called for doctype: {doctype}")
            if doctype == "GP Agent Settings":
                print(f"Returning mocked settings: {cls.settings.name}")
                return cls.settings
            return frappe.get_single(doctype, *args, **kwargs)
            
        cls._patcher = patch('frappe.get_single', side_effect=mock_get_single)
        cls._mock = cls._patcher.start()
        print("Base class setup completed")

    def setUp(self):
        """Set up test case and test data"""
        print(f"\n=== Base Class setUp for {self._testMethodName} ===")
        super().setUp()
        print("Base class setUp completed")
        
        # Set up test data
        print("Setting up test data...")
        self.test_id = frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S%f')
        self.sample_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        self.sample_function_call = {
            "choices": [{
                "message": {
                    "content": None,
                    "function_call": {
                        "name": "web_search",
                        "arguments": json.dumps({
                            "query": "test query"
                        })
                    }
                }
            }]
        }
        
        self.sample_normal_response = {
            "choices": [{
                "message": {
                    "content": "This is a test response",
                    "role": "assistant"
                }
            }]
        }
        print("Test data setup completed")

    def tearDown(self):
        """Clean up test case and test data"""
        print(f"\n=== Base Class tearDown for {self._testMethodName} ===")
        try:
            # Clean up test data
            print("Cleaning up test data...")
            
            # Clean up logs with test_discussion pattern
            frappe.db.sql("""
                DELETE FROM `tabGP Agent Log` 
                WHERE discussion_id LIKE 'test_discussion_%'
            """)
            
            # Clean up tool logs for test logs
            frappe.db.sql("""
                DELETE FROM `tabGP Agent Tool Log`
                WHERE parent_log LIKE 'LOG-test_project_%'
            """)
            
            frappe.db.commit()
            print("Test data cleanup completed")
            
            # Call parent tearDown
            super().tearDown()
            print("Base class tearDown completed successfully")
        except Exception as e:
            print(f"Error in base class tearDown: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                print("Traceback:")
                print(''.join(traceback.format_tb(e.__traceback__)))
            raise

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level mocks"""
        print("\n=== Base Class tearDownClass ===")
        try:
            print("Stopping frappe.get_single mock...")
            cls._patcher.stop()
            
            # Final cleanup of any remaining test data
            print("Final cleanup of test data...")
            frappe.db.sql("""
                DELETE FROM `tabGP Agent Log` 
                WHERE discussion_id LIKE 'test_discussion_%'
                   OR team_id LIKE 'test_team_%'
                   OR project_id LIKE 'test_project_%'
            """)
            
            frappe.db.sql("""
                DELETE FROM `tabGP Agent Tool Log`
                WHERE parent_log LIKE 'LOG-test_project_%'
            """)
            
            frappe.db.commit()
            print("Base class cleanup completed successfully")
        except Exception as e:
            print(f"Error in base class tearDownClass: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                print("Traceback:")
                print(''.join(traceback.format_tb(e.__traceback__)))
            raise 