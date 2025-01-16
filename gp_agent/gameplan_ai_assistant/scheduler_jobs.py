import json
import frappe
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from frappe.utils.data import get_datetime_str
from gp_agent.gameplan_ai_assistant.llm.openai import OpenAIClient
from gp_agent.gameplan_ai_assistant.llm.anthropic import AnthropicClient
from gp_agent.gameplan_ai_assistant.processing import create_agent_log
from .gameplan_api import GameplanAPI
from .context.factory import ContextFactory
from .tools.registry import get_tool_schemas
from .utils.logging import log_debug
from .utils.settings import get_settings_overrides


# Type alias for GP Agent Log document
GPAgentLog = Any  # frappe.model.document.Document 
Log = GPAgentLog  # Alias for type hints

def get_teams_to_process(settings: Any) -> List[Any]:
    """Get list of teams to process based on settings
    
    Args:
        settings: GP Agent Settings document
        
    Returns:
        List of team documents with 'name' field
    """
    # Get all teams
    teams = frappe.get_all("GP Team", fields=["name"])
    
    # If include_teams is empty, process all teams except excluded
    if not settings.include_teams:
        if settings.exclude_teams:
            exclude_list = [team.strip() for team in settings.exclude_teams.split('\n') if team.strip()]
            teams = [team for team in teams if team.name not in exclude_list]
        return teams
        
    # Otherwise, only process included teams
    include_list = [team.strip() for team in settings.include_teams.split('\n') if team.strip()]
    return [team for team in teams if team.name in include_list]

@frappe.whitelist()
def process_pending_logs(is_background: bool = False):
    """Process pending GP Agent Logs"""
    settings = frappe.get_single("GP Agent Settings")
    
    # Skip if processing is disabled
    if not settings.enabled:
        log_debug("GP Agent processing is disabled")
        return
        
    log_debug("=== Starting process_pending_logs ===")
    
    try:
        # Get only queued or error logs with retries remaining
        # Explicitly exclude Processing status
        logs = frappe.get_list(
            "GP Agent Log",
            filters={
                "status": ["in", ["Queued", "Error"]],  # Removed Processing
                "retry_count": ["<", settings.max_retries]
            },
            fields=["name", "status", "retry_count"],
            order_by="creation asc"
        )
        
        log_debug(f"Found {len(logs)} queued or error logs")
        
        # Process each log
        for log_info in logs:
            try:
                #log_debug(f"Processing log {log_info.name} (status: {log_info.status}, retry_count: {log_info.retry_count})")
                # Process log using process_single_log
                frappe.enqueue(
                    method="gp_agent.gameplan_ai_assistant.processing.process_single_log",
                    queue="default",
                    timeout=300,
                    log_name=log_info.name,
                    is_background=is_background,
                    now=True
                )
            except Exception as e:
                log_debug(f"Error processing log {log_info.name}: {str(e)}")
                
    except Exception as e:
        log_debug(f"Error in process_pending_logs: {str(e)}")
        frappe.log_error(
            title="GP Agent Processing Error",
            message=f"Error in process_pending_logs: {str(e)}"
        )
        return  # Exit with error

def scheduled_process_pending_logs():
    """Wrapper for process_pending_logs to be called by scheduler"""
    process_pending_logs(is_background=True)

