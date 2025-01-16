"""
Tool for finding similar tasks and analyzing their estimation patterns.
"""

from typing import Dict, Any, List, Optional
import frappe
from datetime import datetime, timedelta

from .base import BaseTaskTool
from ...utils.logging import log_debug
from gp_agent.gameplan_ai_assistant.doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class FindSimilarTasksTool(BaseTaskTool):
    """Tool for finding similar tasks and analyzing their estimation patterns"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="find_similar_tasks",
            description="Find historically similar tasks and analyze their estimation patterns"
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "ID of the task to analyze"
                }
            },
            "required": ["task_id"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - task_id: Task ID
            settings: Optional settings to customize tool behavior
            
        Returns:
            Dict with analysis results including:
            - List of similar tasks
            - Similarity scores
            - Estimation patterns
            - Historical accuracy
        """
        task_id = params["task_id"]
        log_debug(f"Finding similar tasks for task {task_id}")
        
        # Get task details
        task = self.api.get_task_details(task_id)
        if not task:
            return {
                "error": f"Task {task_id} not found"
            }
        
        # Find similar tasks
        similar_tasks = self._find_similar_tasks(task)
        if not similar_tasks:
            return {
                "task_id": task_id,
                "task_title": task["title"],
                "similar_tasks": [],
                "estimation_patterns": None,
                "historical_accuracy": None
            }
        
        # Analyze estimation patterns
        estimation_patterns = self._analyze_estimation_patterns(similar_tasks)
        
        # Calculate historical accuracy
        historical_accuracy = self._calculate_historical_accuracy(similar_tasks)
        
        return {
            "task_id": task_id,
            "task_title": task["title"],
            "similar_tasks": [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "similarity_score": t["similarity_score"],
                    "estimation_history": self._get_task_estimation_summary(t["id"])
                }
                for t in similar_tasks
            ],
            "estimation_patterns": estimation_patterns,
            "historical_accuracy": historical_accuracy
        }

    def _find_similar_tasks(self, task: Dict) -> List[Dict]:
        """Find similar completed tasks"""
        # Get all tasks in the project
        project_tasks = self.api.list_tasks(task["project"])
        
        similar_tasks = []
        task_title = task["title"].lower()
        task_description = task.get("description", "").lower()
        
        for t in project_tasks:
            if t["id"] == task["id"] or not t.get("is_completed"):
                continue
                
            # Calculate similarity scores
            title_similarity = self._calculate_text_similarity(
                task_title,
                t["title"].lower()
            )
            desc_similarity = self._calculate_text_similarity(
                task_description,
                t.get("description", "").lower()
            )
            
            # Calculate tag similarity if available
            tags_similarity = self._calculate_tags_similarity(
                task.get("tags", []),
                t.get("tags", [])
            )
            
            # Calculate overall similarity score
            similarity_score = (
                title_similarity * 0.4 +
                desc_similarity * 0.4 +
                tags_similarity * 0.2
            )
            
            # Consider tasks with sufficient similarity
            if similarity_score > 0.3:
                t["similarity_score"] = round(similarity_score, 2)
                similar_tasks.append(t)
        
        # Sort by similarity score and return top 10
        similar_tasks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_tasks[:10]

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        if not text1 or not text2:
            return 0.0
            
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    def _calculate_tags_similarity(self, tags1: List[str], tags2: List[str]) -> float:
        """Calculate similarity between tag sets"""
        if not tags1 or not tags2:
            return 0.0
        
        tags1_set = set(t.lower() for t in tags1)
        tags2_set = set(t.lower() for t in tags2)
        
        intersection = tags1_set.intersection(tags2_set)
        union = tags1_set.union(tags2_set)
        
        return len(intersection) / len(union)

    def _get_task_estimation_summary(self, task_id: str) -> Dict[str, Any]:
        """Get summary of task's estimation history"""
        history = GPTaskEstimate.get_estimate_history(task_id)
        if not history:
            return {
                "initial_estimate": None,
                "final_estimate": None,
                "total_changes": 0,
                "accuracy": None
            }
        
        initial = history[-1]
        final = history[0]
        
        return {
            "initial_estimate": {
                "hours": initial.estimated_hours,
                "confidence": initial.confidence_level
            },
            "final_estimate": {
                "hours": final.estimated_hours,
                "confidence": final.confidence_level
            },
            "total_changes": len(history) - 1,
            "accuracy": self._calculate_estimate_accuracy(history)
        }

    def _calculate_estimate_accuracy(self, history: List[Dict]) -> Dict[str, Any]:
        """Calculate accuracy of estimates for a completed task"""
        if len(history) < 2:
            return None
        
        initial = history[-1]
        final = history[0]
        
        change_percent = ((final.estimated_hours - initial.estimated_hours) / 
                         initial.estimated_hours * 100) if initial.estimated_hours else 0
        
        if abs(change_percent) <= 10:
            accuracy = "very_high"
        elif abs(change_percent) <= 25:
            accuracy = "high"
        elif abs(change_percent) <= 50:
            accuracy = "moderate"
        else:
            accuracy = "low"
        
        return {
            "level": accuracy,
            "change_percent": round(change_percent, 1)
        }

    def _analyze_estimation_patterns(self, similar_tasks: List[Dict]) -> Dict[str, Any]:
        """Analyze estimation patterns across similar tasks"""
        if not similar_tasks:
            return None
        
        total_changes = 0
        initial_confidence_levels = []
        final_confidence_levels = []
        accuracy_levels = []
        change_percentages = []
        
        for task in similar_tasks:
            history = GPTaskEstimate.get_estimate_history(task["id"])
            if not history or len(history) < 2:
                continue
                
            # Track changes
            total_changes += len(history) - 1
            
            # Track confidence levels
            initial_confidence_levels.append(history[-1].confidence_level)
            final_confidence_levels.append(history[0].confidence_level)
            
            # Calculate change percentage
            initial = history[-1].estimated_hours
            final = history[0].estimated_hours
            change_percent = ((final - initial) / initial * 100) if initial else 0
            change_percentages.append(change_percent)
            
            # Track accuracy
            accuracy = self._calculate_estimate_accuracy(history)
            if accuracy:
                accuracy_levels.append(accuracy["level"])
        
        num_tasks = len(similar_tasks)
        return {
            "average_changes": round(total_changes / num_tasks, 1),
            "common_initial_confidence": self._most_common(initial_confidence_levels),
            "common_final_confidence": self._most_common(final_confidence_levels),
            "average_change_percent": round(sum(change_percentages) / len(change_percentages), 1) if change_percentages else 0,
            "accuracy_distribution": {
                level: round(accuracy_levels.count(level) / len(accuracy_levels) * 100, 1)
                for level in ["very_high", "high", "moderate", "low"]
                if accuracy_levels.count(level) > 0
            } if accuracy_levels else {}
        }

    def _calculate_historical_accuracy(self, similar_tasks: List[Dict]) -> Dict[str, Any]:
        """Calculate overall historical estimation accuracy"""
        if not similar_tasks:
            return None
        
        accuracies = []
        total_changes = 0
        total_tasks = 0
        
        for task in similar_tasks:
            history = GPTaskEstimate.get_estimate_history(task["id"])
            if not history or len(history) < 2:
                continue
                
            accuracy = self._calculate_estimate_accuracy(history)
            if accuracy:
                accuracies.append(accuracy["level"])
                total_changes += len(history) - 1
                total_tasks += 1
        
        if not accuracies:
            return None
        
        return {
            "overall_accuracy": self._most_common(accuracies),
            "average_changes_per_task": round(total_changes / total_tasks, 1),
            "accuracy_distribution": {
                level: round(accuracies.count(level) / len(accuracies) * 100, 1)
                for level in ["very_high", "high", "moderate", "low"]
                if accuracies.count(level) > 0
            }
        }

    def _most_common(self, items: List[Any]) -> Any:
        """Find most common item in a list"""
        if not items:
            return None
            
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
            
        return max(counts.items(), key=lambda x: x[1])[0] 