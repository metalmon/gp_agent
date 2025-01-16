import frappe
from frappe.model.document import Document

class GPTaskEstimate(Document):
    def before_insert(self):
        if not self.creation_timestamp:
            self.creation_timestamp = frappe.utils.now_datetime()
        
        if not self.created_by:
            self.created_by = frappe.session.user

        if not self.remaining_hours:
            self.remaining_hours = self.estimated_hours

    def validate(self):
        if self.remaining_hours > self.estimated_hours:
            frappe.throw("Remaining hours cannot be greater than estimated hours")
        
        if self.remaining_hours < 0:
            frappe.throw("Remaining hours cannot be negative")
        
        if self.estimated_hours <= 0:
            frappe.throw("Estimated hours must be greater than zero")

    @staticmethod
    def get_latest_estimate(task_id: str) -> "GPTaskEstimate":
        """Get the latest estimate for a task"""
        estimates = frappe.get_all(
            "GP Task Estimate",
            filters={"task": task_id},
            fields=["*"],
            order_by="creation_timestamp desc",
            limit=1
        )
        return estimates[0] if estimates else None

    @staticmethod
    def get_estimate_history(task_id: str) -> list:
        """Get all estimates for a task in chronological order"""
        return frappe.get_all(
            "GP Task Estimate",
            filters={"task": task_id},
            fields=["*"],
            order_by="creation_timestamp asc"
        ) 