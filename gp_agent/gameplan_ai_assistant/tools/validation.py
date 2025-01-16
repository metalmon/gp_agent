from typing import Dict, List, Optional, Type, Tuple, Any
import json
from dataclasses import dataclass
from .base import BaseTool
from .registry import get_available_tools
from ..utils.logging import log_debug

@dataclass
class ValidationError:
    """Represents a validation error with type, message and optional details"""
    error_type: str
    message: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details
        }

@dataclass 
class ToolCallValidationResult:
    """Result of tool call validation including any fixes applied"""
    is_valid: bool
    errors: List[ValidationError]
    valid_calls: List[Dict] = None  # List of all valid tool calls
    fix_strategy: Optional[str] = None
    fix_details: Optional[Dict] = None
    metrics: Dict = None

    def __post_init__(self):
        if self.valid_calls is None:
            self.valid_calls = []
            
        if self.metrics is None:
            self.metrics = {}
            
        # Always set validation status and other core metrics
        self.metrics.update({
            "validation_status": "Valid" if self.is_valid else "Invalid" if not self.valid_calls else "Fixed",
            "error_types": [e.error_type for e in self.errors],
            "fix_strategy": self.fix_strategy,
            "has_fixes": bool(self.valid_calls),
            "valid_calls_count": len(self.valid_calls),
            "strategy": self.fix_strategy or "split_and_match"  # Ensure strategy is always set
        })
        
        # Add count property to valid_calls list
        self.valid_calls = ValidCallsList(self.valid_calls)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "valid_calls": self.valid_calls,
            "fix_strategy": self.fix_strategy,
            "fix_details": self.fix_details,
            "metrics": self.metrics
        }

class ValidCallsList(list):
    """List subclass that adds a count property"""
    @property
    def count(self) -> int:
        return len(self)

class ToolNameSplitter:
    """Splits concatenated tool names into valid tools"""
    
    def __init__(self, available_tools: Dict[str, Any]):
        """Initialize splitter with available tools"""
        self.available_tools = available_tools
        
    def split(self, tool_name: str) -> Dict[str, Any]:
        """Split concatenated tool names into valid tools
        
        Args:
            tool_name: Tool name to split
            
        Returns:
            Dictionary containing:
            - valid_tools: List of valid tool names found
            - metrics: Dictionary with splitting metrics
        """
        metrics = {
            "original": tool_name,
            "debug_steps": []
        }
        
        if not tool_name:
            metrics["debug_steps"].append("Empty tool name")
            return {"valid_tools": [], "metrics": metrics}
            
        # Find all valid tool names
        valid_tools = []
        remaining = tool_name
        
        while remaining:
            found = False
            metrics["debug_steps"].append(f"Checking remaining: {remaining}")
            
            # Try each tool name
            for name in self.available_tools.keys():
                if remaining.startswith(name):
                    valid_tools.append(name)
                    remaining = remaining[len(name):]
                    found = True
                    metrics["debug_steps"].append(f"Found tool: {name}")
                    break
                    
            if not found:
                # Try finding tool name at any position
                for name in self.available_tools.keys():
                    pos = remaining.find(name)
                    if pos > 0:
                        valid_tools.append(name)
                        remaining = remaining[pos + len(name):]
                        found = True
                        metrics["debug_steps"].append(f"Found tool at position {pos}: {name}")
                        break
                        
            if not found:
                metrics["debug_steps"].append(f"No more tools found in: {remaining}")
                break
                
        metrics["num_tools"] = len(valid_tools)
        return {
            "valid_tools": valid_tools,
            "metrics": metrics
        }

