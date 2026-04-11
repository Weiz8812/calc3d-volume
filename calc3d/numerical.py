import numpy as np
import plotly.graph_objects as go
import sympy as sp
from .constants import x, y

def eval_grid(expr: sp.Expr, X: np.ndarray, Y: np.ndarray, allow_partial: bool = False) -> np.ndarray:
    func = sp.lambdify((x, y), expr, modules=['numpy'])
    raw = func(X, Y)
    arr = np.asarray(raw)
    if np.isscalar(raw):
        arr = np.full_like(X, raw, dtype=float)
    if np.iscomplexobj(arr):
        real = np.real(arr)
        imag = np.imag(arr)
        mask = np.abs(imag) < 1e-10
        vals = np.full(arr.shape, np.nan, dtype=float)
        vals[mask] = real[mask]
    else:
        vals = arr.astype(float)
    if vals.shape != X.shape:
        raise ValueError('The function did not evaluate to a valid grid.')
    if allow_partial:
        if np.isnan(vals).all():
            raise ValueError('The selected region produced no real-valued points. Try changing the bounds.')
        vals[~np.isfinite(vals)] = np.nan
        return vals
    if not np.isfinite(vals).all():
        raise ValueError('The selected region produced undefined or non-finite values. Try changing the function or the x/y bounds.')
    return vals

def approx_int(values: np.ndarray, x_values: np.ndarray, y_values: np.ndarray) -> float:
    return float(np.trapezoid(np.trapezoid(values, x_values, axis=1), y_values))

def boundary_traces(x_min: float, x_max: float, y_min: float, y_max: float) -> list:
    line = dict(color='black', width=5)
    return [
        go.Scatter3d(x=[x_min, x_max], y=[y_min, y_min], z=[0, 0], mode='lines', line=line, showlegend=False),
        go.Scatter3d(x=[x_min, x_max], y=[y_max, y_max], z=[0, 0], mode='lines', line=line, showlegend=False),
        go.Scatter3d(x=[x_min, x_min], y=[y_min, y_max], z=[0, 0], mode='lines', line=line, showlegend=False),
        go.Scatter3d(x=[x_max, x_max], y=[y_min, y_max], z=[0, 0], mode='lines', line=line, showlegend=False),
    ]
