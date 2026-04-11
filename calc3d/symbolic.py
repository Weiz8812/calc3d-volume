import sympy as sp

from .constants import x, y
from .models import ExactAttempt, ParseResult
from .utils import expr_has_problematic_symbolics, has_unsolved_integral, latex_join, simplify_clean


def is_clean_display_expr(expr: sp.Expr, max_ops: int = 24, max_latex: int = 120) -> bool:
    if has_unsolved_integral(expr):
        return False
    if expr_has_problematic_symbolics(expr):
        return False
    if expr.count_ops() > max_ops:
        return False
    if len(sp.latex(expr)) > max_latex:
        return False
    return True


def is_valid_final_expr(expr: sp.Expr | None) -> bool:
    if expr is None:
        return False
    bad_atoms = (sp.nan, sp.zoo, sp.oo, -sp.oo)
    if expr in bad_atoms:
        return False
    if any(expr.has(atom) for atom in bad_atoms):
        return False
    return True


def simple_term_antiderivative(term: sp.Expr, var: sp.Symbol) -> tuple[sp.Expr | None, list[str]]:
    var_name = sp.latex(var)
    lines: list[str] = []

    try:
        antiderivative = sp.integrate(term, var)
    except Exception:
        return None, []

    if antiderivative is None or has_unsolved_integral(antiderivative):
        return None, []

    antiderivative = simplify_clean(antiderivative)
    if not is_clean_display_expr(antiderivative):
        return None, []

    if not term.has(var):
        lines.append(rf"\\int {sp.latex(term)}\\,d{var_name} = {sp.latex(term)} {var_name}")
    elif term == var:
        lines.append(rf"\\int {var_name}\\,d{var_name} = \\frac{{{var_name}^2}}{{2}}")
    elif isinstance(term, sp.Pow) and term.base == var and term.exp != -1:
        new_power = simplify_clean(term.exp + 1)
        lines.append(rf"\\int {sp.latex(term)}\\,d{var_name} = \\frac{{{var_name}^{{{sp.latex(new_power)}}}}}{{{sp.latex(new_power)}}}")
    else:
        coeff, remainder = term.as_independent(var, as_Add=False)
        if coeff != 1 and remainder != 1 and term.has(var):
            lines.append(rf"\\int {sp.latex(term)}\\,d{var_name} = {sp.latex(coeff)} \\int {sp.latex(remainder)}\\,d{var_name}")
            try:
                reduced_antiderivative = sp.integrate(remainder, var)
                if reduced_antiderivative is not None and not has_unsolved_integral(reduced_antiderivative):
                    reduced_antiderivative = simplify_clean(reduced_antiderivative)
                    if is_clean_display_expr(reduced_antiderivative):
                        lines.append(rf"= {sp.latex(coeff)}\\left({sp.latex(reduced_antiderivative)}\\right)")
                        lines.append(rf"= {sp.latex(antiderivative)}")
                        return antiderivative, lines
            except Exception:
                pass
        lines.append(rf"\\int {sp.latex(term)}\\,d{var_name} = {sp.latex(antiderivative)}")

    return antiderivative, lines


def build_antiderivative_steps(integrand: sp.Expr, var: sp.Symbol) -> tuple[sp.Expr | None, list[str]]:
    var_name = sp.latex(var)
    expanded = sp.expand(integrand)

    try:
        antiderivative = sp.integrate(integrand, var)
    except Exception:
        return None, []

    if antiderivative is None or has_unsolved_integral(antiderivative):
        return None, []

    antiderivative = simplify_clean(antiderivative)
    if not is_clean_display_expr(antiderivative):
        return None, []

    if isinstance(expanded, sp.Add):
        terms = list(sp.Add.make_args(expanded))
        term_results: list[sp.Expr] = []
        detail_lines: list[str] = []
        for term in terms:
            term_antiderivative, term_lines = simple_term_antiderivative(term, var)
            if term_antiderivative is None:
                detail_lines = []
                term_results = []
                break
            term_results.append(term_antiderivative)
            detail_lines.extend(term_lines)
        if term_results:
            split_terms = " + ".join(rf"\\int {sp.latex(term)}\\,d{var_name}" for term in terms)
            lines = [rf"\\int \\left({sp.latex(expanded)}\\right)\\,d{var_name} = {split_terms}"]
            lines.extend(detail_lines)
            lines.append(rf"= {sp.latex(simplify_clean(sp.Add(*term_results)))}")
            return antiderivative, lines

    term_antiderivative, term_lines = simple_term_antiderivative(integrand, var)
    if term_antiderivative is not None:
        return simplify_clean(term_antiderivative), term_lines

    return antiderivative, [rf"\\int {sp.latex(integrand)}\\,d{var_name} = {sp.latex(antiderivative)}"]


