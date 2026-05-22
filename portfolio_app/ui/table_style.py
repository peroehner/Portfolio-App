"""Signed green/red styling for portfolio table cells."""
import pandas as pd

from portfolio_app.config import _COLOR_NEGATIVE, _COLOR_POSITIVE


def _signed_cell_color(intensity, rgb_end):
    intensity = max(0.0, min(1.0, intensity))
    r = int(255 - (255 - rgb_end[0]) * intensity)
    g = int(255 - (255 - rgb_end[1]) * intensity)
    b = int(255 - (255 - rgb_end[2]) * intensity)
    return f"background-color: rgb({r},{g},{b}); color: black"


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
            styles.append(_signed_cell_color(intensity, _COLOR_POSITIVE))
        else:
            intensity = abs(val) / max_neg if max_neg else 0
            styles.append(_signed_cell_color(intensity, _COLOR_NEGATIVE))
    return styles
