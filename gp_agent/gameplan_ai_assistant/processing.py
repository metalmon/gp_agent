import json
import traceback
import frappe
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from frappe.utils.data import get_datetime_str
from .llm.openai import OpenAIClient
from .llm.anthropic import AnthropicClient
from .llm.schema import TokenUsage
from .gameplan_api import GameplanAPI
from .context.factory import ContextFactory
from .tools.registry import get_tool_schemas, execute_tool, get_available_tools
from .tools.validation import ToolCallValidationResult, validate_tool_call
from .utils.logging import log_debug
from .utils.token_manager import TokenManager, TokenLimitError
from .llm.base import BaseLLMClient
from .llm.errors import APIError, SchemaError
from .exceptions import LLMError
from .utils.settings import get_settings_overrides
from .context.base import Message

# Type alias for GP Agent Log document
GPAgentLog = Any  # frappe.model.document.Document 
Log = GPAgentLog  # Alias for type hints

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return get_datetime_str(obj)
        return super().default(obj)

def get_llm_client(settings: Optional[Dict[str, Any]] = None) -> BaseLLMClient:
    """Get LLM client based on settings
    
    Args:
        settings: Settings dictionary to use. If not provided, base settings from GP Agent Settings will be used.
        
    Returns:
        LLM client instance
    """
    # Get settings from GP Agent Settings if not provided
    if settings is None:
        raise ValueError(f"No settings provided")
    
    # Ensure api_schema is lowercase
    api_schema = settings.get('api_schema', '').lower()
    
    # Create client based on API schema
    if api_schema == 'openai':
        return OpenAIClient(settings=settings)
    elif api_schema == 'anthropic':
        return AnthropicClient(settings=settings)
    
    raise ValueError(f"Unsupported API schema: {api_schema}")

def create_failed_log(
    team_id: str,
    project_id: str,
    discussion_id: str,
    agent_user: str,
    context: Dict[str, Any],
    model: str = None,
    temperature: float = None,
    token_count: int = None,
    max_tokens: int = None,
    top_p: float = None,
    top_k: int = None,
    context_depth: int = None,
    last_message_id: str = None,
    parent_log_id: str = None,
    is_tool_call: bool = False,
    tools: List[Dict[str, Any]] = None,
    error: str = None
) -> "Document":
    log_data = {
        "doctype": "GP Agent Log",
        "status": "Failed",
        "creation_timestamp": frappe.utils.now_datetime(),
        "model": model if model is not None else None,
        "default_user": agent_user if agent_user is not None else None,
        "team_id": team_id if team_id is not None else None,
        "project_id": project_id if project_id is not None else None,
        "discussion_id": discussion_id if discussion_id is not None else None,
        "last_message_id": last_message_id if last_message_id is not None else None,
        "parent_log_id": parent_log_id if parent_log_id is not None else None,
        "token_count": token_count if token_count is not None else None,
        "max_tokens": max_tokens if max_tokens is not None else None,
        "temperature": temperature if temperature is not None else None,
        "top_p": top_p if top_p is not None else None,
        "top_k": top_k if top_k is not None else None,
        "context_depth": context_depth if context_depth is not None else None,
        "system_prompt": json.dumps(context.get("system_prompt", {}), ensure_ascii=False, cls=DateTimeEncoder) if context.get("system_prompt") else None,
        "messages": json.dumps(context.get("messages", []), ensure_ascii=False, cls=DateTimeEncoder) if context.get("messages") else None,
        "tools": json.dumps(tools, ensure_ascii=False, cls=DateTimeEncoder) if tools else None,
        "is_tool_call": is_tool_call
    }

        # Create log document directly without enqueuing
    try:
        doc = frappe.get_doc(log_data)
        doc.insert()
        log_debug(f"Created failed log {doc.name}")
        return doc
    except Exception as e:
        log_debug(f"Error creating failed log: {str(e)}")
        raise LLMError(f"Failed to create agent with error: {error}")

