# Calc3D Volume

Calc3D Volume is an interactive Streamlit application for visualizing 3D surfaces and evaluating volume in multivariable calculus. It combines graphing, symbolic setup, numerical approximation, and report generation in one workflow.

## Project Background

Calc3D Volume is a focused continuation of **Calc3D Visualizer**, an earlier experimental project developed through the STEM Honors program at Wor-Wic Community College and presented at the 2026 Maryland Scholars Summit. The original project explored a wider set of multivariable-calculus features; Calc3D Volume narrows that work into a more focused tool for volume visualization and evaluation.

## Features

- Enter custom surfaces such as `z = x^2 + y^2`
- Parse explicit, implicit, and power-based surface inputs
- Visualize surfaces interactively in 3D with Plotly
- Work with Cartesian rectangles or polar disks, annuli, and sectors
- Display both real branches when an even-power surface produces them
- Build symbolic double-integral setups and show intermediate steps when available
- Compute numerical volume approximations when an exact symbolic result is impractical
- Choose between signed volume and geometric volume above `z = 0`
- Export the calculation workflow as a LaTeX-based PDF report

## Example Inputs

```text
z = x^2 + y^2
z = sin(x) + cos(y)
z^2 = x + y + 4
x^2 + y^2 + z^2 = 1
```

## Tech Stack

- Python
- Streamlit
- SymPy
- NumPy
- Plotly
- LaTeX / PDF report generation

## Running Locally

Clone the repository and install the Python dependencies:

```bash
pip install -r requirements.txt
```

Launch the application:

```bash
streamlit run app.py
```

The PDF export feature also uses the TeX packages listed in `packages.txt`.

## Development Note

This project was developed through extensive AI-assisted coding together with iterative testing, debugging, and refinement. It is intended as an educational visualization and calculation tool rather than a replacement for a full computer algebra system.
