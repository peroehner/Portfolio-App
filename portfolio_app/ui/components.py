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

    function syncModifiers(e) {
        try {
            var shift = !!(e.shiftKey || (e.getModifierState && e.getModifierState("Shift")));
            var alt = !!(e.altKey || (e.getModifierState && e.getModifierState("Alt")));
            win.sessionStorage.setItem("_pero_shift", shift ? "1" : "0");
            win.sessionStorage.setItem("_pero_alt", alt ? "1" : "0");
            var url = new URL(win.location.href);
            url.searchParams.set("_pero_shift", shift ? "1" : "0");
            url.searchParams.set("_pero_alt", alt ? "1" : "0");
            win.history.replaceState({}, "", url.href);
        } catch (err) {}
    }

    ["pointerdown", "mousedown", "keydown", "click"].forEach(function (ev) {
        doc.addEventListener(ev, syncModifiers, true);
    });
})();
</script>
"""


def inject_table_click_modifiers() -> None:
    """Capture Shift / Alt(Option) on pointer events (no external assets)."""
    components.html(_MODIFIER_SCRIPT, height=0, width=0)


def _qp_flag(name: str) -> bool | None:
    if name not in st.query_params:
        return None
    raw = st.query_params.get(name)
    if isinstance(raw, list):
        raw = raw[-1] if raw else "0"
    return str(raw).lower() in ("1", "true")


def mark_preserve_table_selection() -> None:
    """Keep portfolio table multi-select when a non-table widget triggers rerun."""
    st.session_state["_preserve_table_selection"] = True


def get_table_click_modifiers() -> tuple[bool, bool]:
    """Return (shift_held, alt_held) latched from the last pointer event."""
    shift_qp = _qp_flag("_pero_shift")
    alt_qp = _qp_flag("_pero_alt")

    if shift_qp is not None:
        st.session_state["_pero_shift_lat"] = shift_qp
    if alt_qp is not None:
        st.session_state["_pero_alt_lat"] = alt_qp

    shift_held = bool(st.session_state.get("_pero_shift_lat", False))
    alt_held = bool(st.session_state.get("_pero_alt_lat", False))

    st.session_state["_pero_shift_held"] = shift_held
    st.session_state["_pero_alt_held"] = alt_held
    return shift_held, alt_held


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
