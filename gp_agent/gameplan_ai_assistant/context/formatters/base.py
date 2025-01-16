from typing import Dict, List, Any
from abc import abstractmethod
from ..base import Message, SystemContext, BaseContextFormatter
import html2text
import markdown
import re
from bs4 import BeautifulSoup
import json

class BaseMessageFormatter(BaseContextFormatter):
    """Base message formatter implementation"""
    
    def __init__(self):
        self.html2text = html2text.HTML2Text()
        self.html2text.body_width = 0  # Don't wrap lines
        
    def format_system_context(self, context: SystemContext) -> Dict[str, Any]:
        """Format system context into message format for API"""
        # Create a Message object with the formatted system prompt
        message = Message(
            content=self.format_system_prompt(context),
            tasks=[],
            context={},
            role='system'
        )
        # Use the standard message formatter for consistency
        return self.format_message(message)
        
    def format_message(self, message: Message) -> Dict[str, Any]:
        """Format message into API-specific format"""
        if message.role == 'system':
            return {
                'role': 'system',
                'content': message.content
            }
        return {
            'role': message.role,
            'content': self.format_message_content(message)
        }
        
    def format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format list of messages into API-specific format"""
        return self.format_to_model_messages(messages)
    
    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown format"""
        if not html_content:
            return ""
        try:
            # Convert HTML to markdown
            markdown_text = self.html2text.handle(html_content)
            # Clean up extra newlines
            markdown_text = "\n".join(line for line in markdown_text.splitlines() if line.strip())
            return self._clean_markdown(markdown_text)
        except Exception as e:
            # Fallback to simple replacement if conversion fails
            content = html_content.replace("<p>", "").replace("</p>", "\n")
            content = content.replace("<br>", "\n").replace("<br/>", "\n")
            return content.strip()
    
    def markdown_to_html(self, markdown_content: str) -> str:
        """Convert Markdown to HTML format"""
        if not markdown_content:
            return ""
            
        # Create markdown instance with extensions
        md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'nl2br',           # Convert newlines to <br>
            'sane_lists',      # Better list handling
            'smarty',          # Smart quotes, dashes, etc.
            'attr_list'        # Add HTML attributes to elements
        ])
        
        # Convert markdown to HTML
        html_content = md.convert(markdown_content)
        
        # Parse with BeautifulSoup for cleaning
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ensure code blocks have proper formatting
        for code in soup.find_all('code'):
            # Only wrap in pre if not already in one
            if code.parent.name != 'pre':
                code.wrap(soup.new_tag('pre'))
                # Add appropriate class for syntax highlighting
                if 'class' in code.attrs:
                    code.parent['class'] = code['class']
        
        # Ensure lists are properly formatted
        for ul in soup.find_all(['ul', 'ol']):
            if not ul.parent or ul.parent.name not in ['li', 'ul', 'ol']:
                ul['class'] = ul.get('class', []) + ['list-style-type-disc']
        
        # Clean up empty paragraphs
        for p in soup.find_all('p'):
            if len(p.get_text(strip=True)) == 0:
                p.decompose()
        
        return str(soup)
    
    def _clean_markdown(self, content: str) -> str:
        """Clean up converted markdown content"""
        if not content:
            return ""
            
        # Split into lines and clean each line
        lines = []
        in_code_block = False
        code_block_lines = []
        
        for line in content.split('\n'):
            # Handle code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    code_block_lines.append(line.strip())
                    lines.append('\n'.join(code_block_lines))
                    code_block_lines = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    code_block_lines = [line.strip()]
            elif in_code_block:
                # Inside code block
                code_block_lines.append(line.strip())
            else:
                # Normal line
                cleaned = line.strip()
                if cleaned:
                    # Fix list formatting
                    if cleaned.startswith(('- ', '* ', '+ ', '1. ')):
                        indent = len(line) - len(line.lstrip())
                        cleaned = ' ' * indent + cleaned
                    lines.append(cleaned)
        
        # Join lines
        content = '\n'.join(lines)
        
        # Fix formatting
        content = re.sub(r'\n{3,}', '\n\n', content)  # Remove multiple empty lines
        content = re.sub(r'\[([^\]]+)\]\s+\(([^)]+)\)', r'[\1](\2)', content)  # Fix link spacing
        content = re.sub(r'!\[([^\]]*)\]\s+\(([^)]+)\)', r'![\1](\2)', content)  # Fix image spacing
        content = re.sub(r'(?m)^>\s+', '> ', content)  # Fix blockquote spacing
        content = re.sub(r'`\s+([^`]+)\s+`', r'`\1`', content)  # Fix inline code spacing
        content = re.sub(r'\|\s+([^|]+)\s+\|', r'|\1|', content)  # Fix table spacing
        content = re.sub(r'<!--[\s\S]*?-->', '', content)  # Remove HTML comments
        content = re.sub(r'\[([^\]]+)\]\(\s*\)', r'\1', content)  # Remove empty links
        content = re.sub(r'!\[([^\]]*)\]\(\s*\)', '', content)  # Remove empty images
        
        return content.strip()
    
    @abstractmethod
    def format_to_model_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format messages for sending to the model"""
        pass
    
    @abstractmethod
    def parse_model_response(self, response: Dict[str, Any]) -> Message:
        """Parse model response into a Message object"""
        pass 

    def format_system_prompt(self, context: SystemContext) -> str:
        """Format system prompt from SystemContext
        
        Structure:
        1. Base instructions
        2. Project context:
           - Project/discussion metadata
           - Unassigned tasks
           - Tasks from non-participating users
           - Project pages
        3. Related content:
           - Discussions
           - Tasks
           - Pages
           - Messages
        """
        sections = []
        
        # Base instructions
        sections.append(f"# Instructions\n{context.base_instructions}\n")
        
        # Project context
        sections.append("# Project Context\n")
        
        # Add metadata section
        if context.metadata:
            sections.append("## Project Metadata\n")
            for key, value in context.metadata.items():
                if isinstance(value, list):
                    sections.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    sections.append(f"{key}: {value}")
            sections.append("")
        
        if context.unassigned_tasks:
            sections.append("## Unassigned Tasks (Not Assigned to Any User)\n")
            for task in context.unassigned_tasks:
                sections.append(f"- {task['title']}")
                if task.get('status'):
                    sections.append(f"  Status: {task['status']}")
                if task.get('description'):
                    desc = self.html_to_markdown(task['description'])
                    sections.append(f"  Description: {desc}")
                sections.append("")
                
        if context.pages:
            sections.append("## Pages\n")
            for page in context.pages:
                sections.append(f"### {page['title']}")
                if page.get('content'):
                    content = self.html_to_markdown(page['content'])
                    sections.append(content)
                sections.append("")
                
        # Related content
        if any([context.related_discussions, context.related_tasks, 
                context.related_pages, context.related_messages]):
            sections.append("# Related Content\n")
            
            if context.related_discussions:
                sections.append("## Discussions\n")
                for disc in context.related_discussions:
                    sections.append(f"### {disc['title']}")
                    if disc.get('content'):
                        content = self.html_to_markdown(disc['content'])
                        sections.append(content)
                    sections.append("")
                    
            if context.related_tasks:
                sections.append("## Tasks from Other Projects\n")
                for task in context.related_tasks:
                    sections.append(f"- {task['title']} ({task.get('project', 'Unknown project')})")
                    if task.get('status'):
                        sections.append(f"  Status: {task['status']}")
                    sections.append("")
                    
            if context.related_pages:
                sections.append("## Pages from Other Projects\n")
                for page in context.related_pages:
                    sections.append(f"### {page['title']} ({page.get('project', 'Unknown project')})")
                    if page.get('content'):
                        content = self.html_to_markdown(page['content'])
                        sections.append(content)
                    sections.append("")
                    
            if context.related_messages:
                sections.append("## Related Messages\n")
                for msg in context.related_messages:
                    if msg.get('content'):
                        content = self.html_to_markdown(msg['content'])
                        sections.append(f"From {msg.get('author', 'Unknown')} in {msg.get('discussion_title', 'Unknown discussion')}:")
                        sections.append(content)
                        sections.append("")
        
        return "\n".join(sections)

    def format_message_content(self, message: Message) -> str:
        """Format message content
        
        Structure:
        1. Tool instructions (if present)
        2. User metadata:
           - Author
           - Timestamp
           - Full name
           - Email
           - User tasks
        3. Message content (converted from HTML to Markdown)
        """
        sections = []
        
        # Tool instructions if present
        if message.context.get('tool_instructions'):
            sections.append("# Tool Instructions")
            sections.append(message.context['tool_instructions'])
            sections.append("")
        
        # User metadata
        if message.context.get('user_metadata'):
            metadata = message.context['user_metadata']
            sections.append("# User Info")
            sections.append(f"Author: {metadata.get('author', 'Unknown')}")
            sections.append(f"Full Name: {metadata.get('full_name', 'Unknown')}")
            sections.append(f"Email: {metadata.get('email', 'Unknown')}")
            sections.append(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
            sections.append("")
            
        # Project metadata
        if message.context.get('project_metadata'):
            metadata = message.context['project_metadata']
            sections.append("# Project Info")
            for key, value in metadata.items():
                if isinstance(value, list):
                    sections.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    sections.append(f"{key}: {value}")
            sections.append("")

        # User tasks
        if message.tasks:
            sections.append("# User Tasks")
            for task in message.tasks:
                sections.append(f"- {task['title']}")
                if task.get('status'):
                    sections.append(f"  Status: {task['status']}")
                sections.append("")
        
        # Message content
        if message.content:
            sections.append("# Message")
            content = self.html_to_markdown(message.content)
            sections.append(content)
        
        return "\n".join(sections) 

    def format_content(self, content: str) -> str:
        """Format plain text content to HTML
        
        Args:
            content: Plain text content in markdown format
            
        Returns:
            Formatted HTML content
        """

        return self.markdown_to_html(content)

    def clean_service_headers(self, content: str) -> str:
        """Clean service headers from content while preserving actual message content
        
        If content has two #Message headers, returns everything after the second one.
        Otherwise returns the original content.
        
        Args:
            content: Raw message content
            
        Returns:
            Cleaned content with service headers removed
        """
        if not content:
            return ""
            
        # Find all #Message headers using regex, case insensitive
        pattern = r'#\s*[Mm]essage\b'
        matches = list(re.finditer(pattern, content))
        
        # If we found exactly two message headers, take everything after the second one
        if len(matches) == 2:
            # Get position after second header
            start_pos = matches[1].end()
            # Find first non-whitespace character after header
            content_match = re.search(r'\S', content[start_pos:])
            if content_match:
                start_pos = start_pos + content_match.start()
            cleaned = content[start_pos:]
            # Clean up extra whitespace
            cleaned = re.sub(r'\s{3,}', '\n\n', cleaned)
            return cleaned.strip()
            
        # Otherwise return original content
        return content 

    def format_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Format tool call data to standardized format
        
        Args:
            tool_call: Raw tool call data from LLM response
            
        Returns:
            Formatted tool call data with standardized structure:
            {
                "name": str,
                "arguments": str  # JSON string
            }
        """
        # Extract tool name and arguments based on schema
        if "function" in tool_call:
            # OpenAI format
            tool_name = tool_call["function"].get("name", "")
            arguments = tool_call["function"].get("arguments", "{}")
        else:
            # Direct format
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", "{}")
            
            # For Anthropic format, rename parameters to arguments
            if "parameters" in tool_call:
                arguments = tool_call["parameters"]
            
        # Convert arguments to string if they're a dict
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)
            
        return {
            "name": tool_name,
            "arguments": arguments
        } 