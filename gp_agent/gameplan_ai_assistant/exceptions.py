class GPAgentException(Exception):
    """Base exception class for GP Agent errors"""
    pass 

class TokenLimitError(Exception):
    """Raised when token limit is exceeded"""
    pass 

class LLMError(GPAgentException):
    """Raised when there is an error with the LLM service"""
    pass 