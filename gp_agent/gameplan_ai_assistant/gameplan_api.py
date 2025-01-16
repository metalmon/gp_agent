from datetime import datetime
import frappe
from typing import List, Dict, Optional, Any
from frappe.exceptions import DoesNotExistError
from .utils import log_debug


class GameplanAPI:
    """Gameplan API wrapper with singleton pattern"""
    
    _instance = None
    
    def __init__(self, user=None):
        if not user and not frappe.session.user:
            raise ValueError("User must be provided when session user is not available")
            
        self.user = user or frappe.session.user
        
        # Check if user exists in database and fallback to Administrator if not
        if not frappe.db.exists("User", self.user):
            raise DoesNotExistError(f"User {self.user} does not exist in the database")
        
    @classmethod
    def get_instance(cls) -> Optional['GameplanAPI']:
        """Get singleton instance"""
        return cls._instance
    
    @classmethod
    def set_instance(cls, instance: 'GameplanAPI'):
        """Set singleton instance"""
        cls._instance = instance
    
    def get_projects(self, team_names: List[str], status: str, archived_at: Optional[str], limit: int = 10) -> List[Dict]:
        """Get projects for a teams"""
        try:
            return frappe.get_all(
                "GP Project",
                filters={"team": ["in", team_names], "status": status, "archived_at": archived_at},
                fields=["name", "title", "team"],
                limit=limit
            )
        except Exception as e:
            log_debug(f"Error fetching projects: {str(e)}")
            return []
        
    def get_project_discussions(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get discussions for a project"""
        try:
            # Try to convert project_id to int if it's a string
            numeric_project_id = int(project_id)
        except (ValueError, TypeError):
            # If conversion fails, use original value
            numeric_project_id = project_id
            
        # Get project title first
        project = frappe.db.get_value("GP Project", numeric_project_id, ["title"], as_dict=True)
        project_title = project.title if project else "Unknown Project"
        log_debug(f"Getting discussions for project: {project_id} ('{project_title}', converted to: {numeric_project_id})")
        
        discussions = frappe.get_all(
            "GP Discussion",
            filters={
                "project": numeric_project_id,
                "status": ["!=", "Closed"]
            },
            fields=[
                "name",
                "title",
                "project",
                "last_post_by",
                "last_post_at",
                "modified",
                "content",  # Add content field
                "owner"     # Add owner field
            ],
            order_by="modified desc",
            limit=limit
        )
        
        log_debug(f"Found {len(discussions)} discussions in project '{project_title}', first discussion: {discussions[0] if discussions else None}")
        
        # Log project IDs for each discussion
        for disc in discussions:
            log_debug(f"Discussion {disc.name} in project '{project_title}': project_id={disc.project}")
            
        return discussions
        
    def get_discussion_comments(self, discussion_id: str, limit: int = 10) -> List[Dict]:
        """Get comments for a discussion"""
        log_debug(f"Getting comments for discussion {discussion_id} with limit {limit}")
        
        # First get the discussion to get its project_id
        discussion = frappe.db.get_value("GP Discussion", discussion_id, ["project"], as_dict=True)
        project_id = discussion.project if discussion else None
        
        # Get project title
        project = frappe.db.get_value("GP Project", project_id, ["title"], as_dict=True) if project_id else None
        project_title = project.title if project else "Unknown Project"
        
        log_debug(f"Got project_id={project_id} ('{project_title}') for discussion {discussion_id}")
        
        comments = frappe.get_all(
            "GP Comment",
            filters={
                "reference_doctype": "GP Discussion",
                "reference_name": discussion_id,
                "deleted_at": ["is", "not set"]
            },
            fields=[
                "name",
                "content",
                "owner",
                "creation",
                "modified",
                "reference_name"
            ],
            order_by="creation desc",
            limit=limit
        )
        
        log_debug(f"Found {len(comments)} comments in discussion {discussion_id} (project '{project_title}')")
        for comment in comments:
            # Add project_id to each comment
            comment.project = project_id
            log_debug(f"Comment {comment.name} in project '{project_title}': reference_name={comment.reference_name}, project_id={comment.project}")
            
        return comments
        
    def get_project_tasks(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get tasks for a project. Returns only non-completed tasks by default."""
        return frappe.get_all(
            "GP Task",
            filters={
                "project": project_id,
                "status": ["!=", "Completed"]
            },
            fields=[
                "name",
                "title",
                "description",
                "status",
                "priority",
                "owner",
                "modified",
                "assigned_to",
                "due_date"
            ],
            order_by="modified desc",
            limit=limit
        )

    def get_all_project_tasks(self, project_id: str, status: Optional[List[str]] = None, assigned_to: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get all tasks for a project with optional filters. Does not filter out completed tasks by default.
        
        Args:
            project_id: ID of the project
            status: Optional list of statuses to filter by
            assigned_to: Optional user to filter tasks assigned to
            limit: Maximum number of tasks to return (default: 10)
            
        Returns:
            List of tasks matching the filters
        """
        filters = {"project": project_id}
        
        # Add status filter if provided and valid
        if status:
            valid_statuses = ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
            valid_status_filters = [s for s in status if s in valid_statuses]
            if valid_status_filters:
                filters["status"] = ["in", valid_status_filters]
        
        # Add assignee filter if provided
        if assigned_to:
            filters["assigned_to"] = assigned_to
            
        return frappe.get_all(
            "GP Task",
            filters=filters,
            fields=[
                "name",
                "title",
                "description",
                "status",
                "priority",
                "start_date",
                "due_date",
                "is_completed",
                "assigned_to",
                "comments_count",
                "idx",
                "modified",
                "owner",
                "team"
            ],
            order_by="modified desc",
            limit=limit
        )
        
    def get_project_pages(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get pages for a project"""
        return frappe.get_all(
            "GP Page",
            filters={
                "project": project_id
            },
            fields=[
                "name",
                "title",
                "content",
                "owner",
                "creation",
                "modified",
                "project",
                "user"
            ],
            order_by="modified desc",
            limit=limit
        )
    
    def create_comment(self, discussion_id: str, message: str) -> Dict:
        """Create a new comment in a discussion"""
        # Get latest message timestamp
        latest_comment = frappe.get_all(
            "GP Comment",
            filters={
                "reference_doctype": "GP Discussion",
                "reference_name": discussion_id,
                "deleted_at": ["is", "not set"]
            },
            fields=["creation"],
            order_by="creation desc",
            limit=1
        )
        
        # Use latest message time + 1 second, or current time if no messages
        if latest_comment:
            latest_time = frappe.utils.get_datetime(latest_comment[0].creation)
            # Add 1 second to ensure our message appears last
            creation_time = frappe.utils.add_to_date(latest_time, seconds=1)
        else:
            # If no messages yet, use current time
            creation_time = frappe.utils.now_datetime()
        
        # Validate message
        if not message:
            log_debug("Message content is empty or None")
            raise ValueError("Message content cannot be empty")
            
        # Create comment with explicit timestamp
        doc = frappe.get_doc({
            "doctype": "GP Comment",
            "content": message,
            "reference_doctype": "GP Discussion",
            "reference_name": discussion_id,
            "creation": creation_time,
            "modified": creation_time,
            "owner": self.user,
            "modified_by": self.user
        })
        
        log_debug(f"Creating comment in discussion {discussion_id} with timestamp {creation_time}")
        
        # Insert comment with flags to prevent modified updates
        doc.flags.ignore_modified = True
        doc.insert(ignore_permissions=True)
        
        # Update discussion's information without triggering modified updates
        discussion = frappe.get_doc("GP Discussion", discussion_id)
        discussion.flags.ignore_modified = True
        discussion.flags.ignore_links = True  # Prevent updating linked docs
        discussion.last_post_at = creation_time
        discussion.last_post_by = self.user
        discussion.comments_count = (discussion.comments_count or 0) + 1
        discussion.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"success": True, "creation_time": creation_time}

    def get_project_polls(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get polls for a project"""
        # Get discussions for the project
        discussions = frappe.get_all(
            "GP Discussion",
            filters={"project": project_id},
            fields=["name"],
            limit=limit
        )
        
        # Get polls for these discussions
        polls = []
        for disc in discussions:
            disc_polls = frappe.get_all(
                "GP Poll",
                filters={
                    "discussion": disc.name
                },
                fields=[
                    "name",
                    "title",
                    "multiple_answers",
                    "anonymous",
                    "total_votes",
                    "discussion",
                    "stopped_at"
                ],
                limit=limit
            )
            
            # Get options and votes for each poll
            for poll in disc_polls:
                # Get options
                poll.options = frappe.get_all(
                    "GP Poll Option",
                    filters={"parent": poll.name},
                    fields=["title", "percentage", "votes"]
                )
                
                # Get votes if not anonymous
                if not poll.anonymous:
                    poll.votes = frappe.get_all(
                        "GP Poll Vote",
                        filters={"parent": poll.name},
                        fields=["user", "option"]
                    )
                    
                polls.append(poll)
                
        return polls[:limit]  # Ensure we don't return more than limit

    def get_teams(self, limit: int = 10) -> List[Dict]:
        """Get list of teams"""
        return frappe.get_all(
            "GP Team",
            filters={
                "archived_at": ["is", "not set"]
            },
            fields=["name", "title"],
            limit=limit
        )

    def get_team_projects(self, team_id: str, limit: int = 10) -> List[Dict]:
        """Get projects for a team"""
        return frappe.get_all(
            "GP Project",
            filters={
                "team": team_id,
                "status": "Open",
                "archived_at": ["is", "not set"]
            },
            fields=["name", "title"],
            limit=limit
        )

    def get_discussion(self, discussion_id: str) -> Dict:
        """Get details of a single discussion"""
        log_debug(f"Getting details for discussion {discussion_id}")
        
        discussion = frappe.get_doc("GP Discussion", discussion_id)
        if not discussion:
            log_debug(f"Discussion {discussion_id} not found")
            return {}
            
        # Get project title
        project = frappe.db.get_value("GP Project", discussion.project, ["title"], as_dict=True) if discussion.project else None
        project_title = project.title if project else "Unknown Project"
        
        log_debug(f"Found discussion {discussion_id} in project '{project_title}' (project_id={discussion.project})")
        
        return {
            "name": discussion.name,
            "title": discussion.title,
            "project": discussion.project,
            "content": discussion.content,
            "owner": discussion.owner,
            "last_post_by": discussion.last_post_by,
            "last_post_at": str(discussion.last_post_at) if discussion.last_post_at else None,
            "modified": str(discussion.modified) if discussion.modified else None,
            "status": discussion.status
        }

    def get_project(self, project_id: str) -> Dict:
        """Get a single project with all fields"""
        return frappe.get_doc("GP Project", project_id).as_dict()

    def get_project_title(self, project_id: str) -> str:
        """Get project title"""
        if not project_id:
            return "Unknown Project"
        project = frappe.db.get_value("GP Project", project_id, ["title"], as_dict=True)
        return project.title if project else "Unknown Project"

    def get_team_settings_override(self, team_id: str) -> Optional[Dict]:
        """Get team settings override"""
        if not team_id:
            return None
        return frappe.db.get_value(
            "GP Team Settings Override",
            {"team": team_id},
            ["model", "system_prompt", "default_user", "temperature", "max_tokens", "top_p", 
             "skip_if_last_message_from_agent_user", "context_depth", "chat_memory"],
            as_dict=True
        )

    def get_project_settings_override(self, project_id: str) -> Optional[Dict]:
        """Get project settings override"""
        if not project_id:
            return None
        return frappe.db.get_value(
            "GP Project Settings Override",
            {"project": project_id},
            ["model", "system_prompt", "default_user", "temperature", "max_tokens", "top_p", 
             "skip_if_last_message_from_agent_user", "context_depth", "chat_memory"],
            as_dict=True
        )

    def get_discussion_settings_override(self, discussion_id: str) -> Optional[Dict]:
        """Get discussion settings override"""
        if not discussion_id:
            return None
        return frappe.db.get_value(
            "GP Discussion Settings Override",
            {"discussion": discussion_id},
            ["model", "system_prompt", "default_user", "temperature", "max_tokens", "top_p", 
             "skip_if_last_message_from_agent_user", "context_depth", "chat_memory"],
            as_dict=True
        )

    def get_team(self, team_id: str) -> Dict:
        """Get a single team with all fields"""
        if not team_id:
            return {"title": "Unknown Team"}
        return frappe.get_doc("GP Team", team_id).as_dict()

    def get_discussion_project_and_team(self, discussion_id: str) -> Dict:
        """Get project and team info for a discussion"""
        if not discussion_id:
            return {"project": None, "team": None}
            
        discussion = frappe.db.get_value("GP Discussion", discussion_id, ["project"], as_dict=True)
        if not discussion or not discussion.project:
            return {"project": None, "team": None}
            
        project = frappe.db.get_value("GP Project", discussion.project, ["team", "title"], as_dict=True)
        if not project:
            return {"project": discussion.project, "team": None, "project_title": "Unknown Project"}
            
        return {
            "project": discussion.project,
            "team": project.team,
            "project_title": project.title
        }

    def get_last_comment_id(self, discussion_id: str, last_post_by: str, last_post_at: str) -> Optional[str]:
        """Get last comment ID for a discussion"""
        if not discussion_id or not last_post_by or not last_post_at:
            log_debug(f"Missing discussion_id, last_post_by, or last_post_at for discussion {discussion_id}")
            return None
            
        log_debug(f"Getting last comment for discussion {discussion_id} with last_post_by {last_post_by} and last_post_at {last_post_at}")
        
        # Convert last_post_at to datetime if it's string
        if isinstance(last_post_at, str):
            last_post_at = frappe.utils.get_datetime(last_post_at)
            
        # Add/subtract 1 second to create a range
        start_time = frappe.utils.add_to_date(last_post_at, seconds=-1)
        end_time = frappe.utils.add_to_date(last_post_at, seconds=1)
        
        last_comment = frappe.get_all(
            "GP Comment",
            filters={
                "reference_doctype": "GP Discussion",
                "reference_name": discussion_id,
                "owner": last_post_by,
                "creation": ["between", [start_time, end_time]]
            },
            fields=["name"],
            limit=1
        )
        log_debug(f"Last comment: {last_comment}")
        return last_comment[0].name if last_comment else None
        
    def log_exists(self, discussion_id: str, last_message_id: str) -> bool:
        """Check if agent log exists for given parameters"""
        if not last_message_id:
            return False
            
        return bool(frappe.db.exists("GP Agent Log", {
            "discussion_id": discussion_id,
            "last_message_id": last_message_id
        })) 

    def get_comment_creation_time(self, comment_id: str) -> datetime:
        """Get creation time for a comment"""
        creation = frappe.db.get_value("GP Comment", comment_id, "creation")
        return creation

    def create_page(self, project_id: str, title: str, content: str) -> Dict:
        """Create a new page in the project"""
        log_debug(f"Creating page '{title}' in project {project_id}")
        
        # Create the page doc
        page = frappe.get_doc({
            "doctype": "GP Page",
            "project": project_id,
            "title": title,
            "content": content,
            "user": self.user
        })
        page.insert()
        
        log_debug(f"Created page {page.name} in project '{self.get_project_title(project_id)}' (project_id={project_id})")
        
        return {
            "id": page.name,
            "title": page.title,
            "url": f"/project/{project_id}/page/{page.name}"
        }

    def update_page(self, page_id: str, title: Optional[str] = None, content: Optional[str] = None) -> Dict:
        """Update an existing page"""
        log_debug(f"Updating page {page_id}")
        
        # Get the page doc
        page = frappe.get_doc("GP Page", page_id)
        
        # Update fields if provided
        if title is not None:
            page.title = title
        if content is not None:
            page.content = content
            
        page.save()
        
        log_debug(f"Updated page {page.name} in project '{self.get_project_title(page.project)}'")
        
        return {
            "id": page.name,
            "title": page.title,
            "url": f"/project/{page.project}/page/{page.name}"
        }

    def get_page_content(self, page_id: str) -> Dict:
        """Get content of a specific page"""
        log_debug(f"Getting content for page {page_id}")
        
        # Get the page doc
        page = frappe.get_doc("GP Page", page_id)
        
        log_debug(f"Retrieved page {page.name} from project '{self.get_project_title(page.project)}'")
        
        return {
            "id": page.name,
            "title": page.title,
            "content": page.content,
            "url": f"/project/{page.project}/page/{page.name}",
            "created_by": page.owner,
            "created_at": str(page.creation),
            "modified_at": str(page.modified)
        }

    def list_pages(self, project_id: str, limit: int = 10) -> List[Dict]:
        """List pages in a project
        
        Args:
            project_id: ID of the project to list pages from
            limit: Maximum number of pages to return (default: 10)
            
        Returns:
            List of pages with basic metadata
        """
        log_debug(f"Listing pages for project {project_id}")
        
        # Get all pages for the project
        pages = frappe.get_all(
            "GP Page",
            filters={"project": project_id},
            fields=[
                "name",
                "title",
                "owner",
                "user",
                "creation",
                "modified",
                "project"
            ],
            order_by="modified desc",
            limit=limit
        )
        
        project_title = self.get_project_title(project_id)
        log_debug(f"Found {len(pages)} pages in project '{project_title}'")
        
        # Format the response
        return [{
            "id": page.name,
            "title": page.title,
            "project": page.project,
            "owner": page.owner,
            "user": page.user,
            "creation": str(page.creation),
            "modified": str(page.modified)
        } for page in pages]

    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details
        
        Args:
            task_id: Task ID
            
        Returns:
            Task details or None if not found
        """
        try:
            task = frappe.get_doc("GP Task", task_id)
            return task.as_dict()
        except frappe.DoesNotExistError:
            log_debug(f"Task {task_id} not found")
            return None
        except Exception as e:
            log_debug(f"Error getting task details: {str(e)}")
            return None

    def update_task(
        self, 
        task_id: str,
        status: str = None,
        description: str = None,
        start_date: str = None,
        due_date: str = None,
        priority: str = None,
        assigned_to: str = None
    ) -> Dict:
        """Update task details
        
        Args:
            task_id: ID of the task to update
            status: New status (Backlog/Todo/In Progress/Done/Canceled)
            description: New description (HTML format)
            start_date: Start date (YYYY-MM-DD)
            due_date: Due date (YYYY-MM-DD)
            priority: Priority (Urgent/High/Medium/Low)
            assigned_to: User to assign the task to
            
        Returns:
            Updated task details
        """
        log_debug(f"Updating task {task_id}")
        
        # Get the task doc
        task = frappe.get_doc("GP Task", task_id)
        
        # Validate and update status if provided
        if status is not None:
            valid_statuses = ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
            if status in valid_statuses:
                task.status = status
                # Update completion status
                task.is_completed = 1 if status == "Done" else 0
                if status == "Done":
                    task.completed_at = frappe.utils.now_datetime()
                    task.completed_by = self.user
                elif task.is_completed:  # Was completed, now uncompleted
                    task.completed_at = None
                    task.completed_by = None
        
        # Validate and update priority if provided
        if priority is not None:
            valid_priorities = ["Urgent", "High", "Medium", "Low"]
            if priority in valid_priorities:
                task.priority = priority
        
        # Update other fields if provided
        if description is not None:
            task.description = description
        if start_date is not None:
            task.start_date = start_date
        if due_date is not None:
            task.due_date = due_date
        if assigned_to is not None:
            task.assigned_to = assigned_to
        
        # Save changes
        task.save()
        
        log_debug(f"Updated task {task.name}")
        
        # Return updated task details
        return self.get_task_details(task_id)

    def get_user_tasks(
        self,
        user_id: str,
        status: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get tasks assigned to a specific user
        
        Args:
            user_id: ID of the user to get tasks for
            status: Optional list of statuses to filter by (Backlog/Todo/In Progress/Done/Canceled)
            project_id: Optional project ID to filter tasks from
            limit: Maximum number of tasks to return (default: 10)
            
        Returns:
            List of tasks assigned to the user with basic metadata
        """
        log_debug(f"Getting tasks for user {user_id}")
        
        # Build filters
        filters = {"assigned_to": user_id}
        
        # Add status filter if provided
        if status:
            valid_statuses = ["Backlog", "Todo", "In Progress", "Done", "Canceled"]
            valid_status_filters = [s for s in status if s in valid_statuses]
            if valid_status_filters:
                filters["status"] = ["in", valid_status_filters]
                
        # Add project filter if provided
        if project_id:
            filters["project"] = project_id
            
        # Get tasks matching filters
        tasks = frappe.get_all(
            "GP Task",
            filters=filters,
            fields=[
                "name",
                "title",
                "description",
                "status",
                "priority", 
                "start_date",
                "due_date",
                "is_completed",
                "project",
                "comments_count",
                "idx",
                "modified"
            ],
            order_by="modified desc",
            limit=limit
        )
        
        log_debug(f"Found {len(tasks)} tasks assigned to user {user_id}")
        
        # Format the response
        return [{
            "id": task.name,
            "title": task.title,
            "description": task.description or "",
            "status": task.status,
            "priority": task.priority,
            "start_date": str(task.start_date) if task.start_date else None,
            "due_date": str(task.due_date) if task.due_date else None,
            "is_completed": task.is_completed,
            "project": task.project,
            "comments_count": task.comments_count or 0,
            "idx": task.idx,
            "modified": str(task.modified)
        } for task in tasks]

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Frappe
        
        Args:
            user_id: User ID/email
            
        Returns:
            Dict with user information including:
            - full_name: User's full name
            - email: User's email
            - user_image: URL to user's avatar (optional)
        """
        try:
            user = frappe.get_doc('User', user_id)
            return {
                'full_name': user.full_name,
                'email': user.email,
                'user_image': user.user_image if hasattr(user, 'user_image') else None
            }
        except Exception as e:
            frappe.log_error(f"Error getting user info: {str(e)}")
            return {
                'full_name': user_id,  # Fallback to user_id if we can't get the name
                'email': user_id
            }

    def get_team_users(self, team_id: str) -> List[Dict]:
        """Get users for a team
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of users with basic metadata
        """
        log_debug(f"Getting users for team {team_id}")
        
        # Get team members
        members = frappe.get_all(
            "GP Member",
            filters={"parent": team_id},
            fields=["user"]
        )
        
        # Get guest access
        guests = frappe.get_all(
            "GP Guest Access",
            filters={"team": team_id},
            fields=["user"]
        )
        
        # Combine users
        user_ids = list(set([m.user for m in members] + [g.user for g in guests]))
        
        # Get user profiles
        users = []
        for user_id in user_ids:
            profile = frappe.get_all(
                "GP User Profile",
                filters={"user": user_id},
                fields=["user", "full_name", "enabled"],
                limit=1
            )
            if profile:
                users.append({
                    "id": user_id,
                    "full_name": profile[0].full_name,
                    "enabled": profile[0].enabled
                })
            else:
                # Fallback to User doctype if no profile
                user = frappe.get_all(
                    "User",
                    filters={"name": user_id},
                    fields=["name", "full_name", "enabled"],
                    limit=1
                )
                if user:
                    users.append({
                        "id": user_id,
                        "full_name": user[0].full_name,
                        "enabled": user[0].enabled
                    })
        
        log_debug(f"Found {len(users)} users in team {team_id}")
        return users

def create_delayed_message(discussion_id: str, message: str, creation_time, user: str):
    """Create a message with specified creation time"""
    try:
        # Add detailed logging
        log_debug(f"Creating delayed message with params: discussion_id={discussion_id}, message_length={len(message) if message else 'None'}, creation_time={creation_time}, user={user}")
        
        # Validate message
        if not message:
            log_debug("Message content is empty or None")
            raise ValueError("Message content cannot be empty")
            
        # Validate user exists
        if not frappe.db.exists("User", user):
            log_debug(f"User {user} not found, using Administrator")
            user = "Administrator"
            
        # Set user context
        frappe.set_user(user)
        
        # Create comment with explicit timestamp
        doc = frappe.get_doc({
            "doctype": "GP Comment",
            "content": message,
            "reference_doctype": "GP Discussion",
            "reference_name": discussion_id,
            "creation": creation_time,
            "modified": creation_time,
            "owner": user,
            "modified_by": user
        })
        
        log_debug(f"Prepared comment document: {doc.as_dict()}")
        
        doc.insert(ignore_permissions=True)
        
        # Update discussion's information
        discussion = frappe.get_doc("GP Discussion", discussion_id)
        discussion.last_post_at = creation_time
        discussion.last_post_by = user
        discussion.comments_count = (discussion.comments_count or 0) + 1
        discussion.save()
        
        frappe.db.commit()
        
        log_debug(f"Created delayed message in discussion {discussion_id} with timestamp {creation_time}")
        
    except Exception as e:
        log_debug(f"Error creating delayed message: {str(e)}")
        log_debug(f"Error type: {type(e)}")
        log_debug(f"Error args: {e.args}")
        frappe.log_error(
            title="GP Agent Message Creation Failed",
            message=f"Error creating message in discussion {discussion_id}: {str(e)}\nMessage length: {len(message) if message else 'None'}"
        )
        raise 