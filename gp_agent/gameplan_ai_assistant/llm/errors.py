class LLMError(Exception):
    """Base class for LLM errors"""
    pass

class TokenLimitError(LLMError):
    """Raised when context exceeds token limit"""
    def __init__(self, message: str, current_tokens: int, max_tokens: int):
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens
        super().__init__(f"{message} (current: {current_tokens}, max: {max_tokens})")

class APIError(LLMError):
    """Raised when API request fails"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        self.status_code = status_code
        self.response = response
        error_msg = f"{message}"
        if status_code:
            error_msg += f" (status: {status_code})"
        if response:
            error_msg += f" - {response}"
        super().__init__(error_msg)

class SchemaError(LLMError):
    """Raised when there's an error in schema formatting or parsing"""
    pass

class ContextError(LLMError):
    """Raised when there's an error in context building or processing"""
    pass 