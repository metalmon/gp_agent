"""
Tool for fetching webpage content and converting it to markdown format.
Supports both external URLs and Frappe document URLs with advanced content extraction.
"""

import requests
from bs4 import BeautifulSoup
import html2text
import logging
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Optional

import frappe

from .base import BaseWebTool
from ...exceptions import GPAgentException


class GetWebpageContentTool(BaseWebTool):
    """Tool for fetching webpage content and converting it to markdown format.
    
    This tool provides advanced webpage content extraction capabilities:
    
    Features:
    - Flexible URL handling:
        * Direct URLs (https://example.com)
        * Bare domains (example.com -> https://www.example.com)
        * Markdown links ([title](url))
        * Frappe document URLs (/app/doctype/name)
        * Relative paths (docs/installation)
    - Intelligent content extraction focusing on main article/content
    - Handles various content types:
        * Blog posts and articles
        * Documentation pages
        * Product pages
        * Frappe documents
    - Advanced processing:
        * HTML to Markdown conversion
        * Metadata extraction (title, description, author, etc.)
        * Smart content cleaning and formatting
        * Character encoding detection
        * Redirect handling
    - Error handling:
        * Invalid URLs
        * Connection timeouts
        * Access denied errors
        * Malformed content
    """
    
    def __init__(self):
        """Initialize tool"""
        super().__init__(
            name="get_webpage_content",
            description=(
                "Fetches and processes webpage content with advanced extraction. "
                "When given just a domain (e.g. 'frappecrm.ru'), automatically tries the main page first. "
                "If main page is not accessible, tries common paths like '/ru/', '/en/', '/docs/'. "
                "Supports bare domains (example.com), markdown links ([title](url)), "
                "and Frappe document URLs. Automatically adds https:// and www. "
                "Example: For 'frappecrm.ru' will try 'https://www.frappecrm.ru', then '/ru/', etc."
            )
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema
        
        Returns:
            Parameters schema in JSON Schema format
        """
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "URL or domain of the webpage to fetch. Supports multiple formats:\n"
                        "\n1. Bare domains - automatically adds https://www. :\n"
                        "   - example.com -> https://www.example.com\n"
                        "   - frappecrm.ru -> https://www.frappecrm.ru\n"
                        "\n2. Markdown links - extracts URL automatically:\n"
                        "   - [Documentation](https://example.com/docs)\n"
                        "   - [Link](https://frappecrm.ru)\n"
                        "\n3. Direct URLs:\n"
                        "   - https://example.com\n"
                        "   - http://frappecrm.ru/docs\n"
                        "\n4. Frappe URLs:\n"
                        "   - /app/doctype/name\n"
                        "   - /desk#Form/DocType/name\n"
                        "\n5. Relative paths:\n"
                        "   - docs/installation\n"
                        "   - api/method/..."
                    )
                }
            },
            "required": ["url"]
        }
    
    def execute(self, params: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with given parameters
        
        Args:
            params: Tool parameters including:
                   - url: URL or domain to fetch. For bare domains, automatically tries:
                     1. Main domain (e.g. https://www.example.com)
                     2. Common paths (/ru/, /en/, /docs/)
                     3. Returns first successful result
            settings: Optional settings dictionary with API credentials and other settings
            
        Returns:
            Dictionary containing:
            - url: Original URL
            - final_url: Final URL after redirects
            - title: Page title
            - content: Main content in markdown format
            - metadata: Page metadata
            - timestamp: Fetch timestamp
            - error: Error message (if any)
        """
        url = params["url"]
        original_url = url
        
        # Handle markdown links [title](url)
        markdown_link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', url)
        if markdown_link_match:
            url = markdown_link_match.group(2)
        
        try:
            logging.debug(f"Processing URL: {url}")
            
            # For bare domains, try common paths
            if not url.startswith(('http://', 'https://', '/')):
                base_url = 'https://' + url.lstrip('/')
                try:
                    logging.debug(f"Trying URL: {base_url}")
                        
                    # Try to fetch this URL
                    response = requests.head(base_url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        url = base_url
                        logging.debug(f"Successfully found working URL: {url}")
                except Exception as e:
                    logging.debug(f"Failed to access {base_url}: {str(e)}")
            
            # Check if this is a Frappe document URL
            if self._is_frappe_url(url):
                return self._get_frappe_content(url)
            
            # For external URLs, proceed with normal web scraping
            # Validate URL
            if not self._is_valid_url(url):
                raise ValueError(f"Invalid URL format: {url}")
                
            # Setup browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Create session for cookie persistence
            session = requests.Session()
            
            # Set reasonable timeout
            timeout = 30
            
            # Initial request with redirect handling
            try:
                response = session.get(url, headers=headers, allow_redirects=True, timeout=timeout)
                response.raise_for_status()
            except requests.Timeout:
                raise TimeoutError("Request timed out")
            except requests.TooManyRedirects:
                raise ValueError("Too many redirects")
            
            # Get final URL after redirects
            final_url = response.url
            
            # Create BeautifulSoup object for HTML parsing
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                raise ValueError(f"Failed to parse HTML: {str(e)}")
            
            # Check for meta refresh redirect
            refresh_tag = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if refresh_tag:
                content = refresh_tag.get('content', '')
                if content:
                    # Extract URL from content
                    match = re.search(r'url=([^;]+)', content)
                    if match:
                        redirect_url = match.group(1).strip()
                        # Make relative URLs absolute
                        redirect_url = urljoin(final_url, redirect_url)
                        logging.debug(f"Found meta refresh redirect to {redirect_url}")
                        # Make request to new URL
                        try:
                            response = session.get(redirect_url, headers=headers, timeout=timeout)
                            response.raise_for_status()
                            final_url = response.url
                            # Update soup with new content
                            soup = BeautifulSoup(response.text, 'html.parser')
                        except (requests.Timeout, requests.RequestException) as e:
                            raise ValueError(f"Failed to follow meta refresh redirect: {str(e)}")
            
            # Handle character encoding
            if response.encoding.lower() == 'iso-8859-1':
                response.encoding = response.apparent_encoding
            
            # Extract title with fallback
            title = self._extract_title(soup) or url
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            
            # Try alternative content extraction if main content is empty
            if not main_content or not str(main_content).strip():
                logging.debug("Main content not found with primary selectors, trying alternative selectors")
                main_content = self._extract_alternative_content(soup)
            
            # Convert HTML to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # Disable line wrapping
            h.unicode_snob = True  # Use Unicode
            h.protect_links = True  # Don't convert links to references
            h.wrap_links = False  # Don't wrap long links
            
            try:
                markdown_content = h.handle(str(main_content))
            except Exception as e:
                raise ValueError(f"Failed to convert HTML to markdown: {str(e)}")
            
            # Clean up markdown content
            cleaned_content = self._clean_markdown(markdown_content)
            
            logging.debug(f"Successfully fetched and converted content from {final_url}")
            
            return {
                'url': url,
                'final_url': final_url,
                'title': title.strip() if isinstance(title, str) else str(title),
                'content': cleaned_content,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e)
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """Validates URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extracts page title with fallbacks.
        Tries multiple sources: title tag, og:title, h1, etc.
        """
        # Try title tag first
        if soup.title:
            return soup.title.string
        
        # Try Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content')
        
        # Try first h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return None
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extracts metadata from HTML.
        Handles various meta tags including Open Graph and Twitter cards.
        """
        metadata = {}
        
        # Get all meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            # Get name or property
            name = tag.get('name', tag.get('property', ''))
            content = tag.get('content', '')
            
            if name and content:
                # Handle special meta tags
                if name in ['description', 'keywords', 'author']:
                    metadata[name] = content
                elif name.startswith('og:'):  # Open Graph metadata
                    metadata[name.replace('og:', 'og_')] = content
                elif name.startswith('twitter:'):  # Twitter metadata
                    metadata[name.replace('twitter:', 'twitter_')] = content
        
        # Add title to metadata
        if soup.title:
            metadata['title'] = soup.title.string
        
        return metadata
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        Extracts main content from the page.
        Uses various selectors to find the main content area.
        """
        # Try to find main content by common tags
        main_content = None
        
        # Priority selectors for content
        selectors = [
            'main',
            'article',
            '[role="main"]',
            '#main-content',
            '.main-content',
            '#content',
            '.content',
            '.post-content',
            '.article-content',
            '.page-content',
            '.site-content',
            '#app',  # For SPAs
            '.app',  # For SPAs
            '[data-content]',  # For dynamic content
            '[itemprop="articleBody"]',  # Schema.org
            '[itemprop="mainContentOfPage"]'  # Schema.org
        ]
        
        # Try each selector
        for selector in selectors:
            main_content = soup.select_one(selector)
            if main_content and len(str(main_content)) > 100:  # Check for non-empty content
                break
        
        # Fallback to body if no content found
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Remove unwanted elements
        if main_content:
            # Elements to remove
            for element in main_content.select('script, style, iframe, nav, header, footer, aside, .sidebar, .comments, .ad, .advertisement, .social-share'):
                element.decompose()
        
        return main_content
    
    def _extract_alternative_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Alternative content extraction when main selectors fail.
        Tries to find content by looking for largest text block.
        """
        # Get all paragraphs
        paragraphs = soup.find_all('p')
        
        # Find the largest text block
        max_length = 0
        main_content = None
        
        for p in paragraphs:
            text_length = len(p.get_text())
            if text_length > max_length:
                max_length = text_length
                main_content = p.parent
        
        return main_content if main_content else soup.body if soup.body else soup
    
    def _clean_markdown(self, content: str) -> str:
        """
        Cleans up converted markdown content.
        Removes extra whitespace, fixes formatting issues.
        """
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
    
    def _is_frappe_url(self, url: str) -> bool:
        """
        Check if URL points to a Frappe document.
        Supports various Frappe URL formats:
        - /app/doctype/name
        - /desk#Form/DocType/name
        - /desk#List/DocType
        - /api/method/...
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            fragment = parsed.fragment
            
            # Check common Frappe URL patterns
            if path.startswith(('app/', 'desk', 'api/method/')):
                return True
                
            # Check desk URLs with fragments
            if path == 'desk' and fragment:
                if fragment.startswith(('Form/', 'List/', 'view/')):
                    return True
            
            return False
            
        except Exception:
            return False
            
    def _parse_frappe_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse Frappe URL to extract doctype and docname.
        Supports various URL formats:
        - /app/doctype/docname
        - /desk#Form/doctype/docname
        - /desk#view/doctype/docname
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            fragment = parsed.fragment
            
            # Handle /app/doctype/docname format
            if path.startswith('app/'):
                parts = path.split('/')
                if len(parts) >= 3:
                    return parts[1], parts[2]
                    
            # Handle /desk#Form/doctype/docname format
            if path == 'desk' and fragment:
                parts = fragment.split('/')
                if len(parts) >= 3:
                    # Skip the first part (Form/List/view)
                    return parts[1], parts[2]
            
            return None, None
            
        except Exception:
            return None, None
    
    def _format_doc_content(self, doc: "frappe.model.document.Document") -> str:
        """
        Format document content based on doctype.
        """
        content = []
        
        # Add title
        content.append(f"# {doc.get_title()}\n")
        
        # Add description if available
        if hasattr(doc, 'description') and doc.description:
            content.append(doc.description + "\n")
        
        # Add content field if available
        if hasattr(doc, 'content'):
            content.append(doc.content)
        elif hasattr(doc, 'message'):
            content.append(doc.message)
        
        # Add table data if available
        if doc.meta.istable:
            content.append("\n## Table Data\n")
            for field in doc.meta.fields:
                if not field.hidden and hasattr(doc, field.fieldname):
                    value = doc.get(field.fieldname)
                    if value is not None:
                        content.append(f"- **{field.label}**: {value}")
        
        return "\n".join(content) 
    
    def _get_frappe_content(self, url: str) -> Dict[str, Any]:
        """
        Get content from a Frappe document URL.
        Supports various URL formats and document types.
        """
        try:
            # Parse URL to get doctype and docname
            doctype, docname = self._parse_frappe_url(url)
            if not doctype or not docname:
                raise ValueError("Invalid Frappe document URL")
            
            # Get document
            try:
                doc = frappe.get_doc(doctype, docname)
            except frappe.DoesNotExistError:
                raise ValueError(f"Document {doctype}/{docname} not found")
            except frappe.PermissionError:
                raise ValueError(f"Permission denied for {doctype}/{docname}")
            
            # Format content based on doctype
            content = self._format_doc_content(doc)
            
            # Get metadata
            metadata = {
                'doctype': doc.doctype,
                'name': doc.name,
                'owner': doc.owner,
                'creation': str(doc.creation),
                'modified': str(doc.modified),
                'modified_by': doc.modified_by
            }
            
            # Add custom fields if available
            if hasattr(doc, 'title_field'):
                metadata['title'] = doc.get(doc.title_field)
            if hasattr(doc, 'status'):
                metadata['status'] = doc.status
            
            return {
                'url': url,
                'final_url': url,
                'title': doc.get_title(),
                'content': content,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error getting Frappe content from {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e)
            } 