def create_agent_log(
    team_id: str,
    project_id: str,
    discussion_id: str,
    agent_user: str,
    context: Dict[str, Any],
    api_schema: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    top_k: int = None,
    context_depth: int = None,
    last_message_id: str = None,
    parent_log_id: str = None,
    is_tool_call: bool = False
):
    """Create a new agent log document"""
    settings = frappe.get_single("GP Agent Settings")
    
    log_debug("=== Creating Agent Log ===")
    log_debug(f"Team ID: {team_id}")
    log_debug(f"Project ID: {project_id}")
    log_debug(f"Discussion ID: {discussion_id}")
    log_debug(f"Last message ID: {last_message_id}")
    log_debug(f"Parent log ID: {parent_log_id}")
    
    # Validate agent user exists
    if not frappe.db.exists("User", agent_user):
        error_msg = f"Agent user {agent_user} not found"
        log_debug(error_msg)
        
        # Create failed log
        log_data = {
            "doctype": "GP Agent Log",
            "status": "Failed",
            "api_schema": api_schema,
            "model": model,
            "creation_timestamp": frappe.utils.now_datetime(),
            "error": error_msg,
            "default_user": agent_user,  # Save the invalid user for debugging
            "team_id": team_id,
            "project_id": project_id,
            "discussion_id": discussion_id,
            "last_message_id": last_message_id,
            "parent_log_id": parent_log_id,
            "is_tool_call": is_tool_call,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "context_depth": context_depth,
            "tools": tools,
            "error": error_msg
        }
        create_failed_log(**log_data)
        raise
    
    # Get model settings with defaults from GP Agent Settings
    model = model or settings.model
    
    # Validate model is set
    if not model:
        log_debug("Model is not set in settings or parameters")
        raise frappe.ValidationError("Please select a model in GP Agent Settings before running the agent")
        
    max_tokens = max_tokens or settings.max_tokens
    temperature = temperature if temperature is not None else settings.temperature
    top_p = top_p if top_p is not None else settings.top_p
    top_k = top_k if top_k is not None else settings.top_k
    context_depth = context_depth if context_depth is not None else settings.context_depth
    
    # Create token manager
    token_manager = TokenManager(model, max_tokens)
    
    try:
        # Validate and compress context if needed
        context = token_manager.validate_and_compress(context)
        
        # Get available tokens for completion
        available_tokens = token_manager.get_completion_tokens(context)
        total_tokens = token_manager.count_context(context)
        
        log_debug(f"Total tokens: {total_tokens}")
        log_debug(f"Available tokens for completion: {available_tokens}")
        
        # Get tools
        tools = get_tool_schemas()
        
        # Prepare log data
        log_data = {
            "doctype": "GP Agent Log",
            "status": "Queued",
            "creation_timestamp": frappe.utils.now_datetime(),
            "model": model,
            "default_user": agent_user,
            "team_id": team_id,
            "project_id": project_id,
            "discussion_id": discussion_id,
            "last_message_id": last_message_id,
            "parent_log_id": parent_log_id,
            "token_count": total_tokens,
            "max_tokens": available_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "context_depth": context_depth,
            "system_prompt": json.dumps(context.get("system_prompt", {}), ensure_ascii=False, cls=DateTimeEncoder),
            "messages": json.dumps(context.get("messages", []), ensure_ascii=False, cls=DateTimeEncoder),
            "tools": json.dumps(tools, ensure_ascii=False, cls=DateTimeEncoder),
            "is_tool_call": is_tool_call
        }

        # Enqueue log creation with full method path
        frappe.enqueue(
            method="gp_agent.gameplan_ai_assistant.processing._create_agent_log",
            queue="default",
            timeout=300,
            log_data=log_data,
            now=True
        )
        
        log_debug("Log creation enqueued successfully")
        #return frappe.get_doc(log_data)
        
    except TokenLimitError as e:
        log_debug(f"Token limit exceeded: {str(e)}")
        # Create failed log
        log_data = {
            "doctype": "GP Agent Log",
            "status": "Failed",
            "model": model,
            "creation_timestamp": frappe.utils.now_datetime(),
            "error": error_msg,
            "default_user": agent_user,  # Save the invalid user for debugging
            "team_id": team_id,
            "project_id": project_id,
            "discussion_id": discussion_id,
            "last_message_id": last_message_id,
            "parent_log_id": parent_log_id,
            "is_tool_call": is_tool_call,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "token_count": total_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "context_depth": context_depth,
            "tools": tools,
            "error": error_msg
        }
        create_failed_log(**log_data)
        raise
    except Exception as e:
        log_debug(f"Error creating agent log: {str(e)}")
        raise LLMError(f"Failed to create agent log: {str(e)}")

