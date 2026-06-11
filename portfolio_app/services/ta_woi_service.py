"""Per-symbol sticky Window of Interest (WOI) for Technical Analysis."""
from __future__ import annotations

from typing import Any

import streamlit as st

from portfolio_app.services.session_context import get_active_portfolio_id
from portfolio_app.storage.repository import PortfolioRepository

STICKY_WOI_SESSION_KEY = "sticky_woi_by_symbol"
TA_DEFAULT_START_KEY = "ta_default_start"
TA_DEFAULT_END_KEY = "ta_default_end"
TA_WINDOW_SYMBOL_KEY = "_ta_window_symbol"
STICKY_WOI_CHECKBOX_KEY = "sticky_woi_enabled"


def _repo() -> PortfolioRepository:
    return PortfolioRepository()


def clear_ta_window_state() -> None:
    for key in (
        TA_DEFAULT_START_KEY,
        TA_DEFAULT_END_KEY,
        TA_WINDOW_SYMBOL_KEY,
        STICKY_WOI_CHECKBOX_KEY,
        STICKY_WOI_SESSION_KEY,
        "sel_start_ui",
        "sel_end_ui",
        "calc_fib_start",
        "calc_fib_end",
        "ui_fib_start",
        "ui_fib_end",
    ):
        st.session_state.pop(key, None)


def load_sticky_woi_for_portfolio(portfolio_id: int) -> dict[str, dict[str, str]]:
    mapping = _repo().get_symbol_ta_woi_map(portfolio_id)
    st.session_state[STICKY_WOI_SESSION_KEY] = mapping
    return mapping


def get_sticky_woi_map() -> dict[str, dict[str, str]]:
    return dict(st.session_state.get(STICKY_WOI_SESSION_KEY) or {})


def get_sticky_woi(symbol: str) -> dict[str, str] | None:
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return None
    entry = get_sticky_woi_map().get(symbol)
    if not entry:
        return None
    start = entry.get("start")
    end = entry.get("end")
    if not start or not end:
        return None
    return {"start": start, "end": end}


def _active_portfolio_id() -> int | None:
    return get_active_portfolio_id()


def set_sticky_woi(symbol: str, window_start: str, window_end: str) -> None:
    symbol = str(symbol or "").strip().upper()
    portfolio_id = _active_portfolio_id()
    if not symbol or not portfolio_id or not window_start or not window_end:
        return
    _repo().set_symbol_ta_woi(portfolio_id, symbol, window_start, window_end)
    mapping = get_sticky_woi_map()
    mapping[symbol] = {"start": window_start, "end": window_end}
    st.session_state[STICKY_WOI_SESSION_KEY] = mapping


def clear_sticky_woi(symbol: str) -> None:
    symbol = str(symbol or "").strip().upper()
    portfolio_id = _active_portfolio_id()
    if not symbol or not portfolio_id:
        return
    _repo().clear_symbol_ta_woi(portfolio_id, symbol)
    mapping = get_sticky_woi_map()
    mapping.pop(symbol, None)
    st.session_state[STICKY_WOI_SESSION_KEY] = mapping


def set_default_window(window_start: str, window_end: str) -> None:
    if window_start and window_end:
        st.session_state[TA_DEFAULT_START_KEY] = window_start
        st.session_state[TA_DEFAULT_END_KEY] = window_end


def get_default_window() -> tuple[str | None, str | None]:
    return (
        st.session_state.get(TA_DEFAULT_START_KEY),
        st.session_state.get(TA_DEFAULT_END_KEY),
    )


def resolve_window_for_symbol(symbol: str) -> tuple[str | None, str | None, bool]:
    """Return (start, end, is_sticky) for chart/export."""
    sticky = get_sticky_woi(symbol)
    if sticky:
        return sticky["start"], sticky["end"], True
    default_start, default_end = get_default_window()
    return default_start, default_end, False


def _apply_window_values(start: str, end: str) -> None:
    st.session_state["sel_start_ui"] = start
    st.session_state["sel_end_ui"] = end
    st.session_state["calc_fib_start"] = start
    st.session_state["calc_fib_end"] = end
    st.session_state["ui_fib_start"] = start
    st.session_state["ui_fib_end"] = end


