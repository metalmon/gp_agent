from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from typing import Dict, Any, Optional
import json

class GPAgentToolLog(Document):
    def validate(self):
        """Validate tool log
        
        Ensures:
            - Parent log exists
            - Timestamps are valid
        """
        if not self.parent_log:
            frappe.throw("Parent log is required")
            
        if self.status == "Processing" and not self.processing_timestamp:
            self.processing_timestamp = frappe.utils.now_datetime()
            
        self.sync_content_fields()
    
    def sync_content_fields(self):
        """Sync JSON fields with their human-readable counterparts"""
        if self.tool_parameters:
            try:
                params = json.loads(self.tool_parameters)
                self.tool_parameters_content = json.dumps(params, indent=2)
            except:
                self.tool_parameters_content = self.tool_parameters
                
        if self.tool_response:
            try:
                response = json.loads(self.tool_response)
                self.tool_response_content = json.dumps(response, indent=2)
            except:
                self.tool_response_content = self.tool_response
    
    def before_save(self):
        """Update timestamps and sync fields before saving"""
        self.validate()

    def before_insert(self):
        """Initialize default values"""
        if not self.creation_timestamp:
            self.creation_timestamp = frappe.utils.now_datetime()
        
        if not self.status:
            self.status = "Queued"

    def start_processing(self):
        """Mark tool log as processing"""
        self.status = "Processing"
        self.processing_timestamp = frappe.utils.now_datetime()
        self.save()

    def mark_completed(self, response: dict) -> None:
        """Mark tool log as completed with response
        
        Args:
            response: Tool execution response
        """
        self.status = "Completed"
        self.tool_response = json.dumps(response)
        self.save()
        
    def mark_failed(self, error: str) -> None:
        """Mark tool log as failed with error
        
        Args:
            error: Error message
        """
        self.status = "Failed"
        self.error = error
        self.save()

    def mark_error(self, error):
        """Mark tool log as error"""
        self.status = "Failed"  # Since we don't track retries anymore, just mark as failed
        self.error = str(error)
        self.save()

    def on_update(self):
        """Update parent log status if needed"""
        if self.parent_log:
            parent = frappe.get_doc("GP Agent Log", self.parent_log)
            if parent:
                all_tools = frappe.get_all(
                    "GP Agent Tool Log",
                    filters={"parent_log": self.parent_log},
                    fields=["status"]
                )
                
                # If all tool logs are completed/error/failed, update parent log
                if all(t.status in ["Completed", "Error", "Failed"] for t in all_tools):
                    if any(t.status == "Failed" for t in all_tools):
                        parent.status = "Failed"
                    elif any(t.status == "Error" for t in all_tools):
                        parent.status = "Error"
                    else:
                        parent.status = "Completed"
                    parent.save() 

