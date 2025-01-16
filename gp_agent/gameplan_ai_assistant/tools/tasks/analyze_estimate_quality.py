"""
Tool for analyzing task estimate quality.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class AnalyzeEstimateQualityTool(BaseTaskTool):
    """Tool for analyzing quality of estimates for a specific task"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="analyze_estimate_quality",
            description="Analyze quality of estimates for a specific task"
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
                    "description": "ID of the task to analyze estimates for"
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
            - Overall estimate quality score
            - History of estimate changes
            - Confidence level analysis
            - Time accuracy analysis
            - Patterns identified
            - Recommendations for improvement
        """
        task_id = params["task_id"]
        log_debug(f"Analyzing estimate quality for task {task_id}")
        
        # Get task details
        task = self.api.get_task_details(task_id)
        if not task:
            return {
                "error": f"Task {task_id} not found"
            }
        
        # Get estimate history
        history = GPTaskEstimate.get_estimate_history(task_id)
        if not history:
            return {
                "error": "No estimation history found",
                "task_title": task["title"],
                "task_id": task_id
            }
        
        log_debug(f"Found {len(history)} estimates for task")
        
        # Analyze estimate changes
        changes_analysis = self._analyze_estimate_changes(history)
        
        # Analyze confidence levels
        confidence_analysis = self._analyze_confidence_levels(history)
        
        # Analyze time accuracy
        time_analysis = self._analyze_time_accuracy(task, history)
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(changes_analysis, confidence_analysis, time_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            changes_analysis,
            confidence_analysis,
            time_analysis,
            quality_score
        )
        
        return {
            "task_id": task_id,
            "task_title": task["title"],
            "quality_score": quality_score,
            "estimate_changes": changes_analysis,
            "confidence_analysis": confidence_analysis,
            "time_accuracy": time_analysis,
            "recommendations": recommendations
        }

    def _analyze_estimate_changes(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze how estimates have changed over time"""
        if len(history) < 2:
            return {
                "stability": "stable",
                "total_changes": 0,
                "average_change_percent": 0,
                "largest_change": {
                    "from": 0,
                    "to": 0,
                    "percent": 0
                }
            }
        
        changes = []
        largest_change = {
            "from": 0,
            "to": 0,
            "percent": 0
        }
        
        # Analyze each change
        for i in range(len(history) - 1):
            current = history[i]
            previous = history[i + 1]
            
            change_percent = ((current.estimated_hours - previous.estimated_hours) 
                             / previous.estimated_hours * 100) if previous.estimated_hours else 0
            
            changes.append({
                "from": previous.estimated_hours,
                "to": current.estimated_hours,
                "percent": change_percent,
                "date": current.creation.isoformat() if isinstance(current.creation, datetime) else current.creation
            })
            
            # Track largest change
            if abs(change_percent) > abs(largest_change["percent"]):
                largest_change = {
                    "from": previous.estimated_hours,
                    "to": current.estimated_hours,
                    "percent": change_percent
                }
        
        # Calculate average change
        average_change = sum(abs(c["percent"]) for c in changes) / len(changes)
        
        # Determine stability
        if average_change > 50:
            stability = "highly unstable"
        elif average_change > 25:
            stability = "unstable"
        elif average_change > 10:
            stability = "moderately stable"
        else:
            stability = "stable"
            
        return {
            "stability": stability,
            "total_changes": len(changes),
            "average_change_percent": average_change,
            "largest_change": largest_change,
            "change_history": changes
        }

    def _analyze_confidence_levels(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze confidence levels and their changes"""
        if not history:
            return {
                "trend": "no data",
                "consistency": "no data"
            }
        
        confidence_map = {
            "Low": 1,
            "Medium": 2,
            "High": 3
        }
        
        confidence_scores = [confidence_map.get(h.confidence_level, 0) for h in history]
        
        # Analyze trend
        if len(confidence_scores) > 1:
            if confidence_scores[0] < confidence_scores[-1]:
                trend = "increasing"
            elif confidence_scores[0] > confidence_scores[-1]:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "single estimate"
        
        # Analyze consistency
        if len(confidence_scores) > 1:
            changes = sum(1 for i in range(len(confidence_scores)-1) 
                         if confidence_scores[i] != confidence_scores[i+1])
            if changes == 0:
                consistency = "very consistent"
            elif changes <= len(confidence_scores) * 0.25:
                consistency = "mostly consistent"
            elif changes <= len(confidence_scores) * 0.5:
                consistency = "somewhat inconsistent"
            else:
                consistency = "very inconsistent"
        else:
            consistency = "single estimate"
        
        return {
            "trend": trend,
            "consistency": consistency,
            "current_level": history[0].confidence_level,
            "initial_level": history[-1].confidence_level
        }

    def _analyze_time_accuracy(self, task: Dict, history: List[Dict]) -> Dict[str, Any]:
        """Analyze accuracy of time estimates compared to actual time spent"""
        if not history:
            return {
                "accuracy": "no data",
                "deviation_percent": 0
            }
        
        initial_estimate = history[-1].estimated_hours
        current_estimate = history[0].estimated_hours
        
        # For completed tasks, compare with actual time
        if task["is_completed"]:
            # TODO: Get actual time spent from time logs
            actual_hours = 0  # This should be fetched from time tracking
            
            deviation_percent = ((actual_hours - initial_estimate) 
                               / initial_estimate * 100) if initial_estimate else 0
            
            if abs(deviation_percent) <= 10:
                accuracy = "very accurate"
            elif abs(deviation_percent) <= 25:
                accuracy = "moderately accurate"
            elif abs(deviation_percent) <= 50:
                accuracy = "somewhat inaccurate"
            else:
                accuracy = "very inaccurate"
        else:
            # For ongoing tasks, compare initial vs current estimate
            deviation_percent = ((current_estimate - initial_estimate) 
                               / initial_estimate * 100) if initial_estimate else 0
            
            if abs(deviation_percent) <= 10:
                accuracy = "stable"
            elif abs(deviation_percent) <= 25:
                accuracy = "slightly adjusted"
            elif abs(deviation_percent) <= 50:
                accuracy = "significantly adjusted"
            else:
                accuracy = "majorly adjusted"
            
        return {
            "accuracy": accuracy,
            "deviation_percent": round(deviation_percent, 1),
            "initial_estimate": initial_estimate,
            "current_estimate": current_estimate
        }

    def _calculate_quality_score(
        self,
        changes_analysis: Dict,
        confidence_analysis: Dict,
        time_analysis: Dict
    ) -> float:
        """Calculate overall quality score from 0 to 100"""
        score = 100.0
        
        # Deduct points for estimate instability
        if changes_analysis["stability"] == "highly unstable":
            score -= 30
        elif changes_analysis["stability"] == "unstable":
            score -= 20
        elif changes_analysis["stability"] == "moderately stable":
            score -= 10
        
        # Deduct points for confidence inconsistency
        if confidence_analysis["consistency"] == "very inconsistent":
            score -= 20
        elif confidence_analysis["consistency"] == "somewhat inconsistent":
            score -= 10
        
        # Deduct points for time inaccuracy
        if time_analysis["accuracy"] in ["very inaccurate", "majorly adjusted"]:
            score -= 30
        elif time_analysis["accuracy"] in ["somewhat inaccurate", "significantly adjusted"]:
            score -= 20
        elif time_analysis["accuracy"] in ["moderately accurate", "slightly adjusted"]:
            score -= 10
        
        return max(0, score)

    def _generate_recommendations(
        self,
        changes_analysis: Dict,
        confidence_analysis: Dict,
        time_analysis: Dict,
        quality_score: float
    ) -> List[str]:
        """Generate recommendations for improving estimation quality"""
        recommendations = []
        
        # Recommendations based on stability
        if changes_analysis["stability"] in ["highly unstable", "unstable"]:
            recommendations.extend([
                "Break down the task into smaller, more manageable pieces",
                "Document assumptions and risks that could impact the estimate",
                "Review similar completed tasks for better initial estimates"
            ])
        
        # Recommendations based on confidence
        if confidence_analysis["consistency"] in ["very inconsistent", "somewhat inconsistent"]:
            recommendations.extend([
                "Maintain consistent criteria for confidence levels",
                "Document reasons for confidence level changes",
                "Consider team input when assessing confidence"
            ])
        
        # Recommendations based on time accuracy
        if time_analysis["accuracy"] in ["very inaccurate", "somewhat inaccurate", 
                                       "majorly adjusted", "significantly adjusted"]:
            recommendations.extend([
                "Track actual time spent more accurately",
                "Review initial assumptions that led to inaccurate estimates",
                "Consider using historical data from similar tasks"
            ])
        
        # General recommendations for low quality scores
        if quality_score < 60:
            recommendations.extend([
                "Implement regular estimate reviews",
                "Improve task documentation and requirements",
                "Consider team training on estimation techniques"
            ])
        
        return list(set(recommendations))  # Remove duplicates 