"""Custom AG Grid portfolio table (Phase 1 — Standard view spike)."""
import os

import streamlit.components.v1 as components

_PARENT = os.path.dirname(os.path.abspath(__file__))
_BUILD_DIR = os.path.join(_PARENT, "frontend", "build")

_component_func = components.declare_component("pero_portfolio_grid", path=_BUILD_DIR)


def portfolio_grid(
    *,
    rows,
    column_defs,
    selected_rows=None,
    height=320,
    key=None,
    default=None,
):
    """
    Render portfolio rows in AG Grid with Gmail-like selection.

    Returns ``{"rows": [int, ...], "symbols": [str, ...]}`` after user clicks,
    or ``default`` when unchanged.
    """
    return _component_func(
        rows=rows,
        column_defs=column_defs,
        selected_rows=list(selected_rows or []),
        height=int(height),
        key=key,
        default=default,
    )
