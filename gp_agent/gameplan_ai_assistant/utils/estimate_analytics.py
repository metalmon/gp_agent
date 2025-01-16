import frappe
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..doctype.gp_task_estimate.gp_task_estimate import GPTaskEstimate

def analyze_estimate_trends(project_id: str) -> Dict[str, Any]:
    """Analyze estimation trends across the project
    
    Args:
        project_id: ID of the project to analyze
    
    Returns:
        Dict with trend analysis including:
        - Overall trend (increasing/decreasing/stable)
        - Per-user accuracy metrics
        - Common patterns in estimate changes
        - Recommendations for improvement
    """
    # Get all project tasks
    tasks = frappe.get_all(
        "GP Task",
        filters={"project": project_id},
        fields=["name", "title", "status", "assigned_to"]
    )
    
    # Collect all estimates
    all_estimates = []
    user_estimates = {}
    
    for task in tasks:
        history = GPTaskEstimate.get_estimate_history(task.name)
        if history:
            all_estimates.extend([{
                "task": task,
                "estimate": est
            } for est in history])
            
            # Group by user
            for est in history:
                if est.created_by not in user_estimates:
                    user_estimates[est.created_by] = []
                user_estimates[est.created_by].append({
                    "task": task,
                    "estimate": est
                })
    
    return {
        "overall_trends": _analyze_overall_trends(all_estimates),
        "user_metrics": _analyze_user_metrics(user_estimates),
        "patterns": _find_estimate_patterns(all_estimates),
        "recommendations": _generate_recommendations(all_estimates, user_estimates)
    }

def analyze_estimate_quality(task_id: str) -> Dict[str, Any]:
    """Analyze quality of estimates for a specific task
    
    Args:
        task_id: ID of the task to analyze
    
    Returns:
        Dict with quality metrics including:
        - Estimate stability
        - Confidence accuracy
        - Progress consistency
        - Risk indicators
    """
    task = frappe.get_doc("GP Task", task_id)
    history = GPTaskEstimate.get_estimate_history(task_id)
    
    if not history:
        return {
            "task_id": task_id,
            "has_estimates": False
        }
    
    return {
        "task_id": task_id,
        "has_estimates": True,
        "stability_metrics": _calculate_stability_metrics(history),
        "confidence_accuracy": _analyze_confidence_accuracy(history),
        "progress_consistency": _analyze_progress_consistency(history),
        "risk_indicators": _identify_estimate_risks(history)
    }

def get_team_estimation_metrics(team_id: str) -> Dict[str, Any]:
    """Get estimation metrics for team members
    
    Args:
        team_id: ID of the team to analyze
    
    Returns:
        Dict with team metrics including:
        - Per-user estimation accuracy
        - Team trends
        - Areas for improvement
    """
    # Get team members
    team_members = frappe.get_all(
        "User",
        filters={"team": team_id},
        fields=["name", "full_name"]
    )
    
    metrics = {}
    for member in team_members:
        user_id = member.name
        
        # Get all estimates by this user
        estimates = frappe.get_all(
            "GP Task Estimate",
            filters={"created_by": user_id},
            fields=["*"]
        )
        
        if estimates:
            metrics[user_id] = {
                "user": member,
                "accuracy": _calculate_user_accuracy(estimates),
                "confidence_correlation": _analyze_confidence_correlation(estimates),
                "estimation_patterns": _identify_user_patterns(estimates)
            }
    
    return {
        "user_metrics": metrics,
        "team_summary": _summarize_team_metrics(metrics),
        "recommendations": _generate_team_recommendations(metrics)
    }

