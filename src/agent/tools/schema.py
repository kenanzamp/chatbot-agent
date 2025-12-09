import inspect
from typing import Callable, Dict, Any, get_type_hints, Optional, List, Union
from dataclasses import dataclass
import re


# Python type to JSON Schema type mapping
TYPE_MAP = {
    str: "string",
    int: "integer", 
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


@dataclass
class ToolSchema:
    """Represents a tool's schema for LLM consumption."""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


def parse_docstring(docstring: str) -> Dict[str, str]:
    """
    Parse parameter descriptions from docstring.
    Supports Google and Sphinx styles.
    """
    if not docstring:
        return {}
    
    params = {}
    
    # Google style: "param_name: description" or "param_name (type): description"
    google_pattern = r'^\s*(\w+)(?:\s*\([^)]+\))?:\s*(.+)$'
    
    # Sphinx style: ":param param_name: description"
    sphinx_pattern = r':param\s+(\w+):\s*(.+)'
    
    lines = docstring.split('\n')
    in_args_section = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check for Args: section (Google style)
        if stripped.lower() in ('args:', 'arguments:', 'parameters:'):
            in_args_section = True
            continue
        
        # Check for section end
        if stripped.lower() in ('returns:', 'raises:', 'example:', 'examples:'):
            in_args_section = False
            continue
        
        # Sphinx style
        sphinx_match = re.match(sphinx_pattern, stripped)
        if sphinx_match:
            params[sphinx_match.group(1)] = sphinx_match.group(2).strip()
            continue
        
        # Google style (only in args section)
        if in_args_section:
            google_match = re.match(google_pattern, stripped)
            if google_match:
                params[google_match.group(1)] = google_match.group(2).strip()
    
    return params


def get_json_type(python_type: Any) -> str:
    """Convert Python type to JSON Schema type string."""
    # Handle None type
    if python_type is type(None):
        return "null"
    
    # Handle basic types
    if python_type in TYPE_MAP:
        return TYPE_MAP[python_type]
    
    # Handle generic types (List, Dict, Optional, etc.)
    origin = getattr(python_type, '__origin__', None)
    
    if origin is Union:
        # For Optional[X] (which is Union[X, None])
        args = getattr(python_type, '__args__', ())
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return get_json_type(non_none_args[0])
        return "string"  # Default for complex unions
    
    if origin is list:
        return "array"
    
    if origin is dict:
        return "object"
    
    # Default to string for unknown types
    return "string"


def function_to_schema(
    func: Callable,
    name_override: Optional[str] = None,
    description_override: Optional[str] = None
) -> ToolSchema:
    """
    Auto-generate JSON Schema from a Python function.
    Uses type hints and docstring for schema generation.
    """
    sig = inspect.signature(func)
    
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}
    
    docstring = inspect.getdoc(func) or ""
    
    # Parse parameter descriptions from docstring
    param_docs = parse_docstring(docstring)
    
    # Extract main description (first paragraph)
    main_description = docstring.split('\n\n')[0].strip() if docstring else ""
    
    # Build properties and required list
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip special parameters
        if param_name in ("self", "cls", "ctx", "context", "_"):
            continue
        
        # Get type
        param_type = hints.get(param_name, str)
        
        # Get JSON type
        json_type = get_json_type(param_type)
        
        # Build property schema
        prop_schema = {
            "type": json_type,
            "description": param_docs.get(param_name, f"The {param_name} parameter")
        }
        
        # Add enum if it's a Literal type
        if hasattr(param_type, '__args__') and hasattr(param_type, '__origin__'):
            from typing import Literal
            if getattr(param_type, '__origin__', None) is Literal:
                prop_schema["enum"] = list(param_type.__args__)
        
        properties[param_name] = prop_schema
        
        # Check if required (no default value)
        if param.default == inspect.Parameter.empty:
            # Also check if it's Optional
            origin = getattr(param_type, '__origin__', None)
            if origin is not Union:
                required.append(param_name)
            else:
                args = getattr(param_type, '__args__', ())
                if type(None) not in args:
                    required.append(param_name)
    
    return ToolSchema(
        name=name_override or func.__name__,
        description=description_override or main_description or func.__name__,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required
        }
    )
