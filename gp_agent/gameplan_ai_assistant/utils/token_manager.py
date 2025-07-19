import json
from typing import Dict, Any, Optional
# import tiktoken  # Commented out due to Azure server blocking in Russia
from transformers import AutoTokenizer
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
            Uses transformers tokenizer as fallback due to Azure server blocking
            This provides accurate token counting for most models
        """
        self.model = model
        self.max_tokens = max_tokens
        
        # Initialize tokenizer based on model
        self.tokenizer = self._get_tokenizer(model)
        
    def _get_tokenizer(self, model: str):
        """Get appropriate tokenizer for the model"""
        try:
            # Map model names to appropriate tokenizer models
            tokenizer_mapping = {
                # OpenAI models
                'gpt-4': 'gpt2',
                'gpt-3.5-turbo': 'gpt2',
                'gpt-4o': 'gpt2',
                'gpt-4o-mini': 'gpt2',
                
                # Google models - use T5 tokenizer as approximation
                'google/gemini-flash-1.5': 't5-base',
                'google/gemini-pro': 't5-base',
                'google/gemini-pro-1.5': 't5-base',
                'google/gemini-2.0-flash-001': 't5-base',
                
                # Anthropic models - use GPT2 as approximation
                'anthropic/claude-3': 'gpt2',
                'anthropic/claude-3.5': 'gpt2',
                'anthropic/claude-3.5-sonnet': 'gpt2',
                
                # Default fallback
                'default': 'gpt2'
            }
            
            # Get tokenizer model name
            tokenizer_model = tokenizer_mapping.get(model, tokenizer_mapping['default'])
            
            # Load tokenizer
            return AutoTokenizer.from_pretrained(tokenizer_model)
            
        except Exception as e:
            # Fallback to simple word counting if tokenizer fails
            print(f"Warning: Could not load tokenizer for {model}: {e}")
            return None
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        if not text:
            return 0
            
        if self.tokenizer:
            try:
                # Use transformers tokenizer for accurate counting
                tokens = self.tokenizer.encode(text)
                return len(tokens)
            except Exception as e:
                print(f"Warning: Tokenizer failed, falling back to word counting: {e}")
                return self._count_tokens_simple(text)
        else:
            # Fallback to simple word counting
            return self._count_tokens_simple(text)
    
    def _count_tokens_simple(self, text: str) -> int:
        """Simple word-based token counting as fallback"""
        if not text:
            return 0
            
        # Simple approximation: ~1.3 tokens per word for English text
        # This is a reasonable approximation for most models
        words = text.split()
        return int(len(words) * 1.3)
        
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