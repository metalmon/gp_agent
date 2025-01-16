"""
Registry for managing and executing tools.
Handles tool registration, schema validation and execution.
"""

from typing import Dict, List, Any, Optional, Type
from .tool import BaseTool
from ...utils.logging import log_debug


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self, schema_type: str = "OpenAI"):
        """Initialize registry with specific schema type"""
        self.schema_type = schema_type  
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register new tool and validate schema compatibility"""
        if tool.name in self.tools:
            raise ValueError(f"Tool {tool.name} is already registered")
            
        # Validate schema support
        try:
            tool.get_schema("OpenAI")
        except (NotImplementedError, ValueError) as e:
            raise ValueError(
                f"Tool {tool.name} does not support OpenAI schema: {str(e)}"
            )
            
        self.tools[tool.name] = tool
    
    def clear(self) -> None:
        """Clear all registered tools"""
        self.tools.clear()
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas of all registered tools in OpenAI format"""
        return [
            tool.get_schema("OpenAI")
            for tool in self.tools.values()
        ]
    
    def get_tools(self) -> Dict[str, Type[BaseTool]]:
        """Get dictionary of available tools
        
        Returns:
            Dictionary mapping tool names to their classes
        """
        return {name: type(tool) for name, tool in self.tools.items()}
    
    def execute_tool(
        self,
        call_data: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute tool call with provided data
        
        Args:
            call_data: Tool call data in standardized format with name and arguments
            settings: Optional settings dictionary with API credentials and other settings
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found or parameters invalid
            Exception: If execution fails
        """
        # Extract tool name
        tool_name = call_data.get("name")
        if not tool_name:
            log_debug("Tool name not found in call data")
            raise ValueError("Tool name not found in call data")
            
        # Get and validate tool
        tool = self.tools.get(tool_name)
        if not tool:
            log_debug(f"Tool {tool_name} not found in registry")
            return None
            
        # Parse parameters and execute
        params = call_data.get("arguments", {})
        log_debug(f"Executing {tool_name} with params: {params}")
        result = tool.execute(params, settings=settings)
        log_debug(f"Raw result from {tool_name}: {result}")
        log_debug(f"Result type: {type(result)}")
        
        return result