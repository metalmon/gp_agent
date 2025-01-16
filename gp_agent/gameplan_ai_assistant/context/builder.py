from typing import Dict, List, Any, Optional, Union
import json
from .base import (
    BaseContextBuilder,
    BaseContextFormatter,
    SystemContext,
    Message
)
from ..gameplan_api import GameplanAPI
from ..utils.logging import log_debug


class SimpleContextBuilder(BaseContextBuilder):
    """Simple context builder that doesn't depend on GameplanAPI.
    Used for formatting tool calls and responses."""
    
    def __init__(self, settings: Dict[str, Any], formatter: Any):
        """Initialize builder with settings and formatter
        
        Args:
            settings: Settings dictionary
            formatter: Context formatter instance
        """
        self.settings = settings
        self.formatter = formatter
        
    def build_system_context(self, **kwargs) -> Dict[str, Any]:
        """Build system context
        
        Returns:
            Empty system context since we don't need it for tool calls
        """
        return {}
        
    def build_messages_context(self, messages: List[Dict[str, Any]]) -> List[Message]:
        """Build messages context
        
        Args:
            messages: List of messages
            
        Returns:
            List of messages
        """
        messages = []
        for message in messages:
            message = Message(
                content=message.get('content', ''),
                tasks=[],
                context={},
                role=message.get('role', 'assistant')
            )
            messages.append(message)
        return messages
        
    def build_tool_call_message(self, tool_calls: List[Dict[str, Any]]) -> Message:
        """Build message for tool calls
        
        Args:
            tool_calls: List of tool calls
            
        Returns:
            Message with tool calls
        """
        return Message(
            role='assistant',
            content=None,
            tool_calls=tool_calls,
            tasks=[],
            context={}
        )
        
    def build_tool_response_message(
        self,
        content: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        tool_name: str,
        tool_call_id: str
    ) -> List[Message]:
        """Build message for tool response
        
        Args:
            content: Response content (can be string or dict/list that needs serialization)
            tool_name: Tool name
            tool_call_id: Tool call ID
            timestamp: Message timestamp
            
        Returns:
            Message with tool response
        """
        #log_debug(f"Building tool response message for {tool_name} ({tool_call_id})")
        #log_debug(f"Content type before serialization: {type(content)}")
        #log_debug(f"Raw content: {content}")
        
        # Extract results from content if it's a list
        if isinstance(content, list):
            #log_debug(f"Processing list of {len(content)} results")
            if len(content) == 1:
                # Single result - extract it directly
                #log_debug("Extracting single result")
                result = content[0]
                if result is not None:
                    content = result
                    #log_debug(f"Extracted single result: {content}")
            else:
                # Multiple results - extract all results into array
                #log_debug("Extracting multiple results")
                results = []
                for item in content:
                    results.append(item)
                content = results
                #log_debug(f"Extracted {len(results)} results: {content}")
        
        # Serialize content if it's not already a string
        if not isinstance(content, str):
            log_debug("Content is not a string, serializing to JSON")
            content = json.dumps(content, ensure_ascii=False)
            log_debug(f"Serialized content: {content}")
        else:
            log_debug("Content is already a string, using as is")
            
        return Message(
            role='tool',
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tasks=[],
            context={}
        )