def build_definite_evaluation_lines(integrand: sp.Expr, antiderivative: sp.Expr, var: sp.Symbol, lower: sp.Expr, upper: sp.Expr) -> tuple[list[str], sp.Expr]:
    var_name = sp.latex(var)
    upper_value = simplify_clean(antiderivative.subs(var, upper))
    lower_value = simplify_clean(antiderivative.subs(var, lower))
    result = simplify_clean(upper_value - lower_value)
    lines = [
        rf"\\int_{{{sp.latex(lower)}}}^{{{sp.latex(upper)}}} {sp.latex(integrand)}\\,d{var_name} = \\left[{sp.latex(antiderivative)}\\right]_{{{sp.latex(lower)}}}^{{{sp.latex(upper)}}}",
        rf"= {sp.latex(upper_value)} - \\left({sp.latex(lower_value)}\\right)",
        rf"= {sp.latex(result)}",
    ]
    return lines, result


def can_attempt_antiderivative(expr: sp.Expr) -> bool:
    if expr_has_problematic_symbolics(expr):
        return False
    if expr.count_ops() > 30:
        return False
    if len(sp.latex(expr)) > 140:
        return False
    return True


def attempt_exact_integral(integrand: sp.Expr, x_min: sp.Expr, x_max: sp.Expr, y_min: sp.Expr, y_max: sp.Expr, name: str, setup_latex: str) -> ExactAttempt:
    attempt = ExactAttempt(name=name)
    attempt.setup_lines.append(setup_latex)
    attempt.step_lines.append(r"\\text{Integrate with respect to } y \\text{ first.}")

    if not can_attempt_antiderivative(integrand):
        attempt.failure_reason = "The inner antiderivative is too complicated for a clean symbolic step display. Use the numerical approximation for a decimal value."
        attempt.remaining_integral_latex = setup_latex
        attempt.step_lines.append(r"\\text{The exact setup is still valid, but the inner antiderivative is too complicated to display cleanly. Use the numerical approximation for a decimal value.}")
        return attempt

    inner_antiderivative, inner_lines = build_antiderivative_steps(integrand, y)
    if inner_antiderivative is None:
        attempt.failure_reason = "No clean closed-form antiderivative in y was found. Use the numerical approximation for a decimal value."
        attempt.remaining_integral_latex = setup_latex
        attempt.step_lines.append(r"\\text{The exact setup is still valid, but the inner antiderivative is not clean enough to display symbolically. Use the numerical approximation for a decimal value.}")
        return attempt

    attempt.step_lines.extend(inner_lines)
    inner_definite_lines, inner_definite = build_definite_evaluation_lines(integrand, inner_antiderivative, y, y_min, y_max)
    attempt.step_lines.extend(inner_definite_lines)
    attempt.step_lines.append(r"\\text{Now integrate the result with respect to } x \\text{.}")

    outer_setup = rf"\\int_{{{sp.latex(x_min)}}}^{{{sp.latex(x_max)}}} {sp.latex(inner_definite)}\\,dx"
    attempt.remaining_integral_latex = outer_setup

    if not can_attempt_antiderivative(inner_definite):
        attempt.failure_reason = "The outer antiderivative is too complicated for a clean symbolic step display. Use the numerical approximation for a decimal value."
        attempt.step_lines.append(rf"{outer_setup}")
        attempt.step_lines.append(r"\\text{This remaining outer integral is the exact setup. Use the numerical approximation for a decimal value.}")
        return attempt

    outer_antiderivative, outer_lines = build_antiderivative_steps(inner_definite, x)
    if outer_antiderivative is None:
        attempt.failure_reason = "No clean closed-form antiderivative in x was found after the inner integral. Use the numerical approximation for a decimal value."
        attempt.step_lines.append(rf"{outer_setup}")
        attempt.step_lines.append(r"\\text{This remaining outer integral is the exact setup. Use the numerical approximation for a decimal value.}")
        return attempt

    attempt.step_lines.extend(outer_lines)
    final_lines, final_expr = build_definite_evaluation_lines(inner_definite, outer_antiderivative, x, x_min, x_max)
    attempt.step_lines.extend(final_lines)
    attempt.final_expr = final_expr
    if is_valid_final_expr(final_expr):
        attempt.success = True
    else:
        attempt.final_expr = None
        attempt.success = False
        attempt.failure_reason = "The exact symbolic result became undefined during evaluation. Use the numerical approximation for a decimal value."
        attempt.remaining_integral_latex = setup_latex
    return attempt


def build_volume_attempt(pr: ParseResult, x_min: sp.Expr, x_max: sp.Expr, y_min: sp.Expr, y_max: sp.Expr, mode: str) -> ExactAttempt:
    integrand = sp.Max(pr.expr, 0) if mode == "Geometric volume above z = 0" else pr.expr
    setup = rf"V = \\int_{{{sp.latex(x_min)}}}^{{{sp.latex(x_max)}}}\\int_{{{sp.latex(y_min)}}}^{{{sp.latex(y_max)}}} {sp.latex(integrand)}\\,dy\\,dx"
    return attempt_exact_integral(integrand, x_min, x_max, y_min, y_max, "Volume", setup)