def apply_window_for_symbol(symbol: str) -> bool:
    """Apply sticky or default WOI to TA controls. Returns True if a window was applied."""
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return False
    start, end, _ = resolve_window_for_symbol(symbol)
    if not start or not end:
        return False
    _apply_window_values(start, end)
    st.session_state[TA_WINDOW_SYMBOL_KEY] = symbol
    st.session_state[STICKY_WOI_CHECKBOX_KEY] = get_sticky_woi(symbol) is not None
    return True


def ensure_ta_window_for_symbol(symbol: str, month_options: list[str]) -> None:
    """Clamp and apply per-symbol WOI when the displayed symbol changes."""
    symbol = str(symbol or "").strip().upper()
    if not symbol or not month_options:
        return

    if st.session_state.get(TA_WINDOW_SYMBOL_KEY) != symbol:
        if not apply_window_for_symbol(symbol):
            start = month_options[0]
            end = month_options[-1]
            _apply_window_values(start, end)
            set_default_window(start, end)
            st.session_state[TA_WINDOW_SYMBOL_KEY] = symbol
            st.session_state[STICKY_WOI_CHECKBOX_KEY] = False

    default_start, default_end = get_default_window()
    if not default_start or not default_end:
        set_default_window(
            st.session_state.get("sel_start_ui", month_options[0]),
            st.session_state.get("sel_end_ui", month_options[-1]),
        )


def sync_default_window_from_controls() -> None:
    start = st.session_state.get("sel_start_ui")
    end = st.session_state.get("sel_end_ui")
    if start and end:
        set_default_window(start, end)


def persist_sticky_from_controls() -> None:
    symbol = str(st.session_state.get("ta_chart_symbol") or "").strip().upper()
    if not symbol:
        return
    start = st.session_state.get("calc_fib_start") or st.session_state.get("sel_start_ui")
    end = st.session_state.get("calc_fib_end") or st.session_state.get("sel_end_ui")
    if start and end:
        set_sticky_woi(symbol, start, end)


def _lock_ta_symbol_focus(symbol: str) -> None:
    """Keep the current TA chart symbol after Pin WoI toggles."""
    from portfolio_app.ui.components import mark_preserve_table_selection

    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return
    mark_preserve_table_selection()
    st.session_state.ta_chart_symbol = symbol
    st.session_state.selected_symbol = symbol
    st.session_state["_ta_pending_chart_symbol"] = symbol
    st.session_state[TA_WINDOW_SYMBOL_KEY] = symbol
    nav_symbols = st.session_state.get("_ta_nav_symbols") or []
    if symbol in nav_symbols:
        st.session_state.ta_nav_index = nav_symbols.index(symbol)


def on_sticky_woi_toggle() -> None:
    symbol = str(st.session_state.get("ta_chart_symbol") or "").strip().upper()
    if not symbol:
        return
    _lock_ta_symbol_focus(symbol)
    if st.session_state.get(STICKY_WOI_CHECKBOX_KEY):
        sync_default_window_from_controls()
        start = st.session_state.get("sel_start_ui")
        end = st.session_state.get("sel_end_ui")
        if start and end:
            _apply_window_values(start, end)
        persist_sticky_from_controls()
        return
    clear_sticky_woi(symbol)
    default_start, default_end = get_default_window()
    if default_start and default_end:
        _apply_window_values(default_start, default_end)


def on_window_controls_change() -> None:
    """Dropdown/bump edits — keep symbol focus; calc updates only via Re-Analyse."""
    symbol = str(st.session_state.get("ta_chart_symbol") or "").strip().upper()
    if symbol:
        _lock_ta_symbol_focus(symbol)
    sync_default_window_from_controls()


def sticky_woi_note_html(symbol: str) -> str:
    sticky = get_sticky_woi(symbol)
    if not sticky:
        return ""
    return (
        f'<span class="ta-pin-woi-inline">'
        f"· <strong>{symbol}</strong>: {sticky['start']} → {sticky['end']}"
        f"</span>"
    )


def export_windows_for_symbols(
    symbols: list[str],
    default_start: str | None,
    default_end: str | None,
) -> dict[str, dict[str, Any]]:
    """Per-symbol export window: sticky overrides default TA window."""
    out: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        start, end, is_sticky = resolve_window_for_symbol(symbol)
        if not start or not end:
            start, end = default_start, default_end
        out[symbol] = {
            "start": start,
            "end": end,
            "is_sticky": is_sticky,
        }
    return out
