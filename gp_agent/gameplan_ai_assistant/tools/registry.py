"""
Tool registration and execution module.
Provides a centralized way to register and execute tools.
"""

from typing import Dict, List, Any, Optional, Type
from .base.registry import ToolRegistry
from .base import BaseTool
import frappe

# Global registry instance
_registry = ToolRegistry(schema_type="OpenAI")

def register_tool(tool: BaseTool) -> None:
    """Register a tool with the global registry
    
    Args:
        tool: Tool instance to register
    """
    frappe.logger("gameplan").debug(f"Registering tool: {tool.name}")
    _registry.register(tool)

def clear_registry() -> None:
    """Clear all registered tools"""
    frappe.logger("gameplan").debug("Clearing tool registry")
    _registry.clear()

def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get schemas for all registered tools
    
    Returns:
        List of tool schemas in OpenAI format
    """
    return _registry.get_schemas()

def get_available_tools() -> Dict[str, Type[BaseTool]]:
    """Get dictionary of available tools
    
    Returns:
        Dictionary mapping tool names to their classes
    """
    return _registry.get_tools()

def execute_tool(
    call_data: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Execute tool call with provided data
    
    Args:
        call_data: Tool call data in OpenAI format
        parent_log: Optional parent log ID for tracking
        settings: Optional settings dictionary with API credentials and other settings
        
    Returns:
        Tool execution result or None if tool not found
        
    Raises:
        ValueError: If tool not found or parameters invalid
        Exception: If execution fails
    """
    try:
        # Execute tool
        result = _registry.execute_tool(call_data, settings=settings)
        return result
        
    except Exception as e:
        frappe.logger("gameplan").error(f"Error executing tool: {str(e)}")
        raise 