class GameplanContextBuilder(BaseContextBuilder):
    """Gameplan-specific context builder implementation"""
    
    def __init__(self, api: GameplanAPI, settings: Dict[str, Any], formatter: BaseContextFormatter):
        super().__init__(settings)
        self.api = api
        self.formatter = formatter

    def build_system_context(
        self,
        discussion_id: str,
        project_id: str,
        team_id: str
    ) -> SystemContext:
        """Build system context for Gameplan
        
        Args:
            discussion_id: Current discussion ID
            project_id: Current project ID 
            team_id: Current team ID
        """
        # Get base instructions
        base_instructions = self.settings.get('system_prompt', '')
        
        # Get chat memory setting
        chat_memory = self.settings.get('chat_memory', 10)
        
        # Get all project tasks and filter them
        all_tasks = self.api.get_project_tasks(project_id, limit=chat_memory)
        
        # Get discussion participants
        discussion = self.api.get_discussion(discussion_id)
        comments = self.api.get_discussion_comments(discussion_id)
        participants = {discussion.get('owner')} | {msg.get('owner') for msg in comments if msg.get('owner')}
        # Filter out agent user from participants
        participants = {user for user in participants if not self._is_agent_user(user)}
        
        # Get project info
        project = self.api.get_project(project_id)
        project_title = project.get('title', '')
        
        # Split tasks into unassigned and assigned to non-participants
        unassigned_tasks = []
        silent_users_tasks = []
        
        for task in all_tasks:
            assignee = task.get('assigned_to')
            if not assignee:
                unassigned_tasks.append(task)
            elif assignee not in participants:
                silent_users_tasks.append(task)
        
        # Get related content based on context depth from settings
        project_pages, related_discussions, related_tasks, related_pages, related_messages = self._get_related_content(
            discussion_id,
            project_id,
            team_id,
            self.settings
        )
        
        # Combine unassigned tasks with tasks of non-participating users
        system_tasks = unassigned_tasks + silent_users_tasks
        
        # Create and return system context with metadata
        return SystemContext(
            base_instructions=base_instructions,
            unassigned_tasks=system_tasks,
            pages=project_pages,
            related_discussions=related_discussions,
            related_tasks=related_tasks,
            related_pages=related_pages,
            related_messages=related_messages,
            metadata={
                'project_id': project_id,
                'discussion_id': discussion_id,
                'team_id': team_id,
                'participants': list(participants),
                'project_title': project_title,
                'discussion_title': discussion.get('title', '')
            }
        )

    def build_messages_context(
        self,
        discussion_id: str,
        project_id: str,
        team_id: str,
        last_message_id: Optional[str] = None
    ) -> List[Message]:
        """Build messages context
        
        Args:
            discussion_id: Current discussion ID
            project_id: Current project ID
            team_id: Current team ID
            last_message_id: Optional ID of last message to include
        """
        chat_memory = self.settings.get('chat_memory', 10)
        messages = []
        
        # Get discussion content
        discussion = self.api.get_discussion(discussion_id)
        
        # Get project info
        project = self.api.get_project(project_id)
        project_title = project.get('title', '')
        
        # Get discussion comments
        comments = self.api.get_discussion_comments(discussion_id, limit=chat_memory)
        
        # Get user tasks for all participants
        discussion_owner = discussion.get('owner')
        authors = {discussion_owner} | {msg.get('owner') for msg in comments if msg.get('owner')}
        # Filter out agent user from authors
        authors = {user for user in authors if not self._is_agent_user(user)}
        
        user_tasks = {}
        for author in authors:
            user_tasks[author] = self.api.get_user_tasks(
                author, 
                project_id=project_id,
                limit=chat_memory
            )
        
        messages = []
        
        # Add initial discussion message first
        if discussion.get('content'):
            message = Message(
                content=discussion.get('content', ''),
                tasks=user_tasks.get(discussion_owner, []),
                context={
                    'user_metadata': self._build_user_metadata(
                        discussion_owner,
                        discussion.get('creation', '')
                    ),
                    'project_metadata': {
                        'project_id': project_id,
                        'discussion_id': discussion_id,
                        'team_id': team_id,
                        'participants': list(authors),
                        'project_title': project_title,
                        'discussion_title': discussion.get('title', '')
                    }
                },
                role='user'
            )
            
            # Add tool instructions if this is the only message
            if not comments:
                message.context['tool_instructions'] = self.build_tool_instructions()
            
            messages.append(message)
        
        # Convert comments to messages and add them in reverse order
        comment_messages = []
        for comment in comments:
            message_id = comment.get('name')
            owner = comment.get('owner', '')
            is_agent = self._is_agent_user(owner)
            
            message = Message(
                content=comment.get('content', ''),
                tasks=user_tasks.get(owner, []) if not is_agent else [],
                context={
                    'user_metadata': self._build_user_metadata(
                        owner,
                        comment.get('creation', '')
                    ),
                    'project_metadata': {
                        'project_id': project_id,
                        'discussion_id': discussion_id,
                        'team_id': team_id,
                        'participants': list(authors),
                        'project_title': project_title,
                        'discussion_title': discussion.get('title', '')
                    }
                },
                role='assistant' if is_agent else 'user'
            )
            
            # Add tool instructions to the last user message in comments
            if message_id == last_message_id and message.role == 'user':
                message.context['tool_instructions'] = self.build_tool_instructions()
            
            comment_messages.append(message)
            
        # Add reversed comments after the discussion message
        messages.extend(reversed(comment_messages))
        
        return messages
    
    def _get_related_content(
        self,
        discussion_id: str,
        project_id: str,
        team_id: str,
        settings: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get related content based on context depth setting"""
        context_depth = settings.get('context_depth', 'Discussion Only')
        chat_memory = settings.get('chat_memory', 10)
        
        # Get current project pages regardless of context depth
        project_pages = self.api.get_project_pages(project_id, limit=chat_memory)
        
        related_discussions = []
        related_tasks = []
        related_pages = []
        related_messages = []
        
        if context_depth == 'Discussion Only':
            return project_pages, [], [], [], []
            
        elif context_depth == 'Project Wide':
            # Get other discussions from same project
            discussions = self.api.get_project_discussions(project_id, limit=chat_memory)
            for disc in discussions:
                if disc.get('name') != discussion_id:
                    related_discussions.append({
                        'type': 'discussion',
                        'title': disc.get('title', ''),
                        'content': disc.get('content', ''),
                        'author': disc.get('owner', ''),
                        'timestamp': disc.get('creation', ''),
                        'modified': disc.get('modified', '')
                    })
                    
                    # Get messages from related discussions
                    disc_messages = self.api.get_discussion_comments(disc.get('name'), limit=chat_memory)
                    for msg in disc_messages:
                        related_messages.append({
                            'discussion_id': disc.get('name'),
                            'discussion_title': disc.get('title', ''),
                            'author': msg.get('owner', ''),
                            'content': msg.get('content', ''),
                            'timestamp': msg.get('creation', '')
                        })
            
        elif context_depth == 'Team Wide':
            # Get all team projects except current
            projects = self.api.get_team_projects(team_id)
            for proj in projects:
                if proj.name != project_id:
                    # Get latest discussions from each project
                    discussions = self.api.get_project_discussions(proj.name, limit=chat_memory)
                    
                    for disc in discussions:
                        related_discussions.append({
                            'type': 'discussion',
                            'title': disc.get('title', ''),
                            'content': disc.get('content', ''),
                            'author': disc.get('owner', ''),
                            'timestamp': disc.get('creation', ''),
                            'modified': disc.get('modified', ''),
                            'project': proj.name
                        })
                        
                        # Get messages from related discussions
                        disc_messages = self.api.get_discussion_comments(disc.get('name'), limit=chat_memory)
                        for msg in disc_messages:
                            related_messages.append({
                                'discussion_id': disc.get('name'),
                                'discussion_title': disc.get('title', ''),
                                'project': proj.name,
                                'author': msg.get('owner', ''),
                                'content': msg.get('content', ''),
                                'timestamp': msg.get('creation', '')
                            })
                    
                    # Get tasks from other projects
                    proj_tasks = self.api.get_project_tasks(proj.name, limit=chat_memory)
                    for task in proj_tasks:
                        related_tasks.append({
                            'id': task.get('id'),
                            'title': task.get('title'),
                            'status': task.get('status'),
                            'assigned_to': task.get('assigned_to'),
                            'project': proj.name
                        })
                    
                    # Get pages from other projects
                    proj_pages = self.api.get_project_pages(proj.name, limit=chat_memory)
                    for page in proj_pages:
                        related_pages.append({
                            'id': page.get('id'),
                            'title': page.get('title'),
                            'content': page.get('content'),
                            'project': proj.name
                        })
        
        return project_pages, related_discussions, related_tasks, related_pages, related_messages
    
    def build_tool_call_message(
        self,
        tool_calls: List[Dict[str, Any]],
        author: str,
        timestamp: str
    ) -> Message:
        """Build assistant message with tool calls
        
        Creates a message that will be formatted as:
        {
            'role': 'assistant',
            'content': None,
            'tool_calls': [...]
        }
        
        This matches the OpenAI format for tool call messages.
        """
        return Message(
            content=None,
            tasks=[],
            context={
                'user_metadata': self._build_user_metadata(author, timestamp)
            },
            role='assistant',  # Must be 'assistant' for OpenAI tool calls
            tool_calls=tool_calls
        )
    
    def build_tool_response_message(
        self,
        content: str,
        tool_name: str,
        tool_call_id: str,
        timestamp: str
    ) -> Message:
        """Build tool response message
        
        Creates a message that will be formatted as:
        {
            'role': 'tool',
            'content': <tool response>,
            'name': <tool_name>,
            'tool_call_id': <tool_call_id>
        }
        
        This matches the OpenAI format for tool response messages.
        Content format (HTML/Markdown) is determined by the tool itself.
        """
        author = self.settings.get('default_user', '')
        return Message(
            content=content,
            tasks=[],
            context={
                'user_metadata': self._build_user_metadata(author, timestamp)
            },
            role='tool',  # Must be 'tool' for OpenAI tool responses
            tool_name=tool_name,
            tool_call_id=tool_call_id
        )
    
    def _is_agent_user(self, user_id: str) -> bool:
        """Check if user is an agent"""
        return user_id == self.settings.get('default_user')
    
    def _build_user_metadata(self, author: str, timestamp: str) -> Dict[str, Any]:
        """Build user metadata including author and timestamp"""
        # Get user info from API
        user_info = self.api.get_user(author)
        
        return {
            'author': author,
            'timestamp': timestamp,
            'full_name': user_info.get('full_name', ''),
            'email': user_info.get('email', '')
        }
    

    
