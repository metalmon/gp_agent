import frappe
from typing import Dict, Any, Union

def get_settings_overrides(
    team_id: str = None,
    project_id: str = None,
    discussion_id: str = None,
    as_dict: bool = False
) -> Union[Any, Dict[str, Any]]:
    """Get settings with overrides from team/project/discussion
    
    Args:
        team_id: Team ID to check team-specific settings
        project_id: Project ID to check project-specific settings
        discussion_id: Discussion ID to check discussion-specific settings
        as_dict: Whether to return result as dictionary (default: False)
        
    Returns:
        Settings with overrides applied in order: team -> project -> discussion
        Returns Frappe document by default, or dictionary if as_dict=True
    """
    # Get base settings
    settings = frappe.get_single("GP Agent Settings")
    
    # Check team settings override
    if team_id:
        team_override = frappe.get_value("GP Team Settings Override", team_id, as_dict=True)
        if team_override:
            # Update settings with non-null values from override
            for field_name, value in team_override.items():
                if value is not None and hasattr(settings, field_name):
                    setattr(settings, field_name, value)
    
    # Check project settings override
    if project_id:
        project_override = frappe.get_value("GP Project Settings Override", project_id, as_dict=True)
        if project_override:
            # Update settings with non-null values from override
            for field_name, value in project_override.items():
                if value is not None and hasattr(settings, field_name):
                    setattr(settings, field_name, value)
                
    # Check discussion settings override
    if discussion_id:
        discussion_override = frappe.get_value("GP Discussion Settings Override", discussion_id, as_dict=True)
        if discussion_override:
            # Update settings with non-null values from override
            for field_name, value in discussion_override.items():
                if value is not None and hasattr(settings, field_name):
                    setattr(settings, field_name, value)
    
    # Return as dict if requested
    if as_dict:
        return settings.as_dict()
                
    return settings