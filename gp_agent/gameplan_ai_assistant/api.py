"""
API endpoints for GamePlan AI Assistant.
"""

import frappe
from frappe.utils.safe_exec import check_safe_sql_query
from frappe.utils import cint
from typing import Dict, Any, List, Optional
from .tools import register_tools
from .tools.registry import get_tool_schemas, execute_tool
from .scheduler_jobs import schedule_agent_runs as _schedule_agent_runs

def get_available_tools() -> List[Dict[str, Any]]:
    """Get list of available tools and their schemas
    
    Returns:
        List of tool schemas in OpenAI format
    """
    return get_tool_schemas()

@frappe.whitelist()
async def execute_tool_call(
    call_data: Dict[str, Any],
    parent_log: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Execute tool call with provided data
    
    Args:
        call_data: Tool call data in OpenAI format
        parent_log: Optional parent log ID for tracking
        
    Returns:
        Tool execution result or None if tool not found
    """
    return await execute_tool(call_data, parent_log)

@frappe.whitelist()
def process_pending_responses():
    """Process pending GP Agent Log entries"""
    frappe.has_permission("GP Agent Settings", "write", throw=True)
    from .scheduler_jobs import process_pending_responses
    return process_pending_responses(is_background=False)

@frappe.whitelist()
def schedule_agent_runs():
    """API endpoint to manually trigger agent runs"""
    frappe.has_permission("GP Agent Settings", "write", throw=True)
    _schedule_agent_runs(is_background=False)

@frappe.whitelist()
def process_single_response(log_name):
    """Process a single GP Agent Log entry"""
    frappe.has_permission("GP Agent Log", "write", throw=True)
    from .scheduler_jobs import process_single_response
    return process_single_response(log_name, is_background=False)

@frappe.whitelist()
def process_pending_logs():
    """API endpoint to manually process pending logs"""
    frappe.has_permission("GP Agent Settings", "write", throw=True)
    from .scheduler_jobs import process_pending_logs as _process_pending_logs
    _process_pending_logs(is_background=False)

def setup():
    """Initialize module by registering tools"""
    register_tools() 