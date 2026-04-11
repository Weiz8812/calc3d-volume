import copy

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import sympy as sp

from calc3d.constants import SAMPLES
from calc3d.numerical import approx_int, boundary_traces, eval_grid
from calc3d.parsing import parse_surface
from calc3d.polar import (
    approx_polar_midpoint,
    build_polar_volume_attempt,
    polar_boundary_traces,
    polar_midpoint_mesh,
    polar_surface_grid,
)
from calc3d.reporting import build_volume_report_tex, compile_report_pdf
from calc3d.symbolic import build_volume_attempt
from calc3d.utils import to_bound

st.set_page_config(page_title='Calc3D Volume', layout='wide')
st.title('Calc3D Volume')
st.caption('Symbolic-first multivariable calculus tool for 3D surfaces and double integrals.')


def clean_latex(text: str) -> str:
    return (text or '').replace('\\\\', '\\')


def show_latex(text: str) -> None:
    cleaned = clean_latex(text).strip()
    if cleaned:
        st.latex(cleaned)


def apply_volume_branch_adjustments(volume_attempt, show_lower_branch: bool, volume_mode: str):
    volume_attempt = copy.deepcopy(volume_attempt)
    if not show_lower_branch:
        return volume_attempt
    if volume_mode == 'Signed integral':
        volume_attempt.success = True
        volume_attempt.final_expr = sp.Integer(0)
        volume_attempt.failure_reason = ''
        volume_attempt.remaining_integral_latex = ''
        volume_attempt.step_lines.append(r'\text{Both real branches are included. For the total signed volume, the lower branch is the negative of the upper branch, so the contributions cancel by symmetry.}')
        volume_attempt.step_lines.append(r'V = 0')
    else:
        volume_attempt.step_lines.append(r'\text{Both real branches are plotted, but geometric volume above } z = 0 \text{ only uses the upper branch.}')
    return volume_attempt


def compute_cartesian_volume(pr, X, Y, x_values, y_values, show_lower_branch: bool, volume_mode: str):
    try:
        Z_full = eval_grid(pr.expr, X, Y, allow_partial=True)
        Z_clean = np.nan_to_num(Z_full, nan=0.0)
        if show_lower_branch and volume_mode == 'Signed integral':
            return 0.0
        Z_for_volume = np.maximum(Z_clean, 0.0) if volume_mode == 'Geometric volume above z = 0' else Z_clean
        return approx_int(Z_for_volume, x_values, y_values)
    except Exception:
        return None


def compute_polar_volume(pr, r_min_input, r_max_input, theta_min_input, theta_max_input, grid_points: int, show_lower_branch: bool, volume_mode: str):
    try:
        X_mid, Y_mid, R_mid, Theta_mid, dr, dtheta = polar_midpoint_mesh(r_min_input, r_max_input, theta_min_input, theta_max_input, grid_points)
        Z_mid = eval_grid(pr.expr, X_mid, Y_mid, allow_partial=True)
        Z_mid = np.nan_to_num(Z_mid, nan=0.0)
        if show_lower_branch and volume_mode == 'Signed integral':
            return 0.0
        Z_for_volume = np.maximum(Z_mid, 0.0) if volume_mode == 'Geometric volume above z = 0' else Z_mid
        return approx_polar_midpoint(Z_for_volume, R_mid, dr, dtheta)
    except Exception:
        return None


def apply_typed_surface():
    st.session_state.function_text = st.session_state.surface_input


def apply_selected_sample():
    chosen = st.session_state.selected_sample
    st.session_state.function_text = chosen['value']
    st.session_state.surface_input = chosen['value']


if 'function_text' not in st.session_state:
    st.session_state.function_text = SAMPLES[0]['value']
if 'surface_input' not in st.session_state:
    st.session_state.surface_input = st.session_state.function_text

