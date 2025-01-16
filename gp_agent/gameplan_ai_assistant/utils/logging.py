import frappe

def log_debug(message: str):
    """Helper function to log debug messages to both file and console"""
    print(f"DEBUG: {message}")
    frappe.logger().debug(message) 