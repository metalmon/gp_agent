from typing import List, Dict, Any, Union
from ..preprocessors.url_preprocessor import URLPreprocessor
from ..preprocessors.url_batcher import URLBatcher, URLBatch
from ..preprocessors.result_aggregator import ResultAggregator, BatchResult
from ..tools.web.get_webpage_content import get_webpage_content
from ..exceptions import GPAgentException
from urllib.parse import urlparse

class WebContentProcessor:
    """Processes web content from multiple URLs using appropriate handlers"""
    
    @classmethod
    def process_urls(cls, urls: Union[str, List[str]], batch_size: int = 5) -> Dict[str, Any]:
        """
        Process multiple URLs and return aggregated results
        
        Args:
            urls: Single URL string, list of URLs, or text containing URLs
            batch_size: Maximum size of each batch
            
        Returns:
            Dictionary containing:
            - successful_results: Dict[str, Any] - All successful results
            - failed_urls: Dict[str, str] - All failed URLs with error messages
            - stats: Dict with summary statistics
            
        Raises:
            GPAgentException: If processing fails
        """
        try:
            # Extract and validate URLs
            validated_urls = URLPreprocessor.extract_urls(urls)
            
            # Create batches
            batches = URLBatcher.create_batches(validated_urls, batch_size)
            
            # Process each batch
            batch_results = []
            for batch in batches:
                result = cls._process_batch(batch)
                batch_results.append(result)
            
            # Aggregate results
            return ResultAggregator.aggregate_results(batch_results)
            
        except Exception as e:
            raise GPAgentException(f"Failed to process URLs: {str(e)}")
    
    @classmethod
    def _process_batch(cls, batch: URLBatch) -> BatchResult:
        """Process a single batch of URLs"""
        successful_results = {}
        failed_urls = {}
        
        try:
            if batch.batch_type == "frappe":
                import frappe
                for url in batch.urls:
                    try:
                        # Parse doctype and name from URL
                        path = urlparse(url).path
                        parts = [p for p in path.split('/') if p]
                        if len(parts) >= 3 and parts[0] == 'app':
                            doctype, docname = parts[1], parts[2]
                            
                            # Fetch document using frappe API
                            doc = frappe.get_doc(doctype, docname)
                            
                            # Convert to content format
                            content = {
                                "url": url,
                                "title": f"{doc.doctype}: {doc.name}",
                                "content": doc.as_markdown(),
                                "timestamp": str(doc.modified),
                                "metadata": {
                                    "doctype": doc.doctype,
                                    "docname": doc.name,
                                    "modified": str(doc.modified),
                                    "modified_by": doc.modified_by
                                }
                            }
                            successful_results[url] = content
                        else:
                            failed_urls[url] = "Invalid Frappe URL format"
                    except Exception as e:
                        failed_urls[url] = str(e)
            else:
                # Use get_webpage_content for web URLs
                for url in batch.urls:
                    try:
                        content = get_webpage_content(url)
                        successful_results[url] = content
                    except Exception as e:
                        failed_urls[url] = {
                            "url": url,
                            "error": str(e)
                        }
                        
            return BatchResult(
                successful_results=successful_results,
                failed_urls=failed_urls,
                batch_type=batch.batch_type
            )
            
        except Exception as e:
            # If batch processing fails entirely, mark all URLs as failed
            return BatchResult(
                successful_results={},
                failed_urls={url: str(e) for url in batch.urls},
                batch_type=batch.batch_type
            ) 