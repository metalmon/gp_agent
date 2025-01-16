"""
Tool for predicting potential future changes in task estimates.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base import BaseTaskTool
from ...utils.logging import log_debug
from ...doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate


class PredictEstimateChangesTool(BaseTaskTool):
    """Tool for predicting potential future changes in task estimates"""
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="predict_estimate_changes",
            description="Predict potential future changes in task estimates"
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
            Dict with prediction results including:
            - Likelihood of future changes
            - Predicted change patterns
            - Risk factors
            - Confidence level
            - Recommendations
        """
        task_id = params["task_id"]
        log_debug(f"Predicting estimate changes for task {task_id}")
        
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
        
        # Get similar tasks for comparison
        similar_tasks = self._find_similar_tasks(task)
        
        # Analyze historical patterns
        historical_patterns = self._analyze_historical_patterns(history)
        
        # Analyze similar tasks patterns
        similar_patterns = self._analyze_similar_tasks_patterns(similar_tasks)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(task, history, similar_tasks)
        
        # Calculate change likelihood
        change_likelihood = self._calculate_change_likelihood(
            historical_patterns,
            similar_patterns,
            risk_factors
        )
        
        # Generate predictions
        predictions = self._generate_predictions(
            task,
            historical_patterns,
            similar_patterns,
            risk_factors,
            change_likelihood
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            predictions,
            risk_factors,
            change_likelihood
        )
        
        return {
            "task_id": task_id,
            "task_title": task["title"],
            "change_likelihood": change_likelihood,
            "predictions": predictions,
            "risk_factors": risk_factors,
            "recommendations": recommendations
        }

    def _find_similar_tasks(self, task: Dict) -> List[Dict]:
        """Find similar completed tasks for comparison"""
        # Get tasks with similar attributes
        similar_tasks = self.api.get_similar_tasks(task["name"])
        
        # Filter to completed tasks with estimation history
        completed_tasks = []
        for similar_task in similar_tasks:
            history = GPTaskEstimate.get_estimate_history(similar_task["name"])
            if history and similar_task["status"] == "Completed":
                completed_tasks.append({
                    "task": similar_task,
                    "history": history
                })
        
        return completed_tasks

    def _analyze_historical_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in historical estimate changes"""
        if len(history) < 2:
            return {
                "trend": "stable",
                "volatility": "low",
                "change_frequency": 0,
                "average_change": 0,
                "first_estimate": None,
                "last_estimate": None
            }
        
        changes = []
        for i in range(len(history) - 1):
            current = history[i]
            previous = history[i + 1]
            
            change_percent = ((current.estimated_hours - previous.estimated_hours) 
                           / previous.estimated_hours * 100) if previous.estimated_hours else 0
            
            # Convert creation dates to ISO format
            current_date = current.creation.isoformat() if isinstance(current.creation, datetime) else current.creation
            previous_date = previous.creation.isoformat() if isinstance(previous.creation, datetime) else previous.creation
            
            changes.append({
                "percent": change_percent,
                "from_date": previous_date,
                "to_date": current_date
            })
        
        # Calculate metrics
        avg_change = sum(abs(c["percent"]) for c in changes) / len(changes)
        increases = sum(1 for c in changes if c["percent"] > 0)
        decreases = sum(1 for c in changes if c["percent"] < 0)
        
        # Determine trend
        if increases > decreases * 2:
            trend = "increasing"
        elif decreases > increases * 2:
            trend = "decreasing"
        else:
            trend = "fluctuating"
        
        # Calculate change frequency (changes per week)
        first_date = history[-1].creation
        last_date = history[0].creation
        if isinstance(first_date, datetime):
            first_date = first_date.isoformat()
        if isinstance(last_date, datetime):
            last_date = last_date.isoformat()
            
        days_span = (datetime.fromisoformat(last_date) - datetime.fromisoformat(first_date)).days
        changes_per_week = len(changes) / (days_span / 7) if days_span > 0 else 0
        
        # Determine volatility
        if avg_change > 50:
            volatility = "high"
        elif avg_change > 25:
            volatility = "medium"
        else:
            volatility = "low"
        
        return {
            "trend": trend,
            "volatility": volatility,
            "change_frequency": round(changes_per_week, 2),
            "average_change": round(avg_change, 1),
            "first_estimate": first_date,
            "last_estimate": last_date,
            "changes": changes
        }

    def _analyze_similar_tasks_patterns(self, similar_tasks: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns from similar completed tasks"""
        if not similar_tasks:
            return {
                "average_changes": 0,
                "common_patterns": []
            }
        
        total_changes = 0
        patterns = []
        
        for task_data in similar_tasks:
            history = task_data["history"]
            if len(history) > 1:
                # Count changes
                total_changes += len(history) - 1
                
                # Analyze final vs initial
                initial = history[-1].estimated_hours
                final = history[0].estimated_hours
                change_percent = ((final - initial) / initial * 100) if initial else 0
                
                if change_percent > 50:
                    patterns.append("major_increase")
                elif change_percent < -50:
                    patterns.append("major_decrease")
                elif abs(change_percent) > 25:
                    patterns.append("significant_change")
        
        # Get most common patterns
        pattern_counts = {}
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        common_patterns = sorted(
            pattern_counts.keys(),
            key=lambda x: pattern_counts[x],
            reverse=True
        )[:3]
        
        return {
            "average_changes": round(total_changes / len(similar_tasks), 1),
            "common_patterns": common_patterns
        }

    def _identify_risk_factors(
        self,
        task: Dict,
        history: List[Dict],
        similar_tasks: List[Dict]
    ) -> Dict[str, List[str]]:
        """Identify factors that may increase risk of estimate changes"""
        high_risk = []
        medium_risk = []
        low_risk = []
        
        # Historical factors
        if history and len(history) > 1:
            confidence_trend = self._analyze_confidence_trend(history)
            if confidence_trend == "decreasing":
                high_risk.append("decreasing_confidence")
            elif confidence_trend == "fluctuating":
                medium_risk.append("unstable_confidence")
        
        # Similar tasks factors
        if similar_tasks:
            volatile_count = 0
            for task_data in similar_tasks:
                if len(task_data["history"]) > 3:  # Consider tasks with multiple changes
                    volatile_count += 1
            
            if volatile_count > len(similar_tasks) * 0.5:
                high_risk.append("similar_tasks_volatile")
            elif volatile_count > len(similar_tasks) * 0.25:
                medium_risk.append("some_similar_tasks_volatile")
        else:
            medium_risk.append("no_similar_tasks")
        
        # Task specific factors
        if task.get("dependencies"):
            medium_risk.append("has_dependencies")
        
        if not task.get("description"):
            low_risk.append("missing_description")
        
        return {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk
        }

    def _analyze_confidence_trend(self, history: List[Dict]) -> str:
        """Analyze trend in confidence levels"""
        confidence_map = {"Low": 1, "Medium": 2, "High": 3}
        confidence_scores = [
            confidence_map.get(est.confidence_level, 0)
            for est in history
        ]
        
        if len(confidence_scores) < 2:
            return "stable"
        
        # Check if consistently decreasing
        is_decreasing = all(
            confidence_scores[i] <= confidence_scores[i+1]
            for i in range(len(confidence_scores)-1)
        )
        
        if is_decreasing and confidence_scores[0] < confidence_scores[-1]:
            return "decreasing"
        
        # Check for fluctuations
        changes = sum(
            1 for i in range(1, len(confidence_scores))
            if confidence_scores[i] != confidence_scores[i-1]
        )
        
        if changes > len(confidence_scores) * 0.5:
            return "fluctuating"
            
        return "stable"

    def _calculate_change_likelihood(
        self,
        historical_patterns: Dict[str, Any],
        similar_patterns: Dict[str, Any],
        risk_factors: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Calculate likelihood of future estimate changes"""
        base_score = 0.0
        
        # Factor in historical patterns
        if historical_patterns["volatility"] == "high":
            base_score += 0.4
        elif historical_patterns["volatility"] == "medium":
            base_score += 0.2
        
        if historical_patterns["change_frequency"] > 1:
            base_score += 0.2
        elif historical_patterns["change_frequency"] > 0.5:
            base_score += 0.1
        
        # Factor in similar tasks patterns
        if similar_patterns["average_changes"] > 3:
            base_score += 0.2
        elif similar_patterns["average_changes"] > 1:
            base_score += 0.1
        
        if "major_increase" in similar_patterns["common_patterns"]:
            base_score += 0.1
        
        # Factor in risk factors
        base_score += len(risk_factors["high"]) * 0.1
        base_score += len(risk_factors["medium"]) * 0.05
        base_score += len(risk_factors["low"]) * 0.02
        
        # Cap the score at 1.0
        likelihood_score = min(base_score, 1.0)
        
        # Determine likelihood level
        if likelihood_score > 0.7:
            likelihood = "high"
        elif likelihood_score > 0.4:
            likelihood = "medium"
        else:
            likelihood = "low"
        
        return {
            "score": round(likelihood_score, 2),
            "level": likelihood,
            "confidence": "high" if similar_patterns["average_changes"] > 0 else "medium"
        }

    def _generate_predictions(
        self,
        task: Dict,
        historical_patterns: Dict[str, Any],
        similar_patterns: Dict[str, Any],
        risk_factors: Dict[str, List[str]],
        change_likelihood: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate specific predictions about potential changes"""
        predictions = {
            "expected_changes": [],
            "timeline": "unknown",
            "magnitude": "unknown"
        }
        
        # Predict types of changes
        if historical_patterns["trend"] == "increasing":
            predictions["expected_changes"].append({
                "type": "increase",
                "reason": "Historical trend shows consistent increases"
            })
        elif historical_patterns["trend"] == "decreasing":
            predictions["expected_changes"].append({
                "type": "decrease",
                "reason": "Historical trend shows consistent decreases"
            })
        
        if "similar_tasks_volatile" in risk_factors["high"]:
            predictions["expected_changes"].append({
                "type": "volatile",
                "reason": "Similar tasks showed significant volatility"
            })
        
        if "decreasing_confidence" in risk_factors["high"]:
            predictions["expected_changes"].append({
                "type": "increase",
                "reason": "Decreasing confidence often leads to estimate increases"
            })
        
        # Predict timeline
        if historical_patterns["change_frequency"] > 1:
            predictions["timeline"] = "within_week"
        elif historical_patterns["change_frequency"] > 0.5:
            predictions["timeline"] = "within_two_weeks"
        elif historical_patterns["change_frequency"] > 0:
            predictions["timeline"] = "within_month"
        
        # Predict magnitude
        avg_historical_change = historical_patterns["average_change"]
        if avg_historical_change > 50:
            predictions["magnitude"] = "major"
        elif avg_historical_change > 25:
            predictions["magnitude"] = "significant"
        elif avg_historical_change > 10:
            predictions["magnitude"] = "moderate"
        else:
            predictions["magnitude"] = "minor"
        
        return predictions

    def _generate_recommendations(
        self,
        predictions: Dict[str, Any],
        risk_factors: Dict[str, List[str]],
        change_likelihood: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on predictions and risk factors"""
        recommendations = []
        
        # Risk-based recommendations
        if "decreasing_confidence" in risk_factors["high"]:
            recommendations.extend([
                "Review factors affecting estimation confidence",
                "Consider breaking task into smaller, more predictable pieces"
            ])
        
        if "similar_tasks_volatile" in risk_factors["high"]:
            recommendations.extend([
                "Analyze similar completed tasks to understand volatility factors",
                "Plan for potential estimate adjustments"
            ])
        
        if "has_dependencies" in risk_factors["medium"]:
            recommendations.append(
                "Review dependencies and their potential impact on estimates"
            )
        
        # Likelihood based recommendations
        if change_likelihood["level"] == "high":
            recommendations.extend([
                "Implement more frequent estimation reviews",
                "Consider adding buffer to the estimate"
            ])
        
        # Prediction based recommendations
        if predictions["magnitude"] in ["major", "significant"]:
            recommendations.append(
                "Plan for buffer in project timeline to accommodate potential changes"
            )
        
        if predictions["timeline"] == "within_week":
            recommendations.append(
                "Schedule immediate estimation review to address potential changes proactively"
            )
        
        return list(set(recommendations))  # Remove duplicates 