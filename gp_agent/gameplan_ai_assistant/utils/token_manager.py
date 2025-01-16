import json
from typing import Dict, Any, Optional
import tiktoken
from ..exceptions import TokenLimitError

class TokenManager:
    """Manages token counting and context compression"""
    
    # Default encoding to use as fallback
    DEFAULT_ENCODING = "cl100k_base"
    
    def __init__(self, model: str, max_tokens: int):
        """Initialize token manager with model and max tokens
        
        Args:
            model: Model identifier (e.g. 'gpt-4', 'google/gemini-flash-1.5')
            max_tokens: Maximum number of tokens allowed
            
        Note:
            Uses cl100k_base as a fallback encoding for non-OpenAI models
            This provides a reasonable approximation for most modern models
        """
        self.model = model
        self.max_tokens = max_tokens
        
        try:
            # Try to get model-specific encoding first
            self.encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to default encoding for non-OpenAI models
            self.encoder = tiktoken.get_encoding(self.DEFAULT_ENCODING)
            
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        return len(self.encoder.encode(text))
        
    def count_json(self, data: Any) -> int:
        """Count tokens in any JSON-serializable data"""
        if data is None:
            return 0
        return self.count_tokens(json.dumps(data))
        
    def count_context(self, context: Dict[str, Any]) -> int:
        """Count total tokens in context
        
        Args:
            context: Context data with any structure
            
        Returns:
            Total number of tokens
        """
        return self.count_json(context)
        
    def get_completion_tokens(self, context: Dict[str, Any]) -> int:
        """Get available tokens for completion
        
        Args:
            context: Context data with any structure
            
        Returns:
            Number of tokens available for completion
        """
        context_tokens = self.count_context(context)
        available = self.max_tokens - context_tokens
        
        if available <= 0:
            raise TokenLimitError(f"Context size ({context_tokens} tokens) exceeds max tokens ({self.max_tokens})")
            
        return available
        
    def validate_and_compress(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate context size and compress if needed
        
        Args:
            context: Context data with any structure
            
        Returns:
            Validated and possibly compressed context
            
        Raises:
            TokenLimitError: If context is too large even after compression
        """
        # First check total size
        total_tokens = self.count_context(context)
        
        if total_tokens <= self.max_tokens:
            return context
            
        # Context is too large, try to compress
        compressed = self._compress_context(context)
        compressed_tokens = self.count_context(compressed)
        
        if compressed_tokens <= self.max_tokens:
            return compressed
            
        raise TokenLimitError(
            f"Context too large ({total_tokens} tokens) and could not be compressed below limit ({self.max_tokens} tokens)"
        )
        
    def _compress_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compress context by truncating messages and system prompt
        
        Compression steps:
        1. Try keeping last 5 messages
        2. If still too large, try keeping last 3 messages
        3. If still too large, try keeping last message
        4. If still too large, truncate system prompt from bottom
        
        Args:
            context: Context data with any structure
            
        Returns:
            Compressed context
        """
        # Make a copy to avoid modifying original
        compressed = json.loads(json.dumps(context))
        
        # Try keeping different numbers of messages
        if "messages" in compressed:
            for num_messages in [5, 3, 1]:
                compressed["messages"] = context["messages"][-num_messages:]
                if self.count_context(compressed) <= self.max_tokens:
                    return compressed
            
        # If still too large, try truncating system prompt
        if "system_prompt" in compressed:
            system_prompt = compressed["system_prompt"]
            
            # If system prompt is a string, truncate it
            if isinstance(system_prompt, str):
                # Split into lines and keep removing from bottom until it fits
                lines = system_prompt.splitlines()
                while len(lines) > 1 and self.count_context(compressed) > self.max_tokens:
                    lines.pop()
                    compressed["system_prompt"] = "\n".join(lines)
            
            # If system prompt is a dict/object, try truncating its content field
            elif isinstance(system_prompt, dict) and "content" in system_prompt:
                lines = system_prompt["content"].splitlines()
                while len(lines) > 1 and self.count_context(compressed) > self.max_tokens:
                    lines.pop()
                    system_prompt["content"] = "\n".join(lines)
                compressed["system_prompt"] = system_prompt
            
        return compressed 