def _create_agent_log(log_data: Dict[str, Any]) -> None:
    """Create agent log document in background
    
    Args:
        log_data: Log data dictionary
    """
    try:
        doc = frappe.get_doc(log_data)
        doc.insert()
        frappe.db.commit()
        log_debug(f"Created log {doc.name}")
        
    except Exception as e:
        log_debug(f"Error creating log in background: {str(e)}")
        # Convert datetime objects to strings for error logging
        error_log_data = json.dumps(log_data, indent=2, cls=DateTimeEncoder)
        frappe.log_error(
            title="GP Agent Log Creation Failed",
            message=f"Error creating log in background: {str(e)}\nLog data: {error_log_data}"
        )

def process_single_response(response_data: Dict[str, Any], log: Log, settings: Any) -> None:
    """Process single response from API
    
    Args:
        response_data: Response data from API
        log: Log entry to update
        settings: Settings object
    """
    try:
        # Save raw response
        log.db_set('response', json.dumps(response_data, ensure_ascii=False))
        
        #log_debug(f"Saved response to log: {log.response}")
                    
        # Process both tool calls and message content if present
        has_tool_calls = False
        has_message = False
        error_msg = ""
        
        # Process message content if present and not empty
        if content := response_data.get("content"):
            log_debug("Processing message content")
            try:
                process_message_content(content, log, settings)
                has_message = True
            except Exception as e:
                error_msg = error_msg +f"Error processing message content: {str(e)}"

        # Process tool calls if present
        if tool_calls := response_data.get("tool_calls"):
            log_debug("Processing tool calls")
            try:
                process_tool_calls(tool_calls, log, settings, content)
                has_tool_calls = True
            except Exception as e:
                error_msg = error_msg + f"Error processing tool calls: {str(e)}/n"
            
        # Set final status based on processing results
        if error_msg:
            log_debug(error_msg)
            log.db_set('status', 'Error')
            log.db_set('error', f"{log.error}\n{error_msg}")
            return
            
        # If neither tool calls nor message content present, mark as error
        if not (has_tool_calls or has_message):
            error_msg = "Response contains neither tool calls nor message content"
            log_debug(error_msg)
            log.db_set('error', error_msg)
            retry_count = (log.retry_count or 0) + 1
            log.db_set('retry_count', retry_count)
        
            # Set status based on retry count
            if retry_count >= settings.max_retries:
                log.db_set('status', 'Failed')
            else:
                log.db_set('status', 'Error')
            return
            
        # All components processed successfully
        log.db_set('status', 'Completed')
        if not log.completion_timestamp:
            log.db_set('completion_timestamp', frappe.utils.now_datetime())
            
    except Exception as e:
        error_msg = f"Error in process_single_response: {str(e)}"
        log_debug(error_msg)
        # Increment retry count
        retry_count = (log.retry_count or 0) + 1
        log.db_set('retry_count', retry_count)
        
        # Set status based on retry count
        if retry_count >= settings.max_retries:
            log.db_set('status', 'Failed')
        else:
            log.db_set('status', 'Error')
        log.db_set('error', f"{log.error}\n{error_msg}")

def process_message_content(content: str, log: Log, settings: Any) -> bool:
    """Process message content from API response

    Args:
        content: Message content from API
        log: Log entry to update
        settings: Settings object
    """
    if not content or not content.strip():
        return False
        
    try:
        # Validate user exists
        if not frappe.db.exists("User", log.default_user):
            error_msg = f"User {log.default_user} not found"
            log_debug(error_msg)
            log.db_set('status', 'Failed')
            log.db_set('error', f"{log.error}\n{error_msg}")
            return False
            
        # Get settings and create formatter
        _, formatter = ContextFactory.create(settings)
        
        # Convert markdown to HTML using formatter's new method
        html_content = formatter.format_content(content)
        
        # Set user to agent user for message creation
        #frappe.set_user(log.default_user)

        # Create comment using GameplanAPI under agent user context
        try:    
            old_user = frappe.session.user
            frappe.set_user(log.default_user)
            api = GameplanAPI(log.default_user)
            message_result = api.create_comment(log.discussion_id, html_content)
            frappe.set_user(old_user)
        except Exception as e:
            log_debug(f"Error creating comment: {str(e)}")
            log.db_set('status', 'Error')
            log.db_set('error', f"{log.error}\n{str(e)}")
            return False
        
        # Update completion timestamp if not already set
        if not log.completion_timestamp:
            log.db_set('completion_timestamp', message_result.get("creation") if message_result else frappe.utils.now_datetime())
        
        return True
    
    except Exception as e:
        error_msg = f"Error creating message: {str(e)}"
        log_debug(error_msg)
        log.db_set('status', 'Error')
        log.db_set('error', f"{log.error}\n{error_msg}")
        return False

