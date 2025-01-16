"""
Tool for analyzing reasons for estimate changes in a task.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class AnalyzeEstimateChangesTool(BaseTaskTool):
    """Tool for analyzing reasons for estimate changes in a task"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="analyze_estimate_changes",
            description="Analyze reasons for estimate changes in a task"
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
                    "description": "ID of the task to analyze estimate changes for"
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
            - Timeline of changes
            - Identified patterns
            - Common reasons for changes
            - Impact analysis
            - Recommendations
        """
        task_id = params["task_id"]
        log_debug(f"Analyzing estimate changes for task {task_id}")
        
        # Get task details and history
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
                "task_title": task["title"]
            }
            
        # Get task comments and activity
        comments = self.api.get_task_comments(task_id)
        
        # Analyze changes timeline
        timeline = self._analyze_changes_timeline(history)
        
        # Analyze patterns in changes
        patterns = self._analyze_change_patterns(history)
        
        # Analyze reasons from comments and notes
        reasons = self._analyze_change_reasons(history, comments)
        
        # Analyze impact of changes
        impact = self._analyze_change_impact(task, history)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, reasons, impact)
        
        return {
            "task_id": task_id,
            "task_title": task["title"],
            "timeline": timeline,
            "patterns": patterns,
            "reasons": reasons,
            "impact": impact,
            "recommendations": recommendations
        }

    def _analyze_changes_timeline(self, history: List[Dict]) -> List[Dict]:
        """Analyze the timeline of estimate changes"""
        timeline = []
        
        for i in range(len(history) - 1):
            current = history[i]
            previous = history[i + 1]
            
            # Convert datetime to ISO format string
            creation_date = current.creation.isoformat() if isinstance(current.creation, datetime) else current.creation
            
            change = {
                "date": creation_date,
                "user": current.owner,
                "from_hours": previous.estimated_hours,
                "to_hours": current.estimated_hours,
                "change_hours": current.estimated_hours - previous.estimated_hours,
                "change_percent": ((current.estimated_hours - previous.estimated_hours) / 
                                 previous.estimated_hours * 100) if previous.estimated_hours else 0,
                "confidence_change": current.confidence_level != previous.confidence_level,
                "note": current.note
            }
            timeline.append(change)
        
        return timeline

    def _analyze_change_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in estimate changes"""
        if len(history) < 2:
            return {
                "trend": "insufficient data",
                "frequency": "single estimate",
                "common_adjustments": []
            }
        
        # Analyze trend
        changes = []
        for i in range(len(history) - 1):
            change = history[i].estimated_hours - history[i + 1].estimated_hours
            changes.append(change)
        
        increases = sum(1 for c in changes if c > 0)
        decreases = sum(1 for c in changes if c < 0)
        
        if increases > decreases * 2:
            trend = "consistently increasing"
        elif decreases > increases * 2:
            trend = "consistently decreasing"
        elif increases > decreases:
            trend = "slightly increasing"
        elif decreases > increases:
            trend = "slightly decreasing"
        else:
            trend = "fluctuating"
        
        # Analyze frequency
        total_days = (history[0].creation - history[-1].creation).days
        changes_per_week = len(changes) / (total_days / 7) if total_days > 0 else 0
        
        if changes_per_week > 2:
            frequency = "very frequent"
        elif changes_per_week > 1:
            frequency = "frequent"
        elif changes_per_week > 0.5:
            frequency = "moderate"
        else:
            frequency = "infrequent"
        
        # Find common adjustment sizes
        common_adjustments = []
        abs_changes = [abs(c) for c in changes]
        if abs_changes:
            avg_change = sum(abs_changes) / len(abs_changes)
            common_adjustments = [
                c for c in abs_changes 
                if abs(c - avg_change) <= avg_change * 0.25
            ]
        
        return {
            "trend": trend,
            "frequency": frequency,
            "changes_per_week": round(changes_per_week, 1),
            "common_adjustments": common_adjustments
        }

    def _analyze_change_reasons(self, history: List[Dict], comments: List[Dict]) -> Dict[str, Any]:
        """Analyze reasons for estimate changes from notes and comments"""
        reasons = {
            "scope_change": 0,
            "complexity_discovered": 0,
            "resource_constraints": 0,
            "dependencies": 0,
            "other": 0
        }
        
        # Analyze estimate notes
        for est in history:
            note = est.note.lower() if est.note else ""
            
            if any(term in note for term in ["scope", "requirement", "feature"]):
                reasons["scope_change"] += 1
            elif any(term in note for term in ["complex", "difficult", "challenge"]):
                reasons["complexity_discovered"] += 1
            elif any(term in note for term in ["resource", "capacity", "availability"]):
                reasons["resource_constraints"] += 1
            elif any(term in note for term in ["depend", "block", "wait"]):
                reasons["dependencies"] += 1
            elif note:
                reasons["other"] += 1
        
        # Analyze comments around estimate changes
        for i, est in enumerate(history[:-1]):
            change_date = est.creation
            relevant_comments = [
                c for c in comments
                if abs((c["creation"] - change_date).days) <= 2
            ]
            
            for comment in relevant_comments:
                text = comment["content"].lower()
                if any(term in text for term in ["scope", "requirement", "feature"]):
                    reasons["scope_change"] += 1
                elif any(term in text for term in ["complex", "difficult", "challenge"]):
                    reasons["complexity_discovered"] += 1
                elif any(term in text for term in ["resource", "capacity", "availability"]):
                    reasons["resource_constraints"] += 1
                elif any(term in text for term in ["depend", "block", "wait"]):
                    reasons["dependencies"] += 1
        
        # Calculate percentages
        total = sum(reasons.values())
        if total > 0:
            reasons_percent = {
                k: round(v / total * 100, 1)
                for k, v in reasons.items()
            }
        else:
            reasons_percent = {k: 0 for k in reasons}
        
        return {
            "counts": reasons,
            "percentages": reasons_percent,
            "primary_reason": max(reasons.items(), key=lambda x: x[1])[0] if total > 0 else None
        }

    def _analyze_change_impact(self, task: Dict, history: List[Dict]) -> Dict[str, Any]:
        """Analyze impact of estimate changes"""
        if len(history) < 2:
            return {
                "schedule_impact": "no impact",
                "confidence_impact": "no impact",
                "total_adjustment": 0
            }
        
        initial = history[-1]
        current = history[0]
        
        # Calculate schedule impact
        total_adjustment = current.estimated_hours - initial.estimated_hours
        percent_change = (total_adjustment / initial.estimated_hours * 100) if initial.estimated_hours else 0
        
        if abs(percent_change) <= 10:
            schedule_impact = "minimal"
        elif abs(percent_change) <= 25:
            schedule_impact = "moderate"
        elif abs(percent_change) <= 50:
            schedule_impact = "significant"
        else:
            schedule_impact = "major"
        
        # Analyze confidence trend
        confidence_map = {"Low": 1, "Medium": 2, "High": 3}
        confidence_trend = []
        
        for est in history:
            confidence_trend.append(confidence_map.get(est.confidence_level, 0))
        
        if len(confidence_trend) > 1:
            if confidence_trend[0] > confidence_trend[-1]:
                confidence_impact = "increasing"
            elif confidence_trend[0] < confidence_trend[-1]:
                confidence_impact = "decreasing"
            else:
                confidence_impact = "stable"
        else:
            confidence_impact = "unchanged"
        
        return {
            "schedule_impact": schedule_impact,
            "confidence_impact": confidence_impact,
            "total_adjustment": round(total_adjustment, 1),
            "percent_change": round(percent_change, 1)
        }

    def _generate_recommendations(
        self,
        patterns: Dict[str, Any],
        reasons: Dict[str, Any],
        impact: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Recommendations based on patterns
        if patterns["frequency"] in ["very frequent", "frequent"]:
            recommendations.extend([
                "Consider implementing a more structured estimation process",
                "Review estimation changes more thoroughly before updating"
            ])
        
        if patterns["trend"] in ["consistently increasing", "consistently decreasing"]:
            recommendations.extend([
                "Analyze systematic biases in initial estimates",
                "Consider historical data when making initial estimates"
            ])
        
        # Recommendations based on reasons
        primary_reason = reasons["primary_reason"]
        if primary_reason == "scope_change":
            recommendations.extend([
                "Improve initial requirements gathering",
                "Implement better scope control measures"
            ])
        elif primary_reason == "complexity_discovered":
            recommendations.extend([
                "Consider spike/research tasks for complex features",
                "Break down complex tasks into smaller, more predictable pieces"
            ])
        elif primary_reason == "resource_constraints":
            recommendations.extend([
                "Review resource allocation process",
                "Consider team capacity in initial estimates"
            ])
        elif primary_reason == "dependencies":
            recommendations.extend([
                "Identify dependencies earlier in planning",
                "Consider dependency risks in initial estimates"
            ])
        
        # Recommendations based on impact
        if impact["schedule_impact"] in ["significant", "major"]:
            recommendations.extend([
                "Review and update project timeline",
                "Consider breaking task into smaller deliverables"
            ])
        
        if impact["confidence_impact"] == "decreasing":
            recommendations.extend([
                "Review factors affecting estimation confidence",
                "Consider additional planning or analysis phase"
            ])
        
        return list(set(recommendations))  # Remove duplicates 