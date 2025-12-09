#!/usr/bin/env python3
"""
Calculator Skill Script

A comprehensive calculator supporting:
- Basic arithmetic operations
- Percentage calculations
- Expression evaluation with variables
- Array/statistical operations
- Unit conversions

Usage: python3 calc.py <subcommand> [args]
"""

import argparse
import json
import math
import sys
import re
from typing import Any, Dict, List, Optional


def output(data: Dict[str, Any]) -> None:
    """Print JSON output and exit."""
    print(json.dumps(data))
    sys.exit(0 if "error" not in data else 1)


def error(message: str, **extra) -> None:
    """Print error and exit."""
    output({"error": message, **extra})


# ============================================
# Basic Arithmetic Operations
# ============================================

BASIC_OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b if b != 0 else None,
    "power": lambda a, b: a ** b,
    "modulo": lambda a, b: a % b if b != 0 else None,
    "sqrt": lambda a, b=None: math.sqrt(a) if a >= 0 else None,
    "abs": lambda a, b=None: abs(a),
    "floor": lambda a, b=None: math.floor(a),
    "ceil": lambda a, b=None: math.ceil(a),
}


def calc_command(args):
    """Handle basic calculation subcommand."""
    operation = args.operation.lower()
    
    if operation not in BASIC_OPERATIONS:
        error(
            f"Unknown operation: {operation}",
            available=list(BASIC_OPERATIONS.keys())
        )
    
    try:
        a = float(args.a)
    except (ValueError, TypeError):
        error(f"Invalid first number: {args.a}")
    
    # Some operations only need one number
    b = None
    if operation not in ("sqrt", "abs", "floor", "ceil"):
        if args.b is None:
            error(f"Operation '{operation}' requires two numbers")
        try:
            b = float(args.b)
        except (ValueError, TypeError):
            error(f"Invalid second number: {args.b}")
    
    result = BASIC_OPERATIONS[operation](a, b)
    
    if result is None:
        if operation == "sqrt":
            error("Cannot compute square root of negative number")
        elif operation in ("divide", "modulo"):
            error("Division by zero")
        else:
            error("Calculation error")
    
    response = {"operation": operation, "a": a, "result": result}
    if b is not None:
        response["b"] = b
    
    output(response)


# ============================================
# Percentage Calculations
# ============================================

def percent_command(args):
    """Handle percentage calculation subcommand."""
    try:
        value = float(args.value)
    except (ValueError, TypeError):
        error(f"Invalid value: {args.value}")
    
    try:
        percent = float(args.percent)
    except (ValueError, TypeError):
        error(f"Invalid percentage: {args.percent}")
    
    result = (value * percent) / 100
    
    output({
        "value": value,
        "percent": percent,
        "result": result
    })


# ============================================
# Expression Evaluation
# ============================================

# Safe math functions available in expressions
SAFE_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    "pow": pow,
    "min": min,
    "max": max,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def safe_eval(expression: str, variables: Dict[str, float]) -> float:
    """
    Safely evaluate a mathematical expression.
    Only allows specific functions and variables.
    """
    # Create safe namespace
    namespace = {
        "__builtins__": {},  # No builtins
        **SAFE_FUNCTIONS,
        **SAFE_CONSTANTS,
        **variables,
    }
    
    # Validate expression (basic security check)
    # Allow: numbers, operators, parentheses, function names, variable names
    if not re.match(r'^[\d\s\+\-\*/\.\(\)\,a-zA-Z_]+$', expression):
        raise ValueError("Invalid characters in expression")
    
    try:
        result = eval(expression, namespace)
        return float(result)
    except Exception as e:
        raise ValueError(f"Evaluation error: {str(e)}")


def expr_command(args):
    """Handle expression evaluation subcommand."""
    expression = args.expression
    
    # Parse variables
    variables = {}
    if args.var:
        for var_def in args.var:
            if "=" not in var_def:
                error(f"Invalid variable definition: {var_def}. Use format: name=value")
            name, value = var_def.split("=", 1)
            try:
                variables[name.strip()] = float(value.strip())
            except ValueError:
                error(f"Invalid variable value: {value}")
    
    try:
        result = safe_eval(expression, variables)
        output({
            "expression": expression,
            "variables": variables,
            "result": result
        })
    except ValueError as e:
        error(str(e))


# ============================================
# Array/Statistical Operations
# ============================================

