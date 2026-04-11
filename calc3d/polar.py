import numpy as np
import plotly.graph_objects as go
import sympy as sp
from .constants import x, y
from .models import ExactAttempt, ParseResult
from .numerical import eval_grid
from .symbolic import build_antiderivative_steps, build_definite_evaluation_lines, can_attempt_antiderivative, is_valid_final_expr
from .utils import simplify_clean

r, theta = sp.symbols('r theta', nonnegative=True, real=True)

def polar_substitute(expr: sp.Expr) -> sp.Expr:
    return simplify_clean(expr.subs({x: r * sp.cos(theta), y: r * sp.sin(theta)}))

def polar_surface_grid(expr: sp.Expr, r_values: np.ndarray, theta_values: np.ndarray, allow_partial: bool = False):
    Theta, R = np.meshgrid(theta_values, r_values)
    X = R * np.cos(Theta)
    Y = R * np.sin(Theta)
    Z = eval_grid(expr, X, Y, allow_partial=allow_partial)
    return X, Y, Z, R

def polar_midpoint_mesh(r_min: float, r_max: float, theta_min: float, theta_max: float, points: int):
    r_edges = np.linspace(r_min, r_max, points + 1)
    theta_edges = np.linspace(theta_min, theta_max, points + 1)
    r_mid = 0.5 * (r_edges[:-1] + r_edges[1:])
    theta_mid = 0.5 * (theta_edges[:-1] + theta_edges[1:])
    Theta, R = np.meshgrid(theta_mid, r_mid)
    X = R * np.cos(Theta)
    Y = R * np.sin(Theta)
    dr = (r_max - r_min) / points
    dtheta = (theta_max - theta_min) / points
    return X, Y, R, Theta, dr, dtheta

def approx_polar_midpoint(values: np.ndarray, R: np.ndarray, dr: float, dtheta: float) -> float:
    safe = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    return float(np.sum(safe * R) * dr * dtheta)

def polar_boundary_traces(r_min: float, r_max: float, theta_min: float, theta_max: float, points: int = 240) -> list:
    traces = []
    line = dict(color='black', width=5)
    theta_vals = np.linspace(theta_min, theta_max, points)
    for radius in [r_min, r_max]:
        if radius <= 0:
            continue
        x_vals = radius * np.cos(theta_vals)
        y_vals = radius * np.sin(theta_vals)
        z_vals = np.zeros_like(theta_vals)
        traces.append(go.Scatter3d(x=x_vals, y=y_vals, z=z_vals, mode='lines', line=line, showlegend=False))
    r_vals = np.linspace(r_min, r_max, points)
    for angle in [theta_min, theta_max]:
        x_vals = r_vals * np.cos(angle)
        y_vals = r_vals * np.sin(angle)
        z_vals = np.zeros_like(r_vals)
        traces.append(go.Scatter3d(x=x_vals, y=y_vals, z=z_vals, mode='lines', line=line, showlegend=False))
    return traces

def attempt_exact_polar_integral(integrand: sp.Expr, r_min: sp.Expr, r_max: sp.Expr, theta_min: sp.Expr, theta_max: sp.Expr, name: str, setup_latex: str) -> ExactAttempt:
    attempt = ExactAttempt(name=name)
    attempt.setup_lines.append(setup_latex)
    attempt.step_lines.append(r"\\text{Integrate with respect to } r \\text{ first.}")
    if not can_attempt_antiderivative(integrand):
        attempt.failure_reason = 'The polar antiderivative is too complicated for a clean symbolic step display. Use the numerical approximation for a decimal value.'
        attempt.remaining_integral_latex = setup_latex
        return attempt
    inner_antiderivative, inner_lines = build_antiderivative_steps(integrand, r)
    if inner_antiderivative is None:
        attempt.failure_reason = 'No clean closed-form antiderivative in r was found. Use the numerical approximation for a decimal value.'
        attempt.remaining_integral_latex = setup_latex
        return attempt
    inner_definite_lines, inner_definite = build_definite_evaluation_lines(integrand, inner_antiderivative, r, r_min, r_max)
    if not is_valid_final_expr(inner_definite):
        attempt.failure_reason = 'The symbolic evaluation becomes undefined at the boundary, so the exact setup is shown and the numerical approximation should be used for the final value.'
        attempt.remaining_integral_latex = setup_latex
        return attempt
    attempt.step_lines.extend(inner_lines)
    attempt.step_lines.extend(inner_definite_lines)
    outer_setup = rf"\\int_{{{sp.latex(theta_min)}}}^{{{sp.latex(theta_max)}}} {sp.latex(inner_definite)}\\,d\\theta"
    attempt.remaining_integral_latex = outer_setup
    if not can_attempt_antiderivative(inner_definite):
        attempt.failure_reason = 'The outer polar antiderivative is too complicated for a clean symbolic step display. Use the numerical approximation for a decimal value.'
        attempt.step_lines.append(outer_setup)
        return attempt
    outer_antiderivative, outer_lines = build_antiderivative_steps(inner_definite, theta)
    if outer_antiderivative is None:
        attempt.failure_reason = 'No clean closed-form antiderivative in theta was found. Use the numerical approximation for a decimal value.'
        attempt.step_lines.append(outer_setup)
        return attempt
    final_lines, final_expr = build_definite_evaluation_lines(inner_definite, outer_antiderivative, theta, theta_min, theta_max)
    if not is_valid_final_expr(final_expr):
        attempt.failure_reason = 'The exact symbolic result became undefined during evaluation. Use the numerical approximation for a decimal value.'
        attempt.remaining_integral_latex = setup_latex
        return attempt
    attempt.step_lines.extend(outer_lines)
    attempt.step_lines.extend(final_lines)
    attempt.final_expr = final_expr
    attempt.success = True
    return attempt

def build_polar_volume_attempt(pr: ParseResult, r_min: sp.Expr, r_max: sp.Expr, theta_min: sp.Expr, theta_max: sp.Expr, mode: str) -> ExactAttempt:
    z_polar = polar_substitute(pr.expr)
    integrand = simplify_clean((sp.Max(z_polar, 0) if mode == 'Geometric volume above z = 0' else z_polar) * r)
    setup = rf"V = \\int_{{{sp.latex(theta_min)}}}^{{{sp.latex(theta_max)}}}\\int_{{{sp.latex(r_min)}}}^{{{sp.latex(r_max)}}} {sp.latex(integrand)}\\,dr\\,d\\theta"
    attempt = attempt_exact_polar_integral(integrand, r_min, r_max, theta_min, theta_max, 'Volume', setup)
    attempt.setup_lines = [rf"z(r,\\theta) = {sp.latex(z_polar)}", rf"V = \\iint_R z(r,\\theta)\\,r\\,dr\\,d\\theta" if mode == 'Signed integral' else rf"V = \\iint_R \\max(z(r,\\theta),0)\\,r\\,dr\\,d\\theta", setup]
    return attempt
