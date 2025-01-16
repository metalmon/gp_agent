from typing import Dict, List, Any
from .base import BaseMessageFormatter
from ..base import Message
from ...utils.logging import log_debug
import json

class AnthropicContextFormatter(BaseMessageFormatter):
    """Anthropic-specific message formatter implementation"""
    
    def format_to_model_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format messages according to Anthropic schema
        
        Message roles are handled as follows:
        1. tool - converted to assistant role (Anthropic doesn't support tool role)
        2. assistant with tool_calls - messages requesting tool execution
        3. user/assistant - regular messages (content is formatted with metadata)
        
        Tool calls are converted from OpenAI format to Anthropic:
        - function.arguments -> function.parameters
        - Anthropic uses the same function name and id fields
        
        Tool calls and responses must be properly paired:
        - Each tool call must have a corresponding tool response
        - Tool responses must immediately follow their tool calls
        """
        formatted = []
        pending_tool_calls = {}  # Track pending tool calls by ID
        
        for msg in messages:
            if msg.role == 'tool':
                # Tool response message - convert to assistant since Anthropic doesn't have tool role
                if msg.tool_call_id:
                    formatted.append({
                        'role': 'assistant',
                        'content': msg.content
                    })
                    # Mark this tool call as responded
                    if msg.tool_call_id in pending_tool_calls:
                        del pending_tool_calls[msg.tool_call_id]
            elif msg.tool_calls:
                # Assistant message with tool calls - convert from OpenAI format
                tool_call_message = {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': []
                }
                
                for i, call in enumerate(msg.tool_calls):
                    # Format tool call ID to match API response format: tool_<index>_<name>
                    call_id = call.get('id', f'tool_{i}_{call.get("name", "unknown")}')
                    tool_call = {
                        'id': call_id,
                        'type': 'function',
                        'function': {
                            'name': call.get('name'),
                            'parameters': call.get('arguments', {})  # OpenAI arguments -> Anthropic parameters
                        }
                    }
                    # Only add index for tool calls, not responses
                    if msg.role == 'assistant':
                        tool_call['index'] = i
                    tool_call_message['tool_calls'].append(tool_call)
                    pending_tool_calls[call_id] = tool_call
                
                formatted.append(tool_call_message)
            else:
                # Regular user/assistant message - format content with metadata
                formatted_content = self.format_message_content(msg)
                formatted.append({
                    'role': self._convert_role(msg.role),
                    'content': formatted_content
                })
        
        # If there are any pending tool calls without responses, that's an error
        if pending_tool_calls:
            log_debug(f"Warning: Found {len(pending_tool_calls)} tool calls without responses:")
            for call_id, call in pending_tool_calls.items():
                log_debug(f"- Missing response for tool call {call_id} ({call['function']['name']})")
        
        return formatted
    
    def parse_model_response(self, response: Dict[str, Any]) -> Message:
        """Parse Anthropic response into a Message object
        
        Response types:
        1. Regular message - convert content from Markdown to HTML
        2. Tool call message - content is None, includes tool_calls array
        
        Note: Anthropic doesn't support tool responses directly, they are handled
        as regular assistant messages
        """
        role = self._convert_role_back(response.get('role', 'assistant'))
        content = response.get('content')
        tool_calls = response.get('tool_calls')
        
        # For tool call messages, get name and id from first tool call
        tool_name = None
        tool_call_id = None
        if tool_calls and len(tool_calls) > 0:
            first_call = tool_calls[0]
            tool_name = first_call.get('function', {}).get('name')
            tool_call_id = first_call.get('id')
        
        # Clean service headers only for assistant messages and convert to HTML
        if content:
            if role == 'assistant':
                content = self.clean_service_headers(content)
            if role in ['assistant', 'user']:
                content = self.markdown_to_html(content)
        
        return Message(
            content=content,
            tasks=[],
            context={},
            role=role,
            tool_calls=tool_calls,
            tool_name=tool_name,
            tool_call_id=tool_call_id
        )
    
    def _convert_role(self, role: str) -> str:
        """Convert role to Anthropic format"""
        role_map = {
            'user': 'user',
            'assistant': 'assistant',
            'tool': 'assistant',  # Anthropic doesn't have tool role
            'system': 'system'
        }
        return role_map.get(role, role)
    
    def _convert_role_back(self, role: str) -> str:
        """Convert Anthropic role back to our format"""
        role_map = {
            'user': 'user',
            'assistant': 'assistant',
            'system': 'system'
        }
        return role_map.get(role, role) 