with st.sidebar:
    st.header('Inputs')
    st.info('Type your own function first. The sample examples are optional.')
    st.markdown('**Step 1: Enter your own surface**')
    st.text_input('Enter surface here', key='surface_input', on_change=apply_typed_surface, help=('Type your own function here. Examples: z = x^2 + y^2, z^3 = x^2 + y^2, z^2 = x + y + 4, ' + r'\sin(x)+\cos(y), z+y, z+x, x+y+z=0, x^2+y^2+z^2=1, 1=x^2+y^2+z^2, x^2+y^2-z^2=0'))
    if st.button('Use typed surface'):
        apply_typed_surface()
    st.caption('Type your function above, then press Enter or click “Use typed surface”.')
    if st.session_state.function_text.strip():
        try:
            preview = parse_surface(st.session_state.function_text)
            st.caption('Current input preview')
            show_latex(preview.entered_latex)
            if preview.converted_from_power:
                show_latex(rf'z = {preview.explicit_latex}')
        except Exception:
            st.caption('Input preview unavailable until the expression parses.')
    st.markdown('**Optional: load a sample example**')
    sample = st.selectbox('Load sample example', SAMPLES, key='selected_sample', format_func=lambda item: item['label'])
    show_latex(sample['latex'])
    st.button('Use selected sample', on_click=apply_selected_sample)
    coordinate_mode = st.radio('Coordinate mode', ['Cartesian rectangle', 'Polar circular region'])
    st.markdown('**Step 2: Display and calculation options**')
    grid_points = st.slider('Plot grid resolution', min_value=40, max_value=250, value=100, step=10)
    volume_mode = st.radio('Volume calculation', ['Signed integral', 'Geometric volume above z = 0'], format_func=lambda mode: 'Net volume (positive and negative parts)' if mode == 'Signed integral' else 'Only the part above z = 0')
    st.caption('Choose whether to count signed volume or only the part above the xy-plane.')
    show_both_branches = st.checkbox('Show both real branches when available', value=True)
    show_numeric_approximation = st.checkbox('Show numerical approximation', value=True, help='Recommended: leave this on so the final approximate values are always visible.')
    if coordinate_mode == 'Cartesian rectangle':
        st.markdown('**Step 3: Set rectangular bounds**')
        x_min_input = st.number_input('x minimum', value=-2.0, step=1.0)
        x_max_input = st.number_input('x maximum', value=2.0, step=1.0)
        y_min_input = st.number_input('y minimum', value=-2.0, step=1.0)
        y_max_input = st.number_input('y maximum', value=2.0, step=1.0)
    else:
        st.markdown('**Step 3: Set polar bounds**')
        r_min_input = st.number_input('r minimum', value=0.0, step=0.5)
        r_max_input = st.number_input('r maximum', value=1.0, step=0.5)
        theta_min_input = st.number_input('theta minimum (radians)', value=0.0, step=0.5)
        theta_max_input = st.number_input('theta maximum (radians)', value=float(2 * np.pi), step=0.5)
        st.caption('Polar mode is best for disks, annuli, and circular sectors.')

try:
    pr = parse_surface(st.session_state.function_text)
except Exception as exc:
    st.error(f'Could not parse the function. {exc}')
    st.stop()

branch_available = bool(pr.converted_from_power and pr.power is not None and pr.power % 2 == 0 and pr.power_rhs_expr is not None)
show_lower_branch = branch_available and show_both_branches
report_tex = None
report_pdf_bytes = None
report_pdf_message = ''

if coordinate_mode == 'Cartesian rectangle':
    if x_min_input >= x_max_input or y_min_input >= y_max_input:
        st.error('Each minimum must be smaller than its matching maximum.')
        st.stop()
    x_min_exact = to_bound(x_min_input)
    x_max_exact = to_bound(x_max_input)
    y_min_exact = to_bound(y_min_input)
    y_max_exact = to_bound(y_max_input)
    x_values = np.linspace(x_min_input, x_max_input, grid_points)
    y_values = np.linspace(y_min_input, y_max_input, grid_points)
    X, Y = np.meshgrid(x_values, y_values)
    try:
        Z_plot = eval_grid(pr.expr, X, Y, allow_partial=True)
    except Exception as exc:
        st.error(str(exc))
        st.stop()
    partial_domain = np.isnan(Z_plot).any()
    show_latex(pr.entered_latex)
    if pr.converted_from_power:
        show_latex(rf'z = {pr.explicit_latex}')
    if pr.note:
        st.info(pr.note)
    if pr.domain_note:
        st.warning(pr.domain_note)
    if partial_domain:
        st.info('This surface is only real on part of the selected rectangle. The plot shows only the real-valued region, and numerical approximation over that visible region.')
    if show_lower_branch:
        st.info('Both real branches are plotted for this even-power surface. Calculations below are adjusted to match the displayed branches.')
    surfaces = [go.Surface(x=x_values, y=y_values, z=Z_plot, showscale=False, opacity=0.95, name='Upper branch')]
    if show_lower_branch:
        surfaces.append(go.Surface(x=x_values, y=y_values, z=-Z_plot, showscale=False, opacity=0.95, name='Lower branch'))
    base = go.Surface(x=X, y=Y, z=np.zeros_like(X, dtype=float), showscale=False, opacity=0.20, colorscale=[[0, '#d9d9d9'], [1, '#d9d9d9']])
    fig = go.Figure(data=[base] + surfaces + boundary_traces(x_min_input, x_max_input, y_min_input, y_max_input))
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0), scene=dict(xaxis_title='x', yaxis_title='y', zaxis_title='z', aspectmode='data'))
    st.plotly_chart(fig, width='stretch', config={'displaylogo': False, 'scrollZoom': False})
    volume_attempt = build_volume_attempt(pr, x_min_exact, x_max_exact, y_min_exact, y_max_exact, volume_mode)
    volume_attempt = apply_volume_branch_adjustments(volume_attempt, show_lower_branch, volume_mode)
    report_volume_value = compute_cartesian_volume(pr, X, Y, x_values, y_values, show_lower_branch, volume_mode)
    if show_numeric_approximation:
        st.markdown('### Numerical approximation')
        st.subheader('Numerical volume')
        if report_volume_value is not None:
            st.metric('Approximate value', f'{report_volume_value:.6f}')
        else:
            st.warning('Numerical volume was not computed on this region.')
    report_tex = build_volume_report_tex(pr=pr, coordinate_mode=coordinate_mode, volume_attempt=volume_attempt, volume_numeric=report_volume_value, cartesian_bounds=(x_min_exact, x_max_exact, y_min_exact, y_max_exact))