class ArgumentsSplitter:
    """Handles splitting of concatenated JSON arguments into separate argument objects"""
    
    def split(self, args_str: str) -> Tuple[List[Dict], Dict]:
        """Split concatenated JSON arguments into separate objects
        
        Args:
            args_str: String containing one or more JSON objects
            
        Returns:
            Tuple of (list of parsed argument dictionaries, metrics about the split)
        """
        metrics = {
            "original_args": args_str,
            "split_strategy": None,
            "args_count": 0,
            "invalid_args": [],
            "debug_steps": []  # For tracking the splitting process
        }
        
        try:
            # First try parsing as single JSON
            single_args = json.loads(args_str)
            if isinstance(single_args, dict):
                metrics["split_strategy"] = "single_json"
                metrics["args_count"] = 1
                metrics["debug_steps"].append({
                    "strategy": "single_json",
                    "result": "success"
                })
                return [single_args], metrics
        except json.JSONDecodeError as e:
            metrics["debug_steps"].append({
                "strategy": "single_json",
                "result": "failed",
                "error": str(e)
            })
            
        # Try splitting on }{ pattern
        try:
            # Find all JSON object boundaries
            objects = []
            start = 0
            depth = 0
            current = ""
            
            for i, char in enumerate(args_str):
                current += char
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        # Found complete JSON object
                        try:
                            obj = json.loads(current)
                            if isinstance(obj, dict):
                                objects.append(obj)
                                metrics["debug_steps"].append({
                                    "strategy": "depth_tracking",
                                    "position": i,
                                    "object": current,
                                    "result": "valid_json"
                                })
                        except json.JSONDecodeError as e:
                            metrics["invalid_args"].append(current)
                            metrics["debug_steps"].append({
                                "strategy": "depth_tracking",
                                "position": i,
                                "object": current,
                                "result": "invalid_json",
                                "error": str(e)
                            })
                        current = ""
                        start = i + 1
            
            if objects:
                metrics["split_strategy"] = "depth_tracking"
                metrics["args_count"] = len(objects)
                return objects, metrics
                
        except Exception as e:
            metrics["debug_steps"].append({
                "strategy": "depth_tracking",
                "result": "failed",
                "error": str(e)
            })
            
        # No valid split found
        metrics["split_strategy"] = "failed"
        return [], metrics

