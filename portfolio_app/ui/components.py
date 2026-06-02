"""Reusable HTML/JS UI helpers."""
import base64
import os

import streamlit as st

from portfolio_app.config import BEAR_TREND_PATH, BULL_TREND_PATH


def mark_preserve_table_selection() -> None:
    """Keep portfolio table multi-select when a non-table widget triggers rerun."""
    st.session_state["_preserve_table_selection"] = True


def is_financial_data_background_loading(view_name: str = "") -> bool:
    """True while visible financial background loaders still have pending symbols."""
    if st.session_state.get("metadata_bg_active") and st.session_state.get("metadata_queue"):
        return True
    show_valuation = view_name == "Valuation Growth"
    if (
        show_valuation
        and st.session_state.get("valuation_bg_active")
        and st.session_state.get("valuation_queue")
    ):
        return True
    return False


def render_financial_data_loading_umbrella(view_name: str = "") -> None:
    """Overall loading label above detailed analyst/valuation progress bars."""
    if is_financial_data_background_loading(view_name):
        st.caption("Loading financial data...")


@st.cache_data
def get_trend_icon_html(trend_type):
    """Inline trend icons from bull-trend.png / bear-trend.png."""
    paths = {
        "Bullish": (BULL_TREND_PATH, "Bull", "Bullish"),
        "Bearish": (BEAR_TREND_PATH, "Bear", "Bearish"),
    }
    if trend_type in paths:
        path, alt, title = paths[trend_type]
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return (
                f'<img class="trend-icon" src="data:image/png;base64,{b64}" '
                f'alt="{alt}" title="{title}"/>'
            )
    return '<span class="trend-icon-emoji">?</span>'