def _analyze_overall_trends(estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze overall estimation trends"""
    if not estimates:
        return {"trend": "No estimates available"}
    
    # Sort by timestamp
    sorted_estimates = sorted(estimates, key=lambda x: x["estimate"].creation_timestamp)
    
    # Calculate trend metrics
    changes = []
    for i in range(1, len(sorted_estimates)):
        prev = sorted_estimates[i-1]["estimate"].estimated_hours
        curr = sorted_estimates[i]["estimate"].estimated_hours
        changes.append((curr - prev) / prev if prev else 0)
    
    avg_change = sum(changes) / len(changes) if changes else 0
    
    return {
        "trend": "increasing" if avg_change > 0.1 else "decreasing" if avg_change < -0.1 else "stable",
        "average_change_percentage": avg_change * 100,
        "volatility": sum(abs(c) for c in changes) / len(changes) if changes else 0
    }

def _analyze_user_metrics(user_estimates: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Analyze estimation metrics per user"""
    metrics = {}
    
    for user_id, estimates in user_estimates.items():
        initial_vs_final = []
        confidence_accuracy = []
        
        for est in estimates:
            task = est["task"]
            history = GPTaskEstimate.get_estimate_history(task.name)
            if len(history) > 1:
                initial = history[0].estimated_hours
                final = history[-1].estimated_hours
                initial_vs_final.append((final - initial) / initial if initial else 0)
            
            # Check if confidence level matched reality
            if task.status == "Done" and history:
                first_est = history[0]
                confidence_matched = (
                    (first_est.confidence_level == "High" and abs((final - initial) / initial if initial else 0) < 0.1) or
                    (first_est.confidence_level == "Low" and abs((final - initial) / initial if initial else 0) > 0.3)
                )
                confidence_accuracy.append(confidence_matched)
        
        metrics[user_id] = {
            "average_adjustment": sum(initial_vs_final) / len(initial_vs_final) if initial_vs_final else 0,
            "confidence_accuracy": sum(confidence_accuracy) / len(confidence_accuracy) if confidence_accuracy else 0,
            "estimate_count": len(estimates)
        }
    
    return metrics

def _find_estimate_patterns(estimates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find common patterns in estimate changes"""
    patterns = []
    
    # Group estimates by task
    task_estimates = {}
    for est in estimates:
        task_id = est["task"].name
        if task_id not in task_estimates:
            task_estimates[task_id] = []
        task_estimates[task_id].append(est["estimate"])
    
    # Analyze patterns
    for task_id, history in task_estimates.items():
        if len(history) < 2:
            continue
        
        # Look for significant increases
        for i in range(1, len(history)):
            prev = history[i-1]
            curr = history[i]
            change = (curr.estimated_hours - prev.estimated_hours) / prev.estimated_hours
            
            if abs(change) > 0.5:  # 50% change
                patterns.append({
                    "task_id": task_id,
                    "type": "large_adjustment",
                    "change_percentage": change * 100,
                    "timestamp": curr.creation_timestamp,
                    "note": curr.note
                })
    
    return patterns

def _calculate_stability_metrics(history: List["GPTaskEstimate"]) -> Dict[str, Any]:
    """Calculate stability metrics for a series of estimates"""
    if len(history) < 2:
        return {
            "is_stable": True,
            "volatility": 0,
            "trend": "stable"
        }
    
    changes = []
    for i in range(1, len(history)):
        prev = history[i-1].estimated_hours
        curr = history[i].estimated_hours
        changes.append((curr - prev) / prev if prev else 0)
    
    volatility = sum(abs(c) for c in changes) / len(changes)
    
    return {
        "is_stable": volatility < 0.2,  # Less than 20% average change
        "volatility": volatility * 100,  # Convert to percentage
        "trend": "increasing" if sum(changes) > 0 else "decreasing" if sum(changes) < 0 else "stable",
        "change_count": len([c for c in changes if abs(c) > 0.1])  # Count significant changes
    }

def _analyze_confidence_accuracy(history: List["GPTaskEstimate"]) -> Dict[str, Any]:
    """Analyze how well confidence levels matched reality"""
    if len(history) < 2:
        return {
            "confidence_matched": True,
            "confidence_trend": "stable"
        }
    
    confidence_scores = {"High": 3, "Medium": 2, "Low": 1}
    confidence_changes = []
    
    for i in range(1, len(history)):
        prev_score = confidence_scores[history[i-1].confidence_level]
        curr_score = confidence_scores[history[i].confidence_level]
        confidence_changes.append(curr_score - prev_score)
    
    return {
        "confidence_matched": abs(history[-1].estimated_hours - history[0].estimated_hours) / history[0].estimated_hours < 0.2,
        "confidence_trend": "increasing" if sum(confidence_changes) > 0 else "decreasing" if sum(confidence_changes) < 0 else "stable",
        "initial_confidence": history[0].confidence_level,
        "final_confidence": history[-1].confidence_level
    }

def _analyze_progress_consistency(history: List["GPTaskEstimate"]) -> Dict[str, Any]:
    """Analyze consistency of progress based on remaining hours"""
    if len(history) < 2:
        return {
            "is_consistent": True,
            "progress_rate": 0
        }
    
    # Calculate progress rate between each estimate
    rates = []
    for i in range(1, len(history)):
        prev = history[i-1]
        curr = history[i]
        time_diff = (curr.creation_timestamp - prev.creation_timestamp).total_seconds() / 3600  # Convert to hours
        if time_diff > 0:
            progress = prev.remaining_hours - curr.remaining_hours
            rates.append(progress / time_diff)
    
    avg_rate = sum(rates) / len(rates) if rates else 0
    rate_variance = sum((r - avg_rate) ** 2 for r in rates) / len(rates) if rates else 0
    
    return {
        "is_consistent": rate_variance < 0.1,  # Low variance in progress rate
        "progress_rate": avg_rate,  # Hours completed per hour
        "rate_variance": rate_variance,
        "progress_pattern": "steady" if rate_variance < 0.1 else "variable"
    }

def _identify_estimate_risks(history: List["GPTaskEstimate"]) -> List[Dict[str, Any]]:
    """Identify risk factors in estimation history"""
    risks = []
    
    if not history:
        return risks
    
    # Check for frequent changes
    if len(history) > 3:
        risks.append({
            "type": "frequent_updates",
            "description": f"Task has been re-estimated {len(history)} times"
        })
    
    # Check for decreasing confidence
    confidence_scores = {"High": 3, "Medium": 2, "Low": 1}
    if len(history) > 1:
        initial_confidence = confidence_scores[history[0].confidence_level]
        final_confidence = confidence_scores[history[-1].confidence_level]
        if final_confidence < initial_confidence:
            risks.append({
                "type": "decreasing_confidence",
                "description": f"Confidence decreased from {history[0].confidence_level} to {history[-1].confidence_level}"
            })
    
    # Check for large increases
    if len(history) > 1:
        initial = history[0].estimated_hours
        final = history[-1].estimated_hours
        if final > initial * 2:
            risks.append({
                "type": "large_increase",
                "description": f"Estimate more than doubled from {initial} to {final} hours"
            })
    
    return risks

def _generate_recommendations(
    all_estimates: List[Dict[str, Any]],
    user_estimates: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Generate recommendations for improving estimation process"""
    recommendations = []
    
    # Analyze overall patterns
    if all_estimates:
        trends = _analyze_overall_trends(all_estimates)
        if trends["volatility"] > 0.3:
            recommendations.append({
                "type": "high_volatility",
                "description": "High volatility in estimates suggests need for more thorough initial analysis",
                "action": "Consider implementing pre-estimation checklists and technical review sessions"
            })
    
    # Analyze user patterns
    user_metrics = _analyze_user_metrics(user_estimates)
    for user_id, metrics in user_metrics.items():
        if metrics["confidence_accuracy"] < 0.7:
            recommendations.append({
                "type": "confidence_calibration",
                "user_id": user_id,
                "description": f"User's confidence levels don't match actual outcomes ({metrics['confidence_accuracy']*100:.0f}% accuracy)",
                "action": "Review past estimates and actual outcomes to better calibrate confidence levels"
            })
    
    return recommendations 