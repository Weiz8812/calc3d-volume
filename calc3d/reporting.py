from pathlib import Path
import shutil
import subprocess
import tempfile

import sympy as sp

from .models import ExactAttempt, ParseResult

DEFAULT_TEMPLATE = r"""
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath, amssymb, mathtools}
\usepackage[T1]{fontenc}
\usepackage{lmodern}

\title{<<REPORT_TITLE>>}
\author{Zikang Wei}
\date{}

\begin{document}
\maketitle

\section*{1. Surface}
\[
<<SURFACE_LATEX>>
\]

\section*{2. Region}
\[
<<REGION_LATEX>>
\]

\section*{3. Exact Setup}
\[
<<SETUP_LATEX>>
\]

\section*{4. Symbolic Steps}
<<STEPS_BLOCK>>

\section*{5. Final Result}
\[
\boxed{V \approx <<FINAL_DECIMAL>>}
\]

\end{document}
""".strip()


def clean_latex(text: str) -> str:
    return (text or '').replace('\\\\', '\\')


def _latex_escape_text(text: str) -> str:
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _format_decimal(value: float | None) -> str:
    if value is None:
        return r'\text{Not available}'
    return f'{float(value):.6f}'


def _attempt_final_decimal(attempt: ExactAttempt, numeric_value: float | None) -> float | None:
    if attempt.success and attempt.final_expr is not None:
        try:
            return float(sp.N(attempt.final_expr))
        except Exception:
            return numeric_value
    return numeric_value


def _surface_latex(pr: ParseResult) -> str:
    if pr.converted_from_power:
        return clean_latex(rf'{pr.entered_latex} \qquad z = {pr.explicit_latex}')
    return clean_latex(pr.entered_latex)


def _extract_setup_latex(attempt: ExactAttempt, fallback: str = 'V = 0') -> str:
    if attempt.setup_lines:
        return clean_latex(attempt.setup_lines[-1])
    if attempt.remaining_integral_latex:
        return clean_latex(attempt.remaining_integral_latex)
    return fallback


def _build_cartesian_region(bounds: tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]) -> str:
    x_min, x_max, y_min, y_max = bounds
    return rf'[{sp.latex(x_min)}, {sp.latex(x_max)}] \times [{sp.latex(y_min)}, {sp.latex(y_max)}]'


def _build_polar_region(bounds: tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]) -> str:
    r_min, r_max, theta_min, theta_max = bounds
    return rf'r \in [{sp.latex(r_min)}, {sp.latex(r_max)}], \qquad \theta \in [{sp.latex(theta_min)}, {sp.latex(theta_max)}]'


def _display_math_block(content: str) -> str:
    text = clean_latex((content or '').strip())
    if not text:
        return ''
    return f'\\[\n{text}\n\\]'


def _line_already_present(target: str, lines: list[str]) -> bool:
    target_clean = clean_latex((target or '').strip())
    return any(clean_latex((line or '').strip()) == target_clean for line in lines)


def _build_steps_block(symbol: str, attempt: ExactAttempt, numeric_value: float | None) -> str:
    blocks: list[str] = []
    for line in attempt.step_lines:
        block = _display_math_block(line)
        if block:
            blocks.append(block)

    final_decimal = _attempt_final_decimal(attempt, numeric_value)
    if attempt.success and attempt.final_expr is not None:
        exact_line = rf'{symbol} = {sp.latex(attempt.final_expr)}'
        approx_line = rf'{symbol} \approx {_format_decimal(final_decimal)}'
        if not _line_already_present(exact_line, attempt.step_lines):
            blocks.append(_display_math_block(exact_line))
        if not _line_already_present(approx_line, attempt.step_lines):
            blocks.append(_display_math_block(approx_line))
    else:
        if attempt.remaining_integral_latex and not _line_already_present(attempt.remaining_integral_latex, attempt.step_lines):
            blocks.append(_display_math_block(attempt.remaining_integral_latex))
        reason = _latex_escape_text((attempt.failure_reason or 'A numerical approximation is used for the final value.').strip())
        blocks.append(_display_math_block(rf'\text{{{reason}}}'))
        blocks.append(_display_math_block(rf'{symbol} \approx {_format_decimal(final_decimal)}'))
    return '\n\n'.join(block for block in blocks if block)


def build_volume_report_tex(
    pr: ParseResult,
    coordinate_mode: str,
    volume_attempt: ExactAttempt,
    volume_numeric: float | None,
    cartesian_bounds: tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr] | None = None,
    polar_bounds: tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr] | None = None,
) -> str:
    if coordinate_mode == 'Cartesian rectangle':
        if cartesian_bounds is None:
            raise ValueError('Cartesian bounds are required for the Cartesian report template.')
        region_latex = _build_cartesian_region(cartesian_bounds)
    else:
        if polar_bounds is None:
            raise ValueError('Polar bounds are required for the polar report template.')
        region_latex = _build_polar_region(polar_bounds)

    final_decimal = _attempt_final_decimal(volume_attempt, volume_numeric)
    template = DEFAULT_TEMPLATE
    replacements = {
        '<<REPORT_TITLE>>': 'Calc3D Volume Report',
        '<<SURFACE_LATEX>>': _surface_latex(pr),
        '<<REGION_LATEX>>': region_latex,
        '<<SETUP_LATEX>>': _extract_setup_latex(volume_attempt, 'V = 0'),
        '<<STEPS_BLOCK>>': _build_steps_block('V', volume_attempt, volume_numeric),
        '<<FINAL_DECIMAL>>': _format_decimal(final_decimal),
    }
    for old, new in replacements.items():
        template = template.replace(old, new)
    return template


def compile_report_pdf(tex_source: str) -> tuple[bytes | None, str]:
    engine = shutil.which('pdflatex') or shutil.which('xelatex') or shutil.which('lualatex')
    if engine is None:
        return None, 'No LaTeX engine was found in the app environment.'

    engine_name = Path(engine).name
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        tex_path = workdir / 'calc3d_report.tex'
        tex_path.write_text(tex_source, encoding='utf-8')
        cmd = [engine, '-interaction=nonstopmode', '-halt-on-error', tex_path.name]
        for _ in range(2):
            result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                log_tail = '\n'.join((result.stdout or '').splitlines()[-20:])
                if not log_tail:
                    log_tail = '\n'.join((result.stderr or '').splitlines()[-20:])
                message = f'LaTeX compilation failed with {engine_name}.'
                if log_tail:
                    message += f' Last log lines:\n{log_tail}'
                return None, message
        pdf_path = workdir / 'calc3d_report.pdf'
        if not pdf_path.exists():
            return None, 'LaTeX finished without producing a PDF file.'
        return pdf_path.read_bytes(), f'PDF compiled successfully with {engine_name}.'
