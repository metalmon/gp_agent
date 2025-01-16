"""
Base class for page-related tools.
"""

from typing import Dict, Any, Optional, List
from ...gameplan_api import GameplanAPI
from ..base.tool import BaseTool
from abc import ABC, abstractmethod
import json
import html2text
import markdown
import re
from bs4 import BeautifulSoup
from ...utils.logging import log_debug


class BasePageTool(BaseTool):
    """Base class for page management tools"""
    
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.api = GameplanAPI()
        self.html2text = html2text.HTML2Text()
        self.html2text.body_width = 0  # Don't wrap lines
        
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get tool schema for specific format type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            
        Returns:
            Tool schema in requested format
        """
        if schema_type == "OpenAI":
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": self.get_parameters()
                }
            }
        elif schema_type == "Anthropic":
            return {
                "type": "function",
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters()
            }
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")
    
    def parse_call(
        self,
        schema_type: str,
        call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse tool call data based on schema type
        
        Args:
            schema_type: Schema format type (e.g. "OpenAI", "Anthropic", etc.)
            call_data: Raw tool call data to parse
            
        Returns:
            Parsed parameters for tool execution
        """
        if schema_type == "OpenAI":
            arguments = call_data["function"]["arguments"]
            # Parse JSON string if needed
            if isinstance(arguments, str):
                return json.loads(arguments)
            return arguments
        elif schema_type == "Anthropic":
            return call_data["function"]["parameters"]
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema in JSON Schema format
        
        Returns:
            Parameters schema that defines the tool's input format
        """
        pass
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Parsed parameters for tool execution
            
        Returns:
            Tool execution results
        """
        pass 
    
    def format_content(self, content: str, format: str = "html") -> str:
        """Format content between HTML and Markdown formats
        
        Args:
            content: Content to format
            format: Target format ('html' or 'markdown')
            
        Returns:
            Formatted content in requested format
        """
        if format == "html":
            return self.markdown_to_html(content)
        elif format == "markdown":
            return self.html_to_markdown(content)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
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
    
    def get_project_title(self, project_id: str) -> str:
        """Get project title by ID
        
        Args:
            project_id: Project ID to get title for
            
        Returns:
            Project title or empty string if not found
        """
        return self.api.get_project_title(project_id) 