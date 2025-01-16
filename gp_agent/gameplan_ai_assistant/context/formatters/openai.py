from typing import Dict, List, Any
from .base import BaseMessageFormatter
from ..base import Message
from ...utils.logging import log_debug
from ...llm.errors import SchemaError
import json

class OpenAIContextFormatter(BaseMessageFormatter):
    """OpenAI-specific message formatter implementation"""
    
    def format_to_model_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format messages according to OpenAI schema
        
        Message roles are handled as follows:
        1. tool - tool response messages (content is preserved as-is)
        2. assistant with tool_calls - messages requesting tool execution (content is None)
        3. user/assistant - regular messages (content is formatted with metadata and tool instructions)
        
        Tool calls and responses must be properly paired:
        - Each tool call must have a corresponding tool response
        - Tool responses must immediately follow their tool calls
        """
        formatted = []
        pending_tool_calls = {}  # Track pending tool calls by ID
        
        for msg in messages:
            if msg.role == 'tool':
                # Tool response message - preserve content format and ensure it matches a call
                if msg.tool_call_id:
                    formatted.append({
                        'role': 'tool',
                        'content': msg.content,
                        'name': msg.tool_name,
                        'tool_call_id': msg.tool_call_id
                    })
                    # Mark this tool call as responded
                    if msg.tool_call_id in pending_tool_calls:
                        del pending_tool_calls[msg.tool_call_id]
            elif msg.tool_calls:
                # Assistant message with tool calls - track each call
                tool_call_message = {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': []
                }
                
                for i, call in enumerate(msg.tool_calls):
                    # Extract tool name and arguments based on format
                    # OpenAI format: {"function": {"name": "tool_name", "arguments": {...}}}
                    # Direct format: {"name": "tool_name", "arguments": {...}}
                    if "function" in call:
                        tool_name = call["function"].get("name", "unknown")
                        arguments = call["function"].get("arguments", {})
                    else:
                        tool_name = call.get("name", "unknown")
                        arguments = call.get("arguments", {})
                    
                    # Format tool call ID to match API response format: tool_<index>_<n>
                    call_id = call.get('id', f'tool_{i}_{tool_name}')
                    tool_call = {
                        'id': call_id,
                        'type': 'function',
                        'function': {
                            'name': tool_name,
                            'arguments': arguments
                        }
                    }
                    # Only add index for tool calls, not responses
                    if msg.role == 'assistant':
                        tool_call['index'] = i
                    tool_call_message['tool_calls'].append(tool_call)
                    pending_tool_calls[call_id] = tool_call
                
                formatted.append(tool_call_message)
            else:
                # Regular user/assistant message - format content with metadata and tool instructions
                formatted_content = self.format_message_content(msg)
                formatted.append({
                    'role': msg.role,
                    'content': formatted_content
                })
        
        # If there are any pending tool calls without responses, that's an error
        if pending_tool_calls:
            log_debug(f"Warning: Found {len(pending_tool_calls)} tool calls without responses:")
            for call_id, call in pending_tool_calls.items():
                log_debug(f"- Missing response for tool call {call_id} ({call['function']['name']})")
        
        return formatted
    
    def parse_model_response(self, response: Dict[str, Any]) -> Message:
        """Parse OpenAI response into a Message object
        
        Response types:
        1. Regular message - convert content from Markdown to HTML
        2. Tool call message - content is None, includes tool_calls array
        3. Tool response - preserve content format
        
        These correspond to messages created by:
        1. Regular messages - created by context builder from user/assistant messages
        2. Tool call messages - created by build_tool_call_message()
        3. Tool responses - created by build_tool_response_message()
        """
        role = response.get('role', 'assistant')
        content = response.get('content')
        
        # Get tool calls from either direct tool call response or regular message
        tool_calls = response.get('tool_calls', []) if response.get('type') == 'tool_call' else response.get('tool_calls')
        log_debug(f"Initial tool_calls: {json.dumps(tool_calls, indent=2)}")
        
        # For tool response messages, name and tool_call_id are in the root
        tool_name = response.get('name') if role == 'tool' else None
        tool_call_id = response.get('tool_call_id') if role == 'tool' else None
        
        log_debug(f"Parsing model response:")
        log_debug(f"- Role: {role}")
        log_debug(f"- Content: {content}")
        log_debug(f"- Tool calls: {tool_calls}")
        log_debug(f"- Tool name: {tool_name}")
        log_debug(f"- Tool call ID: {tool_call_id}")
                
        # Clean service headers only for assistant messages and convert to HTML
        if content:
            if role == 'assistant':
                content = self.clean_service_headers(content)
            if role in ['assistant', 'user']:
                content = self.markdown_to_html(content)
        
        # Create message with empty context and tasks
        # Context and tasks will be populated by the context builder if needed
        return Message(
            content=content,
            tasks=[],
            context={},
            role=role,
            tool_calls=tool_calls,  # Pass tool_calls as is
            tool_name=tool_name,  # Only for tool response messages
            tool_call_id=tool_call_id  # Only for tool response messages
        ) 