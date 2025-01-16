from typing import List, Dict, Any
from dataclasses import dataclass
from ..exceptions import GPAgentException

@dataclass
class BatchResult:
    """Represents results from processing a batch of URLs"""
    successful_results: Dict[str, Any]  # URL -> result mapping
    failed_urls: Dict[str, str]  # URL -> error message mapping
    batch_type: str

class ResultAggregator:
    """Aggregates and processes results from multiple URL batches"""
    
    @classmethod
    def aggregate_results(cls, batch_results: List[BatchResult]) -> Dict[str, Any]:
        """
        Aggregate results from multiple batches into a single response
        
        Args:
            batch_results: List of BatchResult objects
            
        Returns:
            Dictionary containing:
            - successful_results: Dict[str, Any] - All successful results
            - failed_urls: Dict[str, str] - All failed URLs with error messages
            - stats: Dict with summary statistics
            
        Raises:
            GPAgentException: If aggregation fails
        """
        try:
            # Initialize result containers
            successful_results = {}
            failed_urls = {}
            stats = {
                'total_urls': 0,
                'successful': 0,
                'failed': 0,
                'by_type': {}
            }
            
            # Process each batch
            for result in batch_results:
                # Add successful results
                successful_results.update(result.successful_results)
                
                # Add failed URLs
                failed_urls.update(result.failed_urls)
                
                # Update statistics
                batch_total = len(result.successful_results) + len(result.failed_urls)
                stats['total_urls'] += batch_total
                stats['successful'] += len(result.successful_results)
                stats['failed'] += len(result.failed_urls)
                
                # Update type-specific stats
                if result.batch_type not in stats['by_type']:
                    stats['by_type'][result.batch_type] = {
                        'total': 0,
                        'successful': 0,
                        'failed': 0
                    }
                stats['by_type'][result.batch_type]['total'] += batch_total
                stats['by_type'][result.batch_type]['successful'] += len(result.successful_results)
                stats['by_type'][result.batch_type]['failed'] += len(result.failed_urls)
            
            return {
                'successful_results': successful_results,
                'failed_urls': failed_urls,
                'stats': stats
            }
            
        except Exception as e:
            raise GPAgentException(f"Failed to aggregate results: {str(e)}") 