from dataclasses import dataclass, field
from typing import Optional
import sympy as sp

@dataclass
class ParseResult:
    expr: sp.Expr
    entered_latex: str
    explicit_latex: str
    fx_expr: sp.Expr
    fy_expr: sp.Expr
    note: str = ""
    domain_note: str = ""
    converted_from_power: bool = False
    power: Optional[int] = None
    power_rhs_expr: Optional[sp.Expr] = None

@dataclass
class ExactAttempt:
    name: str
    setup_lines: list[str] = field(default_factory=list)
    step_lines: list[str] = field(default_factory=list)
    final_expr: Optional[sp.Expr] = None
    success: bool = False
    failure_reason: str = ""
    remaining_integral_latex: str = ""
