# Calc3D Volume

Calc3D Volume is a Streamlit app for exploring and evaluating the volume under a surface in multivariable calculus.

The app lets users enter a surface, view its graph over a chosen region, and study both the symbolic setup and numerical approximation of the resulting double integral.

## Features

- Enter custom surfaces such as `z = x^2 + y^2`
- Parse explicit, implicit, and power-based surface inputs
- Graph the surface over Cartesian or polar regions
- Show both real branches when a surface has multiple real outputs
- Display symbolic volume setup and symbolic steps when available
- Compute numerical approximations for volume
- Export a PDF report of the work

## Supported Region Types

- Cartesian rectangles
- Polar disks, annuli, and sectors

## Example Inputs

- `z = x^2 + y^2`
- `z = sin(x) + cos(y)`
- `z^2 = x + y + 4`
- `x^2 + y^2 + z^2 = 1`

## Running the App

Install the dependencies:

```bash
pip install -r requirements.txt
