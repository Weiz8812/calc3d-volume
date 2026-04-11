import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    standard_transformations,
)

x, y, z = sp.symbols("x y z")

SAMPLES = [
    {"label": "z = x^2 + y^2", "value": "z = x^2 + y^2", "latex": r"z = x^2 + y^2"},
    {"label": "z = x^2 - y^2", "value": "z = x^2 - y^2", "latex": r"z = x^2 - y^2"},
    {"label": "z = sin(x) + cos(y)", "value": r"z = \\sin(x) + \\cos(y)", "latex": r"z = \\sin(x) + \\cos(y)"},
    {"label": "z^2 = x + y + 4", "value": "z^2 = x + y + 4", "latex": r"z^2 = x + y + 4"},
    {"label": "x^2 + y^2 + z^2 = 1", "value": "x^2 + y^2 + z^2 = 1", "latex": r"x^2 + y^2 + z^2 = 1"},
]

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

ALLOWED = {
    "x": x, "y": y, "z": z,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log,
    "sqrt": sp.sqrt, "Abs": sp.Abs, "abs": sp.Abs,
    "pi": sp.pi, "E": sp.E,
}

SAFE_GLOBALS = {
    "__builtins__": {},
    "Symbol": sp.Symbol,
    "Integer": sp.Integer,
    "Float": sp.Float,
    "Rational": sp.Rational,
    "factorial": sp.factorial,
    "Add": sp.Add,
    "Mul": sp.Mul,
    "Pow": sp.Pow,
}
