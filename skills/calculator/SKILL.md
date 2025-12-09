---
name: calculator
description: Perform mathematical calculations including basic arithmetic, expressions, array operations, and unit conversions.
---

# Calculator Skill

A comprehensive calculator that supports basic arithmetic, complex expressions, statistical operations on arrays, and unit conversions.

## Usage

All commands are executed using the `execute_command` tool. The calculator script is located at `calculator/scripts/calc.py`.

### Basic Arithmetic

```bash
python3 calculator/scripts/calc.py calc <operation> <a> <b>
```

**Operations:**
- `add` - Add two numbers
- `subtract` - Subtract b from a
- `multiply` - Multiply two numbers
- `divide` - Divide a by b
- `power` - Raise a to the power of b
- `modulo` - Get remainder of a divided by b
- `sqrt` - Square root (only needs one number)
- `abs` - Absolute value (only needs one number)
- `floor` - Round down (only needs one number)
- `ceil` - Round up (only needs one number)

**Examples:**
```bash
# Add two numbers
python3 calculator/scripts/calc.py calc add 5 3
# Output: {"operation": "add", "a": 5.0, "b": 3.0, "result": 8.0}

# Square root
python3 calculator/scripts/calc.py calc sqrt 144
# Output: {"operation": "sqrt", "a": 144.0, "result": 12.0}

# Division
python3 calculator/scripts/calc.py calc divide 100 4
# Output: {"operation": "divide", "a": 100.0, "b": 4.0, "result": 25.0}
```

### Percentage Calculations

```bash
python3 calculator/scripts/calc.py percent of <number> --percent <percentage>
```

**Examples:**
```bash
# Calculate 15% of 200
python3 calculator/scripts/calc.py percent of 200 --percent 15
# Output: {"value": 200.0, "percent": 15.0, "result": 30.0}

# Calculate 8.5% of 1000
python3 calculator/scripts/calc.py percent of 1000 --percent 8.5
# Output: {"value": 1000.0, "percent": 8.5, "result": 85.0}
```

### Expression Evaluation

Evaluate complex mathematical expressions with variables.

```bash
python3 calculator/scripts/calc.py expr "<expression>" [--var name=value ...]
```

**Supported functions:** sin, cos, tan, sqrt, log, log10, exp, abs, floor, ceil, pow

**Examples:**
```bash
# Simple expression
python3 calculator/scripts/calc.py expr "sqrt(144) + pow(5, 2)"
# Output: {"expression": "sqrt(144) + pow(5, 2)", "variables": {}, "result": 37.0}

# Expression with variables
python3 calculator/scripts/calc.py expr "a * b + c" --var a=5 --var b=10 --var c=3
# Output: {"expression": "a * b + c", "variables": {"a": 5.0, "b": 10.0, "c": 3.0}, "result": 53.0}

# Trigonometry (radians)
python3 calculator/scripts/calc.py expr "sin(3.14159/2)"
# Output: {"expression": "sin(3.14159/2)", "variables": {}, "result": 0.9999996829...}
```

### Array/Statistical Operations

Perform statistical operations on arrays of numbers.

```bash
python3 calculator/scripts/calc.py array <operation> '<json_array>'
```

**Operations:**
- `sum` - Sum of all elements
- `mean` - Average of all elements
- `median` - Middle value
- `min` - Minimum value
- `max` - Maximum value
- `stdev` - Standard deviation (population)
- `variance` - Variance (population)
- `range` - Difference between max and min

**Examples:**
```bash
# Calculate average
python3 calculator/scripts/calc.py array mean '[85, 92, 78, 96, 88]'
# Output: {"operation": "mean", "data": [85, 92, 78, 96, 88], "result": 87.8}

# Calculate standard deviation
python3 calculator/scripts/calc.py array stdev '[85, 92, 78, 96, 88]'
# Output: {"operation": "stdev", "data": [85, 92, 78, 96, 88], "result": 6.572...}

# Find sum
python3 calculator/scripts/calc.py array sum '[10, 20, 30, 40, 50]'
# Output: {"operation": "sum", "data": [10, 20, 30, 40, 50], "result": 150}
```

### Unit Conversion

Convert between common units.

```bash
python3 calculator/scripts/calc.py convert <value> <from_unit> <to_unit>
```

**Supported conversions:**
- Length: km, mi, m, ft, cm, in
- Weight: kg, lb, g, oz
- Temperature: c, f, k (Celsius, Fahrenheit, Kelvin)
- Volume: l, gal, ml, floz
- Time: hr, min, sec

**Examples:**
```bash
# Kilometers to miles
python3 calculator/scripts/calc.py convert 100 km mi
# Output: {"value": 100.0, "from": "km", "to": "mi", "result": 62.137...}

# Celsius to Fahrenheit
python3 calculator/scripts/calc.py convert 20 c f
# Output: {"value": 20.0, "from": "c", "to": "f", "result": 68.0}

# Kilograms to pounds
python3 calculator/scripts/calc.py convert 75 kg lb
# Output: {"value": 75.0, "from": "kg", "to": "lb", "result": 165.347...}
```

## Error Handling

If an error occurs, the output will include an error field:

```json
{"error": "Unknown operation: flurbnitz", "available": ["add", "subtract", ...]}
```

Always check for the `error` field in the output and handle it appropriately.

## Notes

- All numeric results are returned as floats
- Division by zero returns an error
- Array operations require valid JSON array format
- Expression evaluation uses a safe math parser (no code injection)
