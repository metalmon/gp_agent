"""
Tool registration initialization.
Registers all available tools with the global registry.
"""

from .registry import register_tool, clear_registry
from .pages.get_pages_list import GetPagesListTool
from .pages.create_page import CreatePageTool
from .pages.update_page import UpdatePageTool
from .pages.get_page_content import GetPageContentTool
from .tasks import (
    GetTaskDetailsTool,
    GetTasksListTool,
    UpdateTaskTool,
    GetUserTasksTool,
    CreateTaskDependencyTool,
    GetTaskDependenciesTool,
    GetTaskEstimateHistoryTool,
    AnalyzeEstimateQualityTool,
    AnalyzeEstimateTrendsTool,
    AnalyzeEstimateChangesTool,
    PredictEstimateChangesTool,
    AnalyzeCriticalPathTool,
    PredictCompletionDatesTool,
    AnalyzeTeamWorkloadTool,
    GetTeamEstimationMetricsTool,
    FindSimilarTasksTool,
    UpdateTaskEstimateTool
)
from .discussion.get_comments import GetCommentsDiscussionTool
from .web import WebSearchTool, GetWebpageContentTool
import frappe

_tools_registered = False

def register_tools():
    """Register all available tools"""
    global _tools_registered
    
    if _tools_registered:
        return
        
    # Clear existing registry first
    clear_registry()
    
    # Page tools
    register_tool(GetPagesListTool())
    register_tool(CreatePageTool())
    register_tool(UpdatePageTool())
    register_tool(GetPageContentTool())
    
    # Task tools
    register_tool(GetTasksListTool())
    register_tool(GetTaskDetailsTool())
    register_tool(UpdateTaskTool())
    register_tool(GetUserTasksTool())
    register_tool(CreateTaskDependencyTool())
    register_tool(GetTaskDependenciesTool())
    register_tool(GetTaskEstimateHistoryTool())
    register_tool(AnalyzeEstimateQualityTool())
    register_tool(AnalyzeEstimateTrendsTool())
    register_tool(AnalyzeEstimateChangesTool())
    register_tool(PredictEstimateChangesTool())
    register_tool(AnalyzeCriticalPathTool())
    register_tool(PredictCompletionDatesTool())
    register_tool(AnalyzeTeamWorkloadTool())
    register_tool(GetTeamEstimationMetricsTool())
    register_tool(FindSimilarTasksTool())
    register_tool(UpdateTaskEstimateTool())
    
    # Discussion tools
    register_tool(GetCommentsDiscussionTool())
    
    # Web tools
    register_tool(WebSearchTool())
    register_tool(GetWebpageContentTool())
    
    _tools_registered = True 