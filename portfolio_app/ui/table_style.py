"""Signed green/red styling for portfolio table cells."""
import pandas as pd

from portfolio_app.config import _COLOR_NEGATIVE, _COLOR_POSITIVE


def _signed_cell_color(intensity, rgb_end):
    intensity = max(0.0, min(1.0, intensity))
    r = int(255 - (255 - rgb_end[0]) * intensity)
    g = int(255 - (255 - rgb_end[1]) * intensity)
    b = int(255 - (255 - rgb_end[2]) * intensity)
    return f"rgb({r},{g},{b})"


def signed_cell_background(value, *, max_pos: float, max_neg: float) -> str:
    """Background color for one numeric cell (matches pandas Styler output)."""
    if pd.isna(value) or value == 0:
        return "rgb(255,255,255)"
    if value > 0:
        intensity = value / max_pos if max_pos else 0
        return _signed_cell_color(intensity, _COLOR_POSITIVE)
    intensity = abs(value) / max_neg if max_neg else 0
    return _signed_cell_color(intensity, _COLOR_NEGATIVE)


def gradient_backgrounds(series) -> list[str]:
    """Per-row background colors for a signed gradient column."""
    numeric = pd.to_numeric(series, errors="coerce")
    positives = numeric[numeric > 0]
    negatives = numeric[numeric < 0]
    max_pos = float(positives.max()) if not positives.empty else 0.0
    max_neg = float(negatives.abs().max()) if not negatives.empty else 0.0
    return [
        signed_cell_background(val, max_pos=max_pos, max_neg=max_neg)
        for val in numeric
    ]


def style_signed_column(series):
    """Green for gains, red for losses; intensity scales with magnitude."""
    numeric = pd.to_numeric(series, errors="coerce")
    positives = numeric[numeric > 0]
    negatives = numeric[numeric < 0]
    max_pos = positives.max() if not positives.empty else 0
    max_neg = negatives.abs().max() if not negatives.empty else 0

    styles = []
    for val in numeric:
        if pd.isna(val) or val == 0:
            styles.append("background-color: white; color: black")
        elif val > 0:
            intensity = val / max_pos if max_pos else 0
            styles.append(
                f"background-color: {_signed_cell_color(intensity, _COLOR_POSITIVE)}; color: black"
            )
        else:
            intensity = abs(val) / max_neg if max_neg else 0
            styles.append(
                f"background-color: {_signed_cell_color(intensity, _COLOR_NEGATIVE)}; color: black"
            )
    return styles
