"""Reusable HTML/JS UI helpers."""
import base64
import os

import streamlit as st
import streamlit.components.v1 as components

from portfolio_app.config import BEAR_TREND_PATH, BULL_TREND_PATH

_MODIFIER_SCRIPT = """
<script>
(function () {
    var win = window.parent;
    var doc = win.document;
    if (win.__pero_modifiers_bound) return;
    win.__pero_modifiers_bound = true;

    function modifierHeld(e) {
        return !!(
            e.altKey
            || (e.getModifierState && e.getModifierState("Alt"))
            || e.ctrlKey
        );
    }

    function syncModifiers(e) {
        try {
            var url = new URL(win.location.href);
            var alt = modifierHeld(e);
            var shift = !!(e.shiftKey || (e.getModifierState && e.getModifierState("Shift")));
            url.searchParams.set("_pero_alt", alt ? "1" : "0");
            url.searchParams.set("_pero_shift", shift ? "1" : "0");
            win.history.replaceState({}, "", url);
        } catch (err) {}
    }

    // Only pointer/mouse down — keyup was clearing Alt before Streamlit reran.
    doc.addEventListener("pointerdown", syncModifiers, true);
    doc.addEventListener("mousedown", syncModifiers, true);
})();
</script>
"""


def inject_table_click_modifiers():
    """Record Alt/Shift on pointer down into URL params for the next rerun."""
    components.html(_MODIFIER_SCRIPT, height=0)


def _qp_flag(name: str) -> bool | None:
    """Read a 0/1 query flag; None if the param is absent this run."""
    if name not in st.query_params:
        return None
    raw = st.query_params.get(name)
    if isinstance(raw, list):
        raw = raw[-1] if raw else "0"
    return str(raw).lower() in ("1", "true")


def prime_click_modifiers():
    """Latch modifier keys from URL at the start of each run."""
    get_table_click_modifiers()


def mark_preserve_table_selection() -> None:
    """Keep portfolio table multi-select when a non-table widget triggers rerun."""
    import streamlit as st

    st.session_state["_preserve_table_selection"] = True


def get_table_click_modifiers():
    """Return (shift_held, alt_held) latched from the last pointer down."""
    shift_qp = _qp_flag("_pero_shift")
    alt_qp = _qp_flag("_pero_alt")

    if shift_qp is not None:
        st.session_state["_pero_shift_held"] = shift_qp
    if alt_qp is not None:
        st.session_state["_pero_alt_held"] = alt_qp

    return (
        bool(st.session_state.get("_pero_shift_held", False)),
        bool(st.session_state.get("_pero_alt_held", False)),
    )


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