else:
    if r_min_input < 0 or r_min_input >= r_max_input or theta_min_input >= theta_max_input:
        st.error('Use polar bounds with 0 <= r minimum < r maximum and theta minimum < theta maximum.')
        st.stop()
    r_min_exact = to_bound(r_min_input)
    r_max_exact = to_bound(r_max_input)
    theta_min_exact = sp.nsimplify(theta_min_input, [sp.pi])
    theta_max_exact = sp.nsimplify(theta_max_input, [sp.pi])
    r_values = np.linspace(r_min_input, r_max_input, grid_points)
    theta_values = np.linspace(theta_min_input, theta_max_input, grid_points)
    try:
        X, Y, Z_plot, R = polar_surface_grid(pr.expr, r_values, theta_values, allow_partial=True)
    except Exception as exc:
        st.error(str(exc))
        st.stop()
    partial_domain = np.isnan(Z_plot).any()
    show_latex(pr.entered_latex)
    if pr.converted_from_power:
        show_latex(rf'z = {pr.explicit_latex}')
    if pr.note:
        st.info(pr.note)
    if pr.domain_note:
        st.warning(pr.domain_note)
    st.info('Polar mode treats the region in the xy-plane as a disk, annulus, or circular sector.')
    if partial_domain:
        st.info('This surface is only real on part of the selected polar region. The plot shows only the real-valued part, and numerical approximation over that visible region.')
    if show_lower_branch:
        st.info('Both real branches are plotted for this even-power surface. Calculations below are adjusted to match the displayed branches.')
    surfaces = [go.Surface(x=X, y=Y, z=Z_plot, showscale=False, opacity=0.95, name='Upper branch')]
    if show_lower_branch:
        surfaces.append(go.Surface(x=X, y=Y, z=-Z_plot, showscale=False, opacity=0.95, name='Lower branch'))
    base = go.Surface(x=X, y=Y, z=np.zeros_like(X, dtype=float), showscale=False, opacity=0.20, colorscale=[[0, '#d9d9d9'], [1, '#d9d9d9']])
    fig = go.Figure(data=[base] + surfaces + polar_boundary_traces(r_min_input, r_max_input, theta_min_input, theta_max_input))
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0), scene=dict(xaxis_title='x', yaxis_title='y', zaxis_title='z', aspectmode='data'))
    st.plotly_chart(fig, width='stretch', config={'displaylogo': False, 'scrollZoom': False})
    volume_attempt = build_polar_volume_attempt(pr, r_min_exact, r_max_exact, theta_min_exact, theta_max_exact, volume_mode)
    volume_attempt = apply_volume_branch_adjustments(volume_attempt, show_lower_branch, volume_mode)
    report_volume_value = compute_polar_volume(pr, r_min_input, r_max_input, theta_min_input, theta_max_input, grid_points, show_lower_branch, volume_mode)
    if show_numeric_approximation:
        st.markdown('### Numerical approximation')
        st.subheader('Numerical volume')
        if report_volume_value is not None:
            st.metric('Approximate value', f'{report_volume_value:.6f}')
        else:
            st.warning('Numerical volume was not computed on this polar region.')
    report_tex = build_volume_report_tex(pr=pr, coordinate_mode=coordinate_mode, volume_attempt=volume_attempt, volume_numeric=report_volume_value, polar_bounds=(r_min_exact, r_max_exact, theta_min_exact, theta_max_exact))

if report_tex is not None:
    report_pdf_bytes, report_pdf_message = compile_report_pdf(report_tex)

st.markdown('### Calculation details')
st.subheader('Volume')
for line in volume_attempt.setup_lines:
    show_latex(line)
if volume_attempt.success and volume_attempt.final_expr is not None:
    st.success('Exact symbolic result found.')
    show_latex(rf'V = {sp.latex(volume_attempt.final_expr)}')
else:
    st.warning(volume_attempt.failure_reason or 'Exact symbolic result not found.')
    if volume_attempt.remaining_integral_latex:
        show_latex(volume_attempt.remaining_integral_latex)

with st.expander('Show volume steps', expanded=False):
    for line in volume_attempt.step_lines:
        show_latex(line)
    if volume_attempt.success and volume_attempt.final_expr is not None:
        show_latex(rf'V = {sp.latex(volume_attempt.final_expr)}')
    elif volume_attempt.remaining_integral_latex:
        show_latex(volume_attempt.remaining_integral_latex)

if report_pdf_bytes is not None:
    st.success(report_pdf_message or 'PDF compiled successfully!')
    st.download_button('Download Overleaf-style PDF report', data=report_pdf_bytes, file_name='calc3d_report.pdf', mime='application/pdf', on_click='ignore')
elif report_tex is not None:
    st.warning(report_pdf_message or 'Could not compile the Overleaf-style PDF report. Download the .tex file instead.')
    st.download_button('Download Overleaf .tex report', data=report_tex, file_name='calc3d_report.tex', mime='text/x-tex', on_click='ignore')
