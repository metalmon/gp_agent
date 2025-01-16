from typing import Dict, Any, Type, Tuple
from .base import BaseContextBuilder, BaseContextFormatter
from .builder import GameplanContextBuilder, SimpleContextBuilder
from .formatters.openai import OpenAIContextFormatter
from .formatters.anthropic import AnthropicContextFormatter
from ..gameplan_api import GameplanAPI
import frappe


class ContextFactory:
    """Factory for creating context builders and formatters"""
    
    _builders = {
        'default': GameplanContextBuilder,
        'simple': SimpleContextBuilder
    }
    
    _formatters = {
        'openai': OpenAIContextFormatter,
        'anthropic': AnthropicContextFormatter
    }
    
    @classmethod
    def register_builder(cls, name: str, builder_class: Type[BaseContextBuilder]):
        """Register a new context builder implementation
        
        Args:
            name: Builder name
            builder_class: Builder class
        """
        cls._builders[name] = builder_class
    
    @classmethod
    def register_formatter(cls, schema: str, formatter_class: Type[BaseContextFormatter]):
        """Register a new context formatter implementation
        
        Args:
            schema: API schema name (e.g. 'openai', 'anthropic')
            formatter_class: Formatter class
        """
        cls._formatters[schema] = formatter_class
    
    @classmethod
    def create(cls, settings: Dict[str, Any]) -> Tuple[BaseContextBuilder, BaseContextFormatter]:
        """Create a context builder and formatter based on settings
        
        Args:
            settings: Settings dictionary containing:
                - context_builder: Builder type (default: 'default')
                - api_schema: API schema to use (default: 'openai')
                - other builder-specific settings
        
        Returns:
            Tuple of (builder, formatter)
        """
        builder_type = settings.get('context_builder', 'default')
        api_schema = settings.get('api_schema', 'openai').lower()
        
        # Get builder class
        if builder_type not in cls._builders:
            raise ValueError(f"Unknown context builder type: {builder_type}")
        builder_class = cls._builders[builder_type]
        
        # Get formatter class
        if api_schema not in cls._formatters:
            raise ValueError(f"Unknown API schema: {api_schema}")
        formatter_class = cls._formatters[api_schema]
        
        # Create formatter instance first
        formatter = formatter_class()
        
        # Create builder instance with formatter
        if builder_class == GameplanContextBuilder:
            # Only validate user and create GameplanAPI for GameplanContextBuilder
            default_user = settings.get('default_user')
            if not default_user or not frappe.db.exists("User", default_user):
                raise ValueError(f"User {default_user} does not exist")
            
            api = GameplanAPI.get_instance() or GameplanAPI(default_user)
            builder = builder_class(api, settings, formatter)
        else:
            builder = builder_class(settings, formatter)
        
        return builder, formatter 