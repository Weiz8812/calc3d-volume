import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from .constants import ALLOWED, SAFE_GLOBALS, TRANSFORMATIONS, x, y, z
from .models import ParseResult
from .utils import simplify_clean


def _extract_braced(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ValueError("Expected '{' in LaTeX-style input.")
    depth = 0
    out = []
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
            if depth > 1:
                out.append(c)
        elif c == "}":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(c)
        else:
            out.append(c)
    raise ValueError("Unbalanced braces in LaTeX-style input.")


def _replace_frac(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if text.startswith(r"\\frac", i):
            i += len(r"\\frac")
            num, i = _extract_braced(text, i)
            den, i = _extract_braced(text, i)
            out.append(f"(({_replace_frac(num)})/({_replace_frac(den)}))")
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def normalize(text: str) -> str:
    text = text.strip()
    if not text:
        raise ValueError("Please enter a surface.")
    text = text.replace("$", "")
    text = text.replace(chr(0x2212), "-").replace(chr(0x2013), "-").replace(chr(0x2014), "-")
    text = text.replace(chr(0x00D7), "*").replace(chr(0x00B7), "*")
    text = text.replace(r"\\left", "").replace(r"\\right", "")
    text = text.replace(r"\\,", "").replace(" ", "")
    text = _replace_frac(text)
    for old, new in {
        r"\\sin": "sin",
        r"\\cos": "cos",
        r"\\tan": "tan",
        r"\\asin": "asin",
        r"\\acos": "acos",
        r"\\atan": "atan",
        r"\\sinh": "sinh",
        r"\\cosh": "cosh",
        r"\\tanh": "tanh",
        r"\\exp": "exp",
        r"\\log": "log",
        r"\\ln": "log",
        r"\\sqrt": "sqrt",
        r"\\pi": "pi",
    }.items():
        text = text.replace(old, new)
    return text.replace("{", "(").replace("}", ")")


def parse_one(expr_text: str) -> sp.Expr:
    return parse_expr(
        expr_text,
        local_dict=ALLOWED.copy(),
        global_dict=SAFE_GLOBALS.copy(),
        transformations=TRANSFORMATIONS,
        evaluate=False,
    )


def is_z_power(expr: sp.Expr) -> bool:
    return isinstance(expr, sp.Pow) and expr.base == z and bool(expr.exp.is_Integer and int(expr.exp) > 0)


def isolate_rearranged_z_surface(left: sp.Expr, right: sp.Expr) -> dict | None:
    equation = simplify_clean(left - right)
    expanded = sp.expand(equation)
    terms = list(sp.Add.make_args(expanded))
    z_terms = [term for term in terms if term.has(z)]
    other_terms = [term for term in terms if not term.has(z)]

    if len(z_terms) != 1:
        return None

    z_term = simplify_clean(z_terms[0])
    coeff, core = z_term.as_independent(z, as_Add=False)
    coeff = simplify_clean(coeff)

    if coeff == 0 or coeff.free_symbols:
        return None

    rest = simplify_clean(sp.Add(*other_terms)) if other_terms else sp.Integer(0)
    rhs_expr = simplify_clean(-rest / coeff)

    if core == z:
        return {"kind": "linear", "rhs_expr": rhs_expr}

    if is_z_power(core):
        return {"kind": "power", "power": int(core.exp), "rhs_expr": rhs_expr}

    return None


def build_power_surface(rhs: sp.Expr, power: int) -> tuple[sp.Expr, str, str, str]:
    rhs_latex = sp.latex(rhs)
    explicit_latex = rf"\\sqrt[{power}]{{{rhs_latex}}}"
    if power % 2 == 1:
        expr = sp.sign(rhs) * sp.Abs(rhs) ** sp.Rational(1, power)
        note = f"Using the real branch derived from z^{power} = g(x,y)."
        domain_note = ""
    else:
        expr = sp.sqrt(rhs) if power == 2 else rhs ** sp.Rational(1, power)
        note = f"Using the principal real branch derived from z^{power} = g(x,y)."
        domain_note = f"For z^{power} = g(x,y), real values only exist where g(x,y) >= 0."
    return expr, explicit_latex, note, domain_note


def build_parse_result(
    expr: sp.Expr,
    entered_latex: str,
    explicit_latex: str,
    note: str = "",
    domain_note: str = "",
    converted: bool = False,
    power: int | None = None,
    power_rhs_expr: sp.Expr | None = None,
) -> ParseResult:
    fx_expr = sp.simplify(sp.diff(expr, x))
    fy_expr = sp.simplify(sp.diff(expr, y))
    bad = (expr.free_symbols | fx_expr.free_symbols | fy_expr.free_symbols) - {x, y}
    if bad:
        raise ValueError("Only x and y may appear in the surface after solving for z.")

    return ParseResult(
        expr,
        entered_latex,
        explicit_latex,
        fx_expr,
        fy_expr,
        note,
        domain_note,
        converted,
        power,
        power_rhs_expr,
    )


def solve_relation_to_surface(left: sp.Expr, right: sp.Expr, entered_latex: str) -> ParseResult:
    converted = False
    note = ""
    domain_note = ""
    power = None
    power_rhs_expr = None

    if left == z:
        expr = right
        explicit_latex = sp.latex(expr)
    elif right == z:
        expr = left
        explicit_latex = sp.latex(expr)
    elif is_z_power(left):
        power = int(left.exp)
        power_rhs_expr = right
        expr, explicit_latex, note, domain_note = build_power_surface(right, power)
        converted = True
    elif is_z_power(right):
        power = int(right.exp)
        power_rhs_expr = left
        expr, explicit_latex, note, domain_note = build_power_surface(left, power)
        converted = True
    else:
        rearranged = isolate_rearranged_z_surface(left, right)
        if rearranged is None:
            if not (left.has(z) or right.has(z)):
                raise ValueError(
                    "Enter a surface that defines z, such as z = x^2 + y^2, z^2 = 1 - x^2 - y^2, or x^2 + y^2 + z^2 = 1. Inputs that do not define z are not supported in this app."
                )
            raise ValueError(
                "Use z = f(x,y), f(x,y) = z, expressions that can be rearranged to z = f(x,y), or power equations such as z^3 = g(x,y), z^2 = g(x,y), or x^2 + y^2 + z^2 = 1."
            )
        converted = True
        if rearranged["kind"] == "linear":
            expr = rearranged["rhs_expr"]
            explicit_latex = sp.latex(expr)
            note = "Rearranged the implicit equation to isolate z."
        else:
            power = rearranged["power"]
            power_rhs_expr = rearranged["rhs_expr"]
            expr, explicit_latex, power_note, domain_note = build_power_surface(power_rhs_expr, power)
            note = f"Rearranged the implicit equation to isolate z^{power}. {power_note}"

    return build_parse_result(expr, entered_latex, explicit_latex, note, domain_note, converted, power, power_rhs_expr)


def parse_surface(text: str) -> ParseResult:
    text = normalize(text)
    if text.count("=") > 1:
        raise ValueError("Please enter at most one equation sign.")

    if "=" not in text:
        expr = parse_one(text)
        if expr.has(z):
            entered_latex = sp.latex(sp.Eq(expr, 0, evaluate=False))
            return solve_relation_to_surface(expr, sp.Integer(0), entered_latex)
        entered_latex = rf"z = {sp.latex(expr)}"
        explicit_latex = sp.latex(expr)
        return build_parse_result(expr, entered_latex, explicit_latex)

    left_text, right_text = text.split("=", 1)
    if not left_text or not right_text:
        raise ValueError("Both sides of the equation must be filled in.")
    left = parse_one(left_text)
    right = parse_one(right_text)
    entered_latex = sp.latex(sp.Eq(left, right, evaluate=False))
    return solve_relation_to_surface(left, right, entered_latex)
