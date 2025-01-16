from typing import List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse
from ..exceptions import GPAgentException

@dataclass
class URLBatch:
    """Represents a batch of URLs with common characteristics"""
    urls: List[str]
    domain: str
    batch_type: str  # 'frappe', 'web', etc.
    
class URLBatcher:
    """Groups URLs into batches for efficient processing"""
    
    BATCH_TYPES = {
        'frappe': lambda domain: (
            # Local Frappe instances
            domain.startswith(('localhost', '127.0.0.1')) or
            # Frappe domains
            any(name in domain for name in ['frappe', 'erpnext']) or
            # Common Frappe ports
            any(port in domain for port in [':8000', ':8001', ':8002', ':8003'])
        ),
        'web': lambda domain: True  # Default type for all other URLs
    }
    
    @classmethod
    def create_batches(cls, urls: List[str], batch_size: int = 5) -> List[URLBatch]:
        """
        Create batches of URLs grouped by domain and type.
        
        Args:
            urls: List of validated URLs
            batch_size: Maximum size of each batch
            
        Returns:
            List of URLBatch objects
            
        Raises:
            GPAgentException: If batch creation fails
        """
        # Validate inputs
        if not urls:
            raise GPAgentException("URL list cannot be empty")
        if batch_size < 1:
            raise GPAgentException("Batch size must be at least 1")
            
        try:
            # Group URLs by domain and type
            url_groups: Dict[str, Dict[str, List[str]]] = {}
            
            for url in urls:
                domain = cls._extract_domain(url)
                batch_type = cls._determine_batch_type(domain)
                
                if domain not in url_groups:
                    url_groups[domain] = {}
                if batch_type not in url_groups[domain]:
                    url_groups[domain][batch_type] = []
                    
                url_groups[domain][batch_type].append(url)
            
            # Create batches
            batches = []
            for domain, type_groups in url_groups.items():
                for batch_type, domain_urls in type_groups.items():
                    # Split into smaller batches if needed
                    for i in range(0, len(domain_urls), batch_size):
                        batch_urls = domain_urls[i:i + batch_size]
                        batches.append(URLBatch(
                            urls=batch_urls,
                            domain=domain,
                            batch_type=batch_type
                        ))
            
            return batches
            
        except Exception as e:
            raise GPAgentException(f"Failed to create URL batches: {str(e)}")
    
    @classmethod
    def _extract_domain(cls, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc
        
    @classmethod
    def _determine_batch_type(cls, domain: str) -> str:
        """Determine batch type based on domain"""
        for batch_type, checker in cls.BATCH_TYPES.items():
            if checker(domain):
                return batch_type
        return 'web'  # Default type 