import sympy as sp


def to_bound(value: float) -> sp.Expr:
    return sp.nsimplify(value, rational=True)


def has_unsolved_integral(expr: sp.Expr) -> bool:
    return bool(expr.has(sp.Integral))


def simplify_clean(expr: sp.Expr) -> sp.Expr:
    return sp.simplify(sp.expand(expr))


def latex_join(exprs: list[sp.Expr], sep: str = " + ") -> str:
    return sep.join(sp.latex(expr) for expr in exprs)


def expr_has_problematic_symbolics(expr: sp.Expr) -> bool:
    bad_funcs = [
        sp.asinh,
        sp.acosh,
        sp.atanh,
        sp.erf,
        sp.Abs,
        sp.sign,
        sp.Max,
        sp.Min,
        sp.Heaviside,
    ]
    if any(expr.has(func) for func in bad_funcs):
        return True
    return "polar_lift" in sp.srepr(expr)