ARRAY_OPERATIONS = {
    "sum": lambda data: sum(data),
    "mean": lambda data: sum(data) / len(data),
    "median": lambda data: sorted(data)[len(data) // 2] if len(data) % 2 else 
                           (sorted(data)[len(data) // 2 - 1] + sorted(data)[len(data) // 2]) / 2,
    "min": lambda data: min(data),
    "max": lambda data: max(data),
    "range": lambda data: max(data) - min(data),
    "variance": lambda data: sum((x - sum(data) / len(data)) ** 2 for x in data) / len(data),
    "stdev": lambda data: math.sqrt(sum((x - sum(data) / len(data)) ** 2 for x in data) / len(data)),
}


def array_command(args):
    """Handle array/statistical operations subcommand."""
    operation = args.operation.lower()
    
    if operation not in ARRAY_OPERATIONS:
        error(
            f"Unknown array operation: {operation}",
            available=list(ARRAY_OPERATIONS.keys())
        )
    
    # Parse JSON array
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        error(f"Invalid JSON array: {e}")
    
    if not isinstance(data, list):
        error("Input must be a JSON array")
    
    if len(data) == 0:
        error("Array cannot be empty")
    
    try:
        data = [float(x) for x in data]
    except (ValueError, TypeError):
        error("All array elements must be numbers")
    
    try:
        result = ARRAY_OPERATIONS[operation](data)
        output({
            "operation": operation,
            "data": data,
            "result": result
        })
    except Exception as e:
        error(f"Calculation error: {str(e)}")


# ============================================
# Unit Conversion
# ============================================

# Conversion factors to base units
UNIT_CONVERSIONS = {
    # Length (base: meters)
    "km": ("length", 1000),
    "m": ("length", 1),
    "cm": ("length", 0.01),
    "mm": ("length", 0.001),
    "mi": ("length", 1609.344),
    "ft": ("length", 0.3048),
    "in": ("length", 0.0254),
    "yd": ("length", 0.9144),
    
    # Weight (base: kilograms)
    "kg": ("weight", 1),
    "g": ("weight", 0.001),
    "mg": ("weight", 0.000001),
    "lb": ("weight", 0.453592),
    "oz": ("weight", 0.0283495),
    
    # Volume (base: liters)
    "l": ("volume", 1),
    "ml": ("volume", 0.001),
    "gal": ("volume", 3.78541),
    "floz": ("volume", 0.0295735),
    "cup": ("volume", 0.236588),
    
    # Time (base: seconds)
    "sec": ("time", 1),
    "min": ("time", 60),
    "hr": ("time", 3600),
    "day": ("time", 86400),
    
    # Temperature (special handling)
    "c": ("temperature", None),
    "f": ("temperature", None),
    "k": ("temperature", None),
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between temperature units."""
    # First convert to Celsius
    if from_unit == "c":
        celsius = value
    elif from_unit == "f":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "k":
        celsius = value - 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")
    
    # Then convert from Celsius to target
    if to_unit == "c":
        return celsius
    elif to_unit == "f":
        return celsius * 9 / 5 + 32
    elif to_unit == "k":
        return celsius + 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {to_unit}")


def convert_command(args):
    """Handle unit conversion subcommand."""
    try:
        value = float(args.value)
    except (ValueError, TypeError):
        error(f"Invalid value: {args.value}")
    
    from_unit = args.from_unit.lower()
    to_unit = args.to_unit.lower()
    
    if from_unit not in UNIT_CONVERSIONS:
        error(f"Unknown unit: {from_unit}", available=list(UNIT_CONVERSIONS.keys()))
    
    if to_unit not in UNIT_CONVERSIONS:
        error(f"Unknown unit: {to_unit}", available=list(UNIT_CONVERSIONS.keys()))
    
    from_type, from_factor = UNIT_CONVERSIONS[from_unit]
    to_type, to_factor = UNIT_CONVERSIONS[to_unit]
    
    if from_type != to_type:
        error(f"Cannot convert between {from_type} and {to_type}")
    
    # Special handling for temperature
    if from_type == "temperature":
        try:
            result = convert_temperature(value, from_unit, to_unit)
        except ValueError as e:
            error(str(e))
    else:
        # Standard conversion: value -> base unit -> target unit
        base_value = value * from_factor
        result = base_value / to_factor
    
    output({
        "value": value,
        "from": from_unit,
        "to": to_unit,
        "result": result
    })


# ============================================
# Main CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Calculator skill - perform various mathematical operations"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # calc subcommand
    calc_parser = subparsers.add_parser("calc", help="Basic arithmetic operations")
    calc_parser.add_argument("operation", help="Operation to perform")
    calc_parser.add_argument("a", help="First number")
    calc_parser.add_argument("b", nargs="?", help="Second number (optional for some operations)")
    
    # percent subcommand
    percent_parser = subparsers.add_parser("percent", help="Calculate percentage")
    percent_parser.add_argument("of", help="Literal 'of'")
    percent_parser.add_argument("value", help="Value to calculate percentage of")
    percent_parser.add_argument("--percent", required=True, help="Percentage to calculate")
    
    # expr subcommand
    expr_parser = subparsers.add_parser("expr", help="Evaluate mathematical expression")
    expr_parser.add_argument("expression", help="Mathematical expression")
    expr_parser.add_argument("--var", action="append", help="Variable definition (name=value)")
    
    # array subcommand
    array_parser = subparsers.add_parser("array", help="Array/statistical operations")
    array_parser.add_argument("operation", help="Operation to perform")
    array_parser.add_argument("data", help="JSON array of numbers")
    
    # convert subcommand
    convert_parser = subparsers.add_parser("convert", help="Unit conversion")
    convert_parser.add_argument("value", help="Value to convert")
    convert_parser.add_argument("from_unit", help="Source unit")
    convert_parser.add_argument("to_unit", help="Target unit")
    
    args = parser.parse_args()
    
    if args.command == "calc":
        calc_command(args)
    elif args.command == "percent":
        percent_command(args)
    elif args.command == "expr":
        expr_command(args)
    elif args.command == "array":
        array_command(args)
    elif args.command == "convert":
        convert_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
