import re
from typing import List, Union
from urllib.parse import urlparse
from ..exceptions import GPAgentException

class URLPreprocessor:
    """Preprocessor for handling URL extraction and validation from model requests"""
    
    URL_PATTERN = r'https?://(?:localhost|(?:[-\w.]|(?:%[\da-fA-F]{2})))+(?::\d+)?(?:/[^/\s]*)*'
    
    @classmethod
    def extract_urls(cls, request: Union[str, List[str]]) -> List[str]:
        """
        Extract URLs from various request formats.
        
        Args:
            request: Can be:
                - Single URL string
                - Comma-separated URLs string
                - List of URLs
                - Text containing URLs
                
        Returns:
            List of validated URLs
            
        Raises:
            GPAgentException: If no valid URLs found or validation fails
        """
        urls = []
        
        # Handle different input types
        if isinstance(request, list):
            # List of URLs
            raw_urls = request
        elif isinstance(request, str):
            if ',' in request:
                # Comma-separated URLs
                raw_urls = [url.strip() for url in request.split(',')]
            elif cls._is_valid_url(request):
                # Single URL
                raw_urls = [request]
            else:
                # Text containing URLs
                raw_urls = re.findall(cls.URL_PATTERN, request)
        else:
            raise GPAgentException(f"Unsupported request type: {type(request)}")
            
        # Validate each URL
        for url in raw_urls:
            validated_url = cls._validate_url(url)
            if validated_url:
                urls.append(validated_url)
                
        if not urls:
            raise GPAgentException("No valid URLs found in request")
            
        return urls
    
    @classmethod
    def _is_valid_url(cls, url: str) -> bool:
        """Check if string is a valid URL"""
        try:
            result = urlparse(url)
            # Check for valid scheme and netloc
            if not all([result.scheme, result.netloc]):
                return False
                
            # Check scheme
            if result.scheme not in ['http', 'https']:
                return False
                
            # Allow localhost and IP addresses
            if result.netloc in ['localhost'] or result.netloc.startswith(('127.0.0.1', 'localhost:')):
                return True
                
            # For other domains, require at least one dot and valid characters
            if '.' not in result.netloc:
                return False
                
            # Check if netloc has valid characters and proper structure
            if not re.match(r'^[\w][\w\-\.]*\.\w+(?::\d+)?$', result.netloc):
                return False
                
            return True
        except:
            return False
            
    @classmethod
    def _validate_url(cls, url: str) -> Union[str, None]:
        """
        Validate and normalize URL.
        Returns normalized URL or None if invalid.
        """
        url = url.strip()
        
        # Try with current scheme
        if cls._is_valid_url(url):
            return url
            
        # Only try adding https:// if the URL looks like a domain
        if not url.startswith(('http://', 'https://')) and re.match(r'^[\w][\w\-\.]*\.\w+', url):
            url_with_scheme = 'https://' + url
            if cls._is_valid_url(url_with_scheme):
                return url_with_scheme
                
        return None 