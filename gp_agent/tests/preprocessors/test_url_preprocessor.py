import unittest
from gp_agent.gameplan_ai_assistant.preprocessors.url_preprocessor import URLPreprocessor
from gp_agent.gameplan_ai_assistant.exceptions import GPAgentException

class TestURLPreprocessor(unittest.TestCase):
    def test_single_url(self):
        """Test processing single URL"""
        url = "https://example.com"
        result = URLPreprocessor.extract_urls(url)
        self.assertEqual(result, [url])
        
    def test_comma_separated_urls(self):
        """Test processing comma-separated URLs"""
        urls = "https://example.com, http://test.com"
        result = URLPreprocessor.extract_urls(urls)
        self.assertEqual(result, ["https://example.com", "http://test.com"])
        
    def test_url_list(self):
        """Test processing list of URLs"""
        urls = ["https://example.com", "http://test.com"]
        result = URLPreprocessor.extract_urls(urls)
        self.assertEqual(result, urls)
        
    def test_urls_in_text(self):
        """Test extracting URLs from text"""
        text = "Please fetch content from https://example.com and also from http://test.com"
        result = URLPreprocessor.extract_urls(text)
        self.assertEqual(result, ["https://example.com", "http://test.com"])
        
    def test_invalid_urls(self):
        """Test handling invalid URLs"""
        urls = "not-a-url, http://invalid"
        with self.assertRaises(GPAgentException):
            URLPreprocessor.extract_urls(urls)
            
    def test_mixed_valid_invalid(self):
        """Test handling mix of valid and invalid URLs"""
        urls = "https://example.com, not-a-url, http://test.com"
        result = URLPreprocessor.extract_urls(urls)
        self.assertEqual(result, ["https://example.com", "http://test.com"])
        
    def test_url_normalization(self):
        """Test URL normalization"""
        urls = "example.com, https://test.com"
        result = URLPreprocessor.extract_urls(urls)
        self.assertEqual(result, ["https://example.com", "https://test.com"])
        
    def test_unsupported_type(self):
        """Test handling unsupported input type"""
        with self.assertRaises(GPAgentException):
            URLPreprocessor.extract_urls(123) 