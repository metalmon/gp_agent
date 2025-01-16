import frappe
from frappe.model.document import Document
from typing import List, Dict, Any

class GPTaskDependency(Document):
    def before_insert(self):
        if not self.creation_timestamp:
            self.creation_timestamp = frappe.utils.now_datetime()
        
        if not self.created_by:
            self.created_by = frappe.session.user

    def validate(self):
        # Check for circular dependencies
        if self.creates_circular_dependency():
            frappe.throw("This dependency would create a circular reference")
        
        # Check if reverse dependency already exists
        if self.has_reverse_dependency():
            frappe.throw("Reverse dependency already exists")

    def creates_circular_dependency(self) -> bool:
        """Check if adding this dependency would create a circular reference"""
        if self.dependency_type == "Blocks":
            blocked_task = self.depends_on
            blocking_task = self.task
        else:
            blocked_task = self.task
            blocking_task = self.depends_on

        # Get all tasks that are blocked by the blocked task
        return self._is_circular(blocked_task, blocking_task, set())

    def _is_circular(self, current_task: str, target_task: str, visited: set) -> bool:
        """Recursive helper for circular dependency check"""
        if current_task == target_task:
            return True
        
        if current_task in visited:
            return False
        
        visited.add(current_task)
        
        # Get all tasks that this task blocks
        blocking = frappe.get_all(
            "GP Task Dependency",
            filters={
                "task": current_task,
                "dependency_type": "Blocks"
            },
            fields=["depends_on"]
        )
        
        # Get all tasks that block this task
        blocked_by = frappe.get_all(
            "GP Task Dependency",
            filters={
                "depends_on": current_task,
                "dependency_type": "Is Blocked By"
            },
            fields=["task"]
        )
        
        # Check each dependent task
        for dep in blocking:
            if self._is_circular(dep.depends_on, target_task, visited):
                return True
        
        for dep in blocked_by:
            if self._is_circular(dep.task, target_task, visited):
                return True
        
        return False

    def has_reverse_dependency(self) -> bool:
        """Check if reverse dependency already exists"""
        return frappe.db.exists(
            "GP Task Dependency",
            {
                "task": self.depends_on,
                "depends_on": self.task,
                "dependency_type": "Blocks" if self.dependency_type == "Is Blocked By" else "Is Blocked By"
            }
        )

    @staticmethod
    def get_dependencies(task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all dependencies for a task"""
        # Get tasks that this task blocks
        blocking = frappe.get_all(
            "GP Task Dependency",
            filters={
                "task": task_id,
                "dependency_type": "Blocks"
            },
            fields=["depends_on as task", "creation_timestamp", "created_by"]
        )
        
        # Get tasks that block this task
        blocked_by = frappe.get_all(
            "GP Task Dependency",
            filters={
                "depends_on": task_id,
                "dependency_type": "Is Blocked By"
            },
            fields=["task", "creation_timestamp", "created_by"]
        )
        
        # Fetch task details for each dependency
        for deps in [blocking, blocked_by]:
            for dep in deps:
                task_details = frappe.get_all(
                    "GP Task",
                    filters={"name": dep.task},
                    fields=["title", "status", "priority", "due_date"]
                )
                if task_details:
                    dep.update(task_details[0])
        
        return {
            "blocking": blocking,
            "blocked_by": blocked_by
        }

    @staticmethod
    def get_dependency_chain(task_id: str, direction: str = "both") -> List[List[str]]:
        """Get the full chain of dependencies
        
        Args:
            task_id: The task to get dependencies for
            direction: 'up' for blocked_by chain, 'down' for blocking chain, 'both' for full chain
        """
        def get_up_chain(task: str, visited: set) -> List[str]:
            """Get chain of tasks that must be completed before this task"""
            if task in visited:
                return []
            visited.add(task)
            
            blocked_by = frappe.get_all(
                "GP Task Dependency",
                filters={
                    "depends_on": task,
                    "dependency_type": "Is Blocked By"
                },
                fields=["task"]
            )
            
            result = []
            for dep in blocked_by:
                chain = get_up_chain(dep.task, visited)
                if chain:
                    result.extend(chain)
            
            return result + [task] if not blocked_by else result
        
        def get_down_chain(task: str, visited: set) -> List[str]:
            """Get chain of tasks that can be started after this task"""
            if task in visited:
                return []
            visited.add(task)
            
            blocking = frappe.get_all(
                "GP Task Dependency",
                filters={
                    "task": task,
                    "dependency_type": "Blocks"
                },
                fields=["depends_on"]
            )
            
            result = [task]
            for dep in blocking:
                chain = get_down_chain(dep.depends_on, visited)
                if chain:
                    result.extend(chain)
            
            return result
        
        visited = set()
        chain = []
        
        if direction in ["up", "both"]:
            up_chain = get_up_chain(task_id, visited)
            if up_chain:
                chain.append(up_chain)
        
        if direction in ["down", "both"]:
            visited = set()  # Reset visited for down chain
            down_chain = get_down_chain(task_id, visited)
            if down_chain:
                chain.append(down_chain)
        
        return chain 