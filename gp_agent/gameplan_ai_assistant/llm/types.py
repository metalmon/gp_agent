from typing import TypedDict, List, Dict, Any, Literal, Optional

class ToolCall(TypedDict):
    """Tool call data structure"""
    tool_name: str
    tool_id: str
    parameters: Dict[str, Any]
    status: str
    response: Optional[Dict[str, Any]]

class ContextData(TypedDict):
    """Context data structure"""
    system_prompt: str
    context: str
    tool_calls: List[ToolCall]

class Message(TypedDict):
    """Message structure for LLM API"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_call_id: Optional[str]

class ChatCompletionRequest(TypedDict):
    """Chat completion request structure"""
    messages: List[Message]
    model: str
    temperature: float
    max_tokens: int
    top_p: float

class TokenUsage(TypedDict):
    """Token usage structure"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(TypedDict):
    """Chat completion response structure"""
    id: str
    object: str
    created: int
    model: str
    usage: TokenUsage
    choices: List[Dict[str, Any]] 