def schedule_agent_runs(is_background: bool = True):
    """Schedule agent runs for all active discussions"""
    settings = get_settings_overrides()
    
    if not settings.enabled:
        return
        
    # Validate model is set
    if not settings.model:
        log_debug("Model is not set in GP Agent Settings")
        raise frappe.ValidationError("Please select a model in GP Agent Settings before running the agent")
    
    # Validate default user exists
    if not frappe.db.exists("User", settings.default_user):
        log_debug(f"Default user {settings.default_user} not found, using Administrator")
        settings.default_user = "Administrator"
    
    # Check if we should run based on schedule
    current_hour = frappe.utils.now_datetime().hour
    current_weekday = frappe.utils.now_datetime().weekday()

    if settings.schedule == "Daily Morning" and current_hour != 9:  # 9 AM
        return
    elif settings.schedule == "Daily Evening" and current_hour != 18:  # 6 PM
        return
    elif settings.schedule == "Weekly on Weekends" and current_weekday not in [5, 6]:  # Saturday = 5, Sunday = 6
        return
    
    log_debug("Starting schedule_agent_runs")
    
    try:
        api = GameplanAPI()
        
        # Get teams to process
        teams = get_teams_to_process(settings)
        team_names = [t.name for t in teams]
        #log_debug(f"Processing teams: {team_names}")
        
        # Get active projects
        projects = api.get_projects(
            team_names=team_names,
            status="Open",
            archived_at=None
        )
        #log_debug(f"Found {len(projects)} active projects")
        
        # Process each team
        for team in teams:
            try:
                #log_debug(f"Processing team: {team.name}")
                
                # Get team's projects
                team_projects = [p for p in projects if p.team == team.name]
                
                # Process each project
                for project in team_projects:
                    try:
                        #log_debug(f"Processing project: {project.name}")
                        # Get recent discussions
                        discussions = api.get_project_discussions(project.name)
                        if not discussions:
                            #log_debug(f"No discussions found for project {project.name}")
                            continue
                        
                        #log_debug(f"Found {len(discussions)} discussions in project")
                        
                        for discussion in discussions:
                            try:
                                #log_debug(f"Processing discussion: {discussion.name}")
                                
                                # Get settings with overrides
                                discussion_settings = get_settings_overrides(
                                    team_id=team.name,
                                    project_id=project.name,
                                    discussion_id=discussion.name
                                )
                                #log_debug(f"Settings with overrides: {discussion_settings}")
                                
                                # First check if we should skip agent responses based on settings
                                skip_agent_messages = discussion_settings.skip_if_last_message_from_agent_user
                                #log_debug(f"Skip agent messages: {skip_agent_messages}")

                                # Get discussion details
                                discussion_doc = api.get_discussion(discussion.name)
                                #log_debug(f"Discussion owner: {discussion_doc.get('owner')}")
                                #log_debug(f"Discussion content exists: {bool(discussion_doc.get('content'))}")
                                #log_debug(f"Last post by: {discussion_doc.get('last_post_by')}")
                                #log_debug(f"Comments count: {discussion_doc.get('comments_count', 0)}")

                                # Only check last message if skip_agent_messages is enabled
                                if skip_agent_messages:
                                    # If there's no last_post_by, check the discussion owner
                                    last_message_owner = discussion.get('last_post_by') or discussion.get('owner')
                                    
                                    # Skip if last message is from agent
                                    #log_debug(f"Last message owner: {last_message_owner}")
                                    #log_debug(f"Agent user: {discussion_settings.default_user}")
                                    if last_message_owner == discussion_settings.default_user:
                                        #log_debug(f"Last message in discussion {discussion.name} is from agent {discussion_settings.default_user} - skipping due to settings")
                                        continue
                                
                                # Get last comment ID if exists
                                last_message_id = api.get_last_comment_id(
                                    discussion_id=discussion.name,
                                    last_post_by=discussion.last_post_by,
                                    last_post_at=discussion.last_post_at
                                )
                                #log_debug(f"Last message ID: {last_message_id}")
                                
                                # Check if we already have a log for this message state
                                if api.log_exists(
                                    discussion_id=discussion.name,
                                    last_message_id=last_message_id
                                ):
                                    #log_debug(f"Log already exists for discussion {discussion.name} with last_message_id {last_message_id} - skipping")
                                    continue
                                    
                                #log_debug(f"Building context for discussion {discussion.name}")
                                
                                # Create builder with overridden settings
                                builder, formatter = ContextFactory.create(discussion_settings.as_dict())
                                
                                # Build context using builder and formatter
                                system_context = builder.build_system_context(
                                    discussion_id=discussion.name,
                                    team_id=team.name,
                                    project_id=project.name
                                )
                                
                                messages_context = builder.build_messages_context(
                                    discussion_id=discussion.name,
                                    team_id=team.name,
                                    project_id=project.name,
                                    last_message_id=last_message_id
                                )
                                
                                # Format context for the model
                                formatted_system_context = formatter.format_system_context(system_context)
                                formatted_messages = formatter.format_messages(messages_context)
                                
                                # Create log
                                #log_debug(f"Creating log for discussion {discussion.name}")
                                
                                # Create agent log with settings
                                create_agent_log(
                                    team_id=team.name,
                                    project_id=project.name,
                                    discussion_id=discussion.name,
                                    agent_user=discussion_settings.default_user,
                                    context={
                                        'system_prompt': formatted_system_context,
                                        'messages': formatted_messages,
                                        'tools': get_tool_schemas()
                                    },
                                    last_message_id=last_message_id,
                                    model=discussion_settings.model,
                                    temperature=discussion_settings.temperature,
                                    max_tokens=discussion_settings.max_tokens,
                                    top_p=discussion_settings.top_p,
                                    top_k=discussion_settings.top_k,
                                    context_depth=discussion_settings.context_depth
                                )
                            except Exception as e:
                                import traceback
                                error_trace = traceback.format_exc()
                                log_debug(f"Error processing discussion {discussion.name}: {str(e)}")
                                log_debug(f"Error traceback: {error_trace}")
                                if not is_background:
                                    raise
                                continue  # Continue with next discussion
                                
                    except Exception as e:
                        log_debug(f"Error processing project {project.name}: {str(e)}")
                        if not is_background:
                            raise
                        continue  # Continue with next project
                        
            except Exception as e:
                log_debug(f"Error processing team {team.name}: {str(e)}")
                if not is_background:
                    raise
                continue  # Continue with next team
                
    except Exception as e:
        log_debug(f"Fatal error in schedule_agent_runs: {str(e)}")
        if not is_background:
            raise
        return  # Exit with error

def scheduled_agent_runs():
    """Wrapper for schedule_agent_runs to be called by scheduler"""
    schedule_agent_runs(is_background=True)

def scheduled_process_pending_logs():
    """Wrapper for process_pending_logs to be called by scheduler"""
    process_pending_logs(is_background=True) 