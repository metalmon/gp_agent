import frappe
import uuid

def get_short_id(full_id: str, length: int = 8) -> str:
    """Get short ID from full ID by taking last N characters
    
    Args:
        full_id: Full ID to shorten
        length: Number of characters to keep (default: 8)
        
    Returns:
        Short ID string
    """
    return full_id[-length:] if full_id else ""

def get_tool_log_name(parent_log: str, tool_name: str) -> str:
    """Generate a name for GP Agent Tool Log
    
    Args:
        parent_log: Parent log ID
        tool_name: Name of the tool
        
    Returns:
        Generated name string
    """
    timestamp = frappe.utils.now_datetime().strftime("%Y%m%d-%H%M%S")
    unique_hash = uuid.uuid4().hex[:8]  # Get first 8 chars of UUID
    
    return f"TOOL-{tool_name}-{timestamp}-{unique_hash}" 