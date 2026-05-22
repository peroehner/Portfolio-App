"""Reusable HTML/JS UI helpers."""
import base64
import os

import streamlit as st
import streamlit.components.v1 as components

from portfolio_app.config import BEAR_TREND_PATH, BULL_TREND_PATH


def inject_table_click_modifiers():
    """Record Alt/Shift on mousedown into URL params for the next rerun."""
    components.html(
        """
        <script>
        (function () {
            var doc = window.parent.document;
            function syncModifiers(e) {
                try {
                    var url = new URL(window.parent.location.href);
                    url.searchParams.set("_pero_alt", e.altKey ? "1" : "0");
                    url.searchParams.set("_pero_shift", e.shiftKey ? "1" : "0");
                    window.parent.history.replaceState({}, "", url);
                } catch (err) {}
            }
            doc.addEventListener("mousedown", syncModifiers, true);
            doc.addEventListener("keydown", syncModifiers, true);
            doc.addEventListener("keyup", syncModifiers, true);
        })();
        </script>
        """,
        height=0,
    )


def get_table_click_modifiers():
    """Return (shift_held, alt_held) from the click that triggered this rerun."""
    qp = st.query_params
    shift = str(qp.get("_pero_shift", "0")).lower() in ("1", "true")
    alt = str(qp.get("_pero_alt", "0")).lower() in ("1", "true")
    return shift, alt


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