class ToolCallMatcher:
    """Matches tools with their arguments"""
    
    def __init__(self, available_tools: Dict[str, Any]):
        """Initialize matcher with available tools"""
        self.available_tools = available_tools
        
    def match(self, tools: List[str], arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Match tools with their arguments
        
        Args:
            tools: List of tool names
            arguments: List of argument dictionaries
            
        Returns:
            Dictionary containing:
            - matches: List of (tool_name, arguments) tuples
            - metrics: Dictionary with matching metrics
        """
        metrics = {
            "num_tools": len(tools),
            "num_arguments": len(arguments),
            "debug_steps": []
        }
        
        # Simple position-based matching if counts match
        if len(tools) == len(arguments):
            metrics["debug_steps"].append("Using position-based matching")
            matches = list(zip(tools, arguments))
            metrics["match_type"] = "position"
            return {"matches": matches, "metrics": metrics}
            
        # Try to match based on required parameters
        metrics["debug_steps"].append("Using parameter-based matching")
        matches = []
        remaining_tools = tools.copy()
        remaining_args = arguments.copy()
        
        for args in remaining_args[:]:
            best_match = None
            best_score = 0
            
            for tool in remaining_tools[:]:
                # Get tool schema
                tool_class = self.available_tools[tool]()
                schema = tool_class.get_parameters()
                required = set(schema.get("required", []))
                optional = set(schema.get("properties", {}).keys()) - required
                
                # Calculate match score
                provided = set(args.keys())
                req_match = len(required & provided)
                opt_match = len(optional & provided)
                score = req_match * 2 + opt_match
                
                if score > best_score and req_match == len(required):
                    best_score = score
                    best_match = tool
                    
            if best_match:
                matches.append((best_match, args))
                remaining_tools.remove(best_match)
                remaining_args.remove(args)
                metrics["debug_steps"].append(f"Matched {best_match} with score {best_score}")
                
        metrics["match_type"] = "parameter"
        metrics["num_matches"] = len(matches)
        return {"matches": matches, "metrics": metrics}

class ToolCallValidator:
    """Validates and fixes tool calls"""
    
    def __init__(self, available_tools: Dict[str, Any]):
        """Initialize validator with available tools"""
        self.available_tools = available_tools
        self.splitter = ToolNameSplitter(available_tools)
        self.matcher = ToolCallMatcher(available_tools)

    def validate_call(self, tool_name: str, arguments: str, tool_id: str) -> ToolCallValidationResult:
        """
        Validates a tool call and attempts to fix it if invalid
        
        Args:
            tool_name: Name of the tool to validate
            arguments: Arguments string or dictionary
            tool_id: ID of the tool call
            
        Returns:
            ToolCallValidationResult with validation status and fixes
        """
        metrics = {
            "original_tool_name": tool_name,
            "original_arguments": arguments,
            "debug_steps": []
        }
        
        try:
            # Convert arguments to string if they're a dict
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)
                
            # Split concatenated tool names
            split_result = self.splitter.split(tool_name)
            metrics["split_result"] = split_result
            
            if not split_result["valid_tools"]:
                return ToolCallValidationResult(
                    is_valid=False,
                    valid_calls=[],
                    errors=[ValidationError(
                        error_type="invalid_tool",
                        message=f"No valid tools found in: {tool_name}"
                    )],
                    metrics=metrics
                )
                
            # Split concatenated arguments
            args_metrics = {"debug_steps": []}
            args = []
            
            try:
                # Try parsing as single JSON first
                args = [json.loads(arguments)]
                args_metrics["debug_steps"].append("Parsed single JSON successfully")
            except json.JSONDecodeError:
                # If that fails, try splitting concatenated JSONs
                current = ""
                depth = 0
                
                for char in arguments:
                    current += char
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                args.append(json.loads(current))
                                current = ""
                            except json.JSONDecodeError:
                                args_metrics["debug_steps"].append(f"Failed to parse JSON: {current}")
                
            args_metrics["num_arguments"] = len(args)
            metrics["args_split"] = args_metrics
            
            if not args:
                return ToolCallValidationResult(
                    is_valid=False,
                    valid_calls=[],
                    errors=[ValidationError(
                error_type="invalid_arguments",
                        message=f"No valid JSON arguments found in: {arguments}"
                    )],
                    metrics=metrics
                )
                
            # Match tools with arguments
            match_result = self.matcher.match(split_result["valid_tools"], args)
            metrics["match_result"] = match_result
            
            if not match_result["matches"]:
                return ToolCallValidationResult(
                    is_valid=False,
                    valid_calls=[],
                    errors=[ValidationError(
                        error_type="no_matches",
                        message="Could not match tools with arguments"
                    )],
                    metrics=metrics
                )
                
            # Create valid tool calls
            valid_calls = []
            for i, (tool, args) in enumerate(match_result["matches"]):
                valid_calls.append({
                    "id": f"{tool_id}_{i}",
                    "name": tool,
                    "arguments": args
                })
                
            return ToolCallValidationResult(
                is_valid=True,
                valid_calls=valid_calls,
                errors=[],
                metrics=metrics
            )
            
        except Exception as e:
            metrics["error"] = str(e)
        return ToolCallValidationResult(
                is_valid=False,
                valid_calls=[],
                errors=[ValidationError(
                    error_type="validation_error", 
                    message=f"Error validating tool call: {str(e)}"
                )],
                metrics=metrics
            )

def validate_tool_call(tool_call: Dict[str, Any], available_tools: Dict[str, Any]) -> ToolCallValidationResult:
    """Validate a tool call and fix any issues
        
        Args:
        tool_call: Tool call to validate
        available_tools: Dictionary of available tools
            
        Returns:
        ToolCallValidationResult with validation status and any fixes
    """
    try:
        # Extract tool name and arguments
        function_data = tool_call.get("function", {})
        tool_name = function_data.get("name", "")
        arguments = function_data.get("arguments", "{}")
        tool_id = tool_call.get("id", "tool_0")
        
        # Initialize metrics
        metrics = {
            "original_tool_name": tool_name,
            "original_arguments": arguments,
            "debug_steps": []
        }
        
        # Find all valid tool names in the concatenated string
        validator = ToolCallValidator(available_tools)
        result = validator.validate_call(tool_name, arguments, tool_id)
        
        if not result.is_valid:
            return result
            
        # Update tool IDs to be unique
        for i, call in enumerate(result.valid_calls):
            call["id"] = f"{tool_id}_{i}"
            
        return result
            
    except Exception as e:
        return ToolCallValidationResult(
            is_valid=False,
            valid_calls=[],
            errors=[ValidationError(
                error_type="validation_error",
                message=f"Error validating tool call: {str(e)}"
            )],
            metrics=metrics
        ) 