def process_tool_calls(tool_calls: Optional[List[Dict[str, Any]]], log: Log, settings: Any, content: Optional[str] = None) -> bool:
    """Process tool calls from API response
       Save tool calls to database in format - Assistant tool call message and tool call result for each tool call
       If tool call is splitted, process each splitted tool call and combine results in one message
    Args:
        tool_calls: List of tool calls to process
        log: Log entry to update
        settings: Settings object
    Returns:
        True if tool calls were processed, False otherwise
    """
    if not tool_calls:
        return False
        
    try:
              
        # Inherit settings from parent log
        settings.api_schema = log.api_schema
        settings.model = log.model
        settings.temperature = log.temperature
        settings.max_tokens = log.max_tokens
        settings.top_p = log.top_p
        settings.top_k = log.top_k
        settings.context_depth = log.context_depth
        settings.default_user = log.default_user
        
        # Get settings dict with decrypted passwords
        settings_dict = settings.as_dict()
        settings_dict['api_schema'] = log.api_schema
        settings_dict['context_builder'] = 'simple'  # Use SimpleContextBuilder for tool calls
        
        # Create builder and formatter
        builder, formatter = ContextFactory.create(settings_dict)
        
       
        # Get API credentials
        api_key = settings.get_password('google_search_api_key')
        search_engine_id = settings.google_search_engine_id
        
        # Only set if we have valid values
        if api_key:
            settings_dict['google_search_api_key'] = api_key
        if search_engine_id:
            settings_dict['google_search_engine_id'] = search_engine_id
            
        log_debug(f"Settings dict: google_search_api_key={bool(settings_dict.get('google_search_api_key'))}, google_search_engine_id={bool(settings_dict.get('google_search_engine_id'))}")
        
        # Get existing messages and available tools
        messages = json.loads(log.messages)
        available_tools = get_available_tools()

        # Process each tool call
        for tool_call in tool_calls:
            try:              
                # Validate tool call
                validation_result = validate_tool_call(tool_call, available_tools)
                log_debug(f"Validation result: {validation_result}")
                # Create a single tool log for this call
                tool_log = frappe.get_doc({
                    "doctype": "GP Agent Tool Log",
                    "parent_log": log.name,
                    "tool_name": tool_call.get("function", {}).get("name", ""),  # Get tool name from function object
                    "tool_id": tool_call.get("id", "tool_0"),
                    "original_call": json.dumps(tool_call, ensure_ascii=False),  # Save original call
                    "tool_parameters": json.dumps(tool_call.get("arguments", {}), ensure_ascii=False),
                    "validation_status": validation_result.metrics.get("validation_status"),
                    "validation_errors": json.dumps([e.to_dict() for e in validation_result.errors], ensure_ascii=False),
                    "fix_details": json.dumps({
                        "strategy": validation_result.metrics.get("strategy", "split_and_match"),  # Strategy for handling concatenated tools
                        "metrics": validation_result.metrics
                    }, ensure_ascii=False)
                })
                tool_log.insert()

                result = []                
                # Process each valid tool call in splitted calls and combose results in one message
                if validation_result.valid_calls.count > 1:
                    
                    # Track results for all valid calls
                    for valid_call in validation_result.valid_calls:
                        try:
                            # Execute tool
                            tool_name = valid_call.get("name")
                            tool_args = valid_call.get("arguments")
                            
                            log_debug(f"Executing tool {tool_name} with args: {tool_args} from splitted tool call")
                            result.append(execute_tool({
                                "name": tool_name,
                                "arguments": tool_args
                            }, settings=settings_dict))   
                        except Exception as e:
                            log_debug(f"Error executing tool {tool_name} from splitted tool call: {str(e)}")
                            log_debug(f"Exception type: {type(e)}")
                            log_debug(f"Exception args: {e.args}")
                            log_debug(f"Traceback: {traceback.format_exc()}")
                            tool_log.db_set("error", str(e))
                            tool_log.db_set("status", "Error")
                            tool_log.db_set("tool_response", result)
                            continue
                        

                elif validation_result.valid_calls.count == 1:
                    # Execute tool
                    try:
                        tool_name = validation_result.valid_calls[0]["name"]
                        tool_args = validation_result.valid_calls[0]["arguments"]
                        log_debug(f"Executing tool {tool_name} with args: {tool_args} from single tool call")
                        result.append(execute_tool({
                            "name": tool_name,
                            "arguments": tool_args
                        }, settings=settings_dict))
                        #if result[-1]["error"]:
                        #    raise SchemaError(result[-1]["error"])
                    except Exception as e:
                        log_debug(f"Error executing tool {tool_name} from single tool call: {str(e)}")
                        tool_log.db_set("status", "Error")
                        tool_log.db_set("error", f"{tool_log.error}\n{str(e)}")
                        tool_log.db_set("tool_response", result)
                        continue
                else:
                    log_debug("No valid tool calls found")
                    tool_log.db_set("status", "Error")
                    tool_log.db_set("error", "No valid tool calls found")
                    continue
                    
                # Store all results in tool_response field
                if result:
                    tool_log.db_set("status", "Completed")
                    tool_log.db_set("tool_response", json.dumps(result, ensure_ascii=False))
                        
                    # Build a single tool call message for this tool log
                    tool_call_msg = builder.build_tool_call_message([{
                        "name": tool_call.get("function", {}).get("name", ""),
                        "arguments": tool_call.get("function", {}).get("arguments", {}),
                        "id": tool_call.get("id", "tool_0")
                    }])
                    #formatted_tool_call_msg = formatter.format_to_model_messages([tool_call_msg])
                    #messages.extend(formatted_tool_call_msg)
                    
                    # Build a single tool response message for this tool log
                    tool_response_msg = builder.build_tool_response_message(
                        content=result,
                        tool_name=tool_call.get("function", {}).get("name", ""),
                        tool_call_id=tool_call.get("id", "tool_0")
                    )
                    #log_debug(f"Tool response message: {tool_response_msg}")
                    formatted_tool_responses = formatter.format_to_model_messages([tool_call_msg, tool_response_msg])
                    #log_debug(f"Formatted responses: {formatted_tool_responses}")
                    messages.extend(formatted_tool_responses)
                else:
                    tool_log.db_set('status', 'Error')
                    tool_log.db_set('error', f"{tool_log.error}\nNo tool results generated from tool call")
                    continue
                    
            except Exception as e:
                log_debug(f"Error in tool call validation/logging/execution: {str(e)}")
                log_debug(f"Exception type: {type(e)}")
                log_debug(f"Exception args: {e.args}")
                log_debug(f"Traceback: {traceback.format_exc()}")
                tool_log.db_set("status", "Error")
                tool_log.db_set("error", f"{tool_log.error}\n{str(e)}")
                continue

        # If was message in response, add it to messages
        if content:
            message = builder.build_messages_context([content])
            formatted_message = formatter.format_to_model_messages(message)                                         
            messages.extend(formatted_message)
            
        # Create new agent log with all messages
        create_agent_log(
            team_id=log.team_id,
            project_id=log.project_id,
            discussion_id=log.discussion_id,
            last_message_id=log.last_message_id,
            agent_user=settings.default_user,
            context={
                'system_prompt': json.loads(log.system_prompt) if log.system_prompt else {},
                'messages': messages,
                'tools': json.loads(log.tools) if log.tools else []
            },
            api_schema=settings.api_schema,
            model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            top_p=settings.top_p,
            top_k=settings.top_k,
            context_depth=settings.context_depth,
            parent_log_id=log.name,
            is_tool_call=True
        )
        
        # Update completion timestamp if not already set
        if not log.completion_timestamp:
            log.db_set('completion_timestamp', frappe.utils.now_datetime())
            
    except Exception as e:
        log_debug(f"Error processing tool calls: {str(e)}")
        return False
    
    return True

def process_single_log(log_name: str, is_background: bool = True) -> None:
    """Process a single GP Agent Log"""
    # Get log document
    log = frappe.get_doc("GP Agent Log", log_name)
    if not log:
        print(f"Log {log_name} not found")
        return
        
    # Skip if already completed
    if log.status == "Completed":
        print(f"Log {log_name} already Completed")
        return
        
    log_debug(f"Processing log {log_name}...")
    
    try:
        # Get settings as Frappe document
        settings = get_settings_overrides(
            team_id=log.team_id,
            project_id=log.project_id,
            discussion_id=log.discussion_id
        )
        
        # Mark as processing atomically
        log.db_set('status', 'Processing')
        log.db_set('processing_timestamp', frappe.utils.now_datetime())
        
        # Get LLM client with minimal required settings
        client = get_llm_client({
            "api_schema": settings.api_schema,
            "base_url": settings.base_url,
            "api_key": settings.get_password('api_key'),
            "model": log.model,
            "temperature": log.temperature,
            "max_tokens": log.max_tokens,
            "top_p": log.top_p,
            "top_k": log.top_k
        })
        
        # Parse context data
        try:
            log_debug(f"Parsing context data from log {log_name}")
            #log_debug(f"Raw system_prompt: {log.system_prompt}")
            #log_debug(f"Raw messages: {log.messages}")
            #log_debug(f"Raw tools: {log.tools}")
            
            # Parse system prompt
            try:
                system_prompt = json.loads(log.system_prompt) if isinstance(log.system_prompt, str) else log.system_prompt or {}
                #log_debug(f"Parsed system_prompt: {json.dumps(system_prompt, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                log_debug(f"Error parsing system_prompt: {str(e)}")
                raise LLMError(f"Failed to parse system_prompt: {str(e)}")
                
            # Parse messages
            try:
                messages = json.loads(log.messages) if isinstance(log.messages, str) else log.messages or []
                #log_debug(f"Parsed messages: {json.dumps(messages, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                log_debug(f"Error parsing messages: {str(e)}")
                raise LLMError(f"Failed to parse messages: {str(e)}")
                
            # Parse tools
            try:
                tools = json.loads(log.tools) if isinstance(log.tools, str) else log.tools or []
                #log_debug(f"Parsed tools: {json.dumps(tools, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                log_debug(f"Error parsing tools: {str(e)}")
                raise LLMError(f"Failed to parse tools: {str(e)}")
                
        except json.JSONDecodeError as e:
            log_debug(f"Error parsing JSON from log fields: {str(e)}")
            log_debug(f"Traceback: {traceback.format_exc()}")
            raise LLMError(f"Failed to parse context data: {str(e)}")
        
        log_debug(f"Parsed context data: system_prompt={bool(system_prompt)}, messages={len(messages)}, tools={len(tools)}")
        

        # Make API request using client
        response_data = client.chat_completion(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            model=log.model,
            temperature=log.temperature,
            max_tokens=log.max_tokens,
            top_p=log.top_p,
            top_k=log.top_k
        )
        log_debug("Received response from API")

        # Update token counts atomically
        token_usage: TokenUsage = client.get_token_usage(response_data)
        if token_usage is not None:
            try:
                log_debug(f"Token usage from API: {json.dumps(token_usage, ensure_ascii=False)}")
                log.db_set('prompt_tokens', token_usage.get('prompt_tokens', 0))
                log.db_set('completion_tokens', token_usage.get('completion_tokens', 0))
                log.db_set('total_tokens', token_usage.get('total_tokens', 0))
                log_debug(f"Updated token counts: prompt={token_usage.get('prompt_tokens')}, completion={token_usage.get('completion_tokens')}, total={token_usage.get('total_tokens')}")
            except Exception as e:
                log_debug(f"Error updating token counts: {str(e)}")
                # Continue processing even if token counts fail

        # Process response with settings document
        process_single_response(response_data, log, settings)
            
    except (TokenLimitError, APIError, SchemaError) as e:
        error_message = str(e)
        log_debug(f"LLM error processing log {log_name}: {error_message}")
        
        # Update retry count atomically
        retry_count = (log.retry_count or 0) + 1
        
        # Check max retries
        if retry_count >= settings.max_retries:
            log.db_set('status', 'Failed')
            log.db_set('error', error_message)
        else:
            log.db_set('status', 'Error')
            log.db_set('retry_count', retry_count)
            log.db_set('error', error_message)
        
        # Log error for background jobs
        if is_background:
            frappe.log_error(
                title="GP Agent Log Processing Failed",
                message=f"Error processing log {log_name} after {retry_count} retries: {error_message}",
            )
        else:
            # Re-raise for UI display
            raise
        