import unittest
from ..gameplan_ai_assistant.utils.token_manager import TokenManager
from ..gameplan_ai_assistant.exceptions import TokenLimitError

class TestTokenManager(unittest.TestCase):
    def setUp(self):
        self.manager = TokenManager("gpt-4", 8000)
        self.small_manager = TokenManager("gpt-4", 50)  # Small limit for testing
        self.medium_manager = TokenManager("gpt-4", 200)  # Medium limit for step testing
        
    def test_count_tokens(self):
        """Test counting tokens in text"""
        # Test basic text
        self.assertGreater(self.manager.count_tokens("Hello world"), 0)
        self.assertEqual(self.manager.count_tokens(""), 0)
        
        # Test longer text
        long_text = "This is a longer text that should be counted as multiple tokens. " * 10
        self.assertGreater(self.manager.count_tokens(long_text), 50)
        
    def test_count_json(self):
        """Test counting tokens in JSON data"""
        # Test simple objects
        self.assertGreater(self.manager.count_json({"key": "value"}), 0)
        self.assertEqual(self.manager.count_json(None), 0)
        self.assertGreater(self.manager.count_json([1, 2, 3]), 0)
        
        # Test nested structure
        nested = {
            "system_prompt": "Hello world",
            "messages": [
                {"role": "user", "content": "Hi there"},
                {"role": "assistant", "content": "Hello!"}
            ]
        }
        self.assertGreater(self.manager.count_json(nested), 20)
        
    def test_count_context(self):
        """Test counting tokens in full context"""
        context = {
            "system_prompt": "You are a helpful assistant",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "tools": [
                {"name": "search", "description": "Search for information"}
            ]
        }
        
        self.assertGreater(self.manager.count_context(context), 30)
        
    def test_get_completion_tokens(self):
        """Test calculating available completion tokens"""
        # Small context should work
        small_context = {"text": "Hello"}
        available = self.small_manager.get_completion_tokens(small_context)
        self.assertGreater(available, 0)
        self.assertLess(available, 50)
        
        # Large context should raise error
        large_context = {"text": "x" * 1000}
        with self.assertRaises(TokenLimitError):
            self.small_manager.get_completion_tokens(large_context)
            
    def test_validate_and_compress(self):
        """Test context validation and compression"""
        # Small context should pass unchanged
        small_context = {
            "system_prompt": "Be helpful",
            "messages": [{"role": "user", "content": "Hi"}]
        }
        result = self.small_manager.validate_and_compress(small_context)
        self.assertEqual(result, small_context)
        
        # Large context should be compressed
        large_context = {
            "system_prompt": "Be helpful and concise",  # Single line prompt
            "messages": [
                {"role": "user", "content": f"Hi {i}"} 
                for i in range(10)
            ]
        }
        
        compressed = self.small_manager.validate_and_compress(large_context)
        
        # Check compression results
        self.assertLessEqual(len(compressed["messages"]), 5)  # Messages truncated
        self.assertEqual(compressed["system_prompt"], "Be helpful and concise")  # System prompt unchanged
        self.assertLessEqual(self.small_manager.count_context(compressed), 50)  # Fits within limit
        
    def test_compression_steps(self):
        """Test compression steps in order"""
        context = {
            "system_prompt": "Line 1\nLine 2\nLine 3",
            "messages": [
                {"role": "user", "content": f"Message {i}"}
                for i in range(10)
            ]
        }
        
        # First compression should only truncate messages
        compressed = self.medium_manager._compress_context(context)
        self.assertEqual(len(compressed["messages"]), 5)
        self.assertEqual(compressed["system_prompt"], context["system_prompt"])
        
        # Create larger context that needs system prompt truncation
        large_context = {
            "system_prompt": "Line\n" * 20,
            "messages": [{"role": "user", "content": "Hi"}]
        }
        
        # Should truncate system prompt when messages truncation isn't enough
        compressed = self.small_manager._compress_context(large_context)
        self.assertLess(len(compressed["system_prompt"].splitlines()), 20)
        
    def test_compression_with_dict_system_prompt(self):
        """Test compression with dict/object system prompt"""
        context = {
            "system_prompt": {
                "content": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                "metadata": {"type": "instruction"}
            },
            "messages": [{"role": "user", "content": "Hi"}]
        }
        
        compressed = self.small_manager._compress_context(context)
        
        # System prompt content should be truncated but structure preserved
        self.assertIsInstance(compressed["system_prompt"], dict)
        self.assertIn("content", compressed["system_prompt"])
        self.assertIn("metadata", compressed["system_prompt"])
        self.assertLess(len(compressed["system_prompt"]["content"].splitlines()), 5) 