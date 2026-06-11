"""Global price-history window (sync speed + Trends + Technical Analysis)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_app.analysis.fibonacci import normalize_ohlc_hist
from portfolio_app.config import (
    HISTORY_MONTHS_DEFAULT,
    HISTORY_MONTHS_MAX,
    HISTORY_MONTHS_MIN,
    HISTORY_MONTHS_PERSIST_KEY,
    HISTORY_MONTHS_WIDGET_KEY,
    SYNCED_HISTORY_MONTHS_KEY,
)
from portfolio_app.data.market_data import clamp_history_months
from portfolio_app.ui.components import mark_preserve_table_selection


def history_months() -> int:
    """Months to request on sync — persisted independently of the slider widget."""
    if HISTORY_MONTHS_PERSIST_KEY not in st.session_state:
        legacy = st.session_state.get("_ta_history_months_persist")
        if legacy is None:
            legacy = st.session_state.get("ta_history_months")
        default = legacy if legacy is not None else HISTORY_MONTHS_DEFAULT
        st.session_state[HISTORY_MONTHS_PERSIST_KEY] = clamp_history_months(default)
    return clamp_history_months(st.session_state[HISTORY_MONTHS_PERSIST_KEY])


def set_history_months(months: int) -> int:
    value = clamp_history_months(months)
    st.session_state[HISTORY_MONTHS_PERSIST_KEY] = value
    return value


def _hist_datetime_index(hist) -> pd.DatetimeIndex | None:
    """Datetime index for month bucketing; None when history has no dates (e.g. snapshot stub)."""
    if hist is None or getattr(hist, "empty", True):
        return None
    index = hist.index
    if isinstance(index, pd.RangeIndex):
        return None
    if isinstance(index, pd.DatetimeIndex):
        return index
    if pd.api.types.is_numeric_dtype(index):
        return None
    try:
        converted = pd.to_datetime(index, errors="coerce")
    except (TypeError, ValueError):
        return None
    if not isinstance(converted, pd.DatetimeIndex) or converted.isna().all():
        return None
    return converted


def month_options_from_hist(hist) -> list[str]:
    """From/To month choices from actual loaded OHLC rows (not the slider value)."""
    dt_index = _hist_datetime_index(hist)
    if dt_index is None:
        return []
    periods = dt_index.to_period("M").unique()
    return sorted(period.strftime("%Y-%m") for period in periods)


def hist_month_span_label(hist) -> str:
    options = month_options_from_hist(hist)
    if not options:
        return "no data"
    if len(options) == 1:
        return options[0]
    return f"{options[0]} → {options[-1]}"


def _request_resync_for_history_change() -> None:
    from portfolio_app.data.market_data import fetch_bulk_close

    fetch_bulk_close.clear()
    st.session_state.pending_network_refresh = True
    st.session_state.pop("analysis_portfolio_key", None)


def on_history_months_change() -> None:
    previous = history_months()
    new_months = set_history_months(st.session_state.get(HISTORY_MONTHS_WIDGET_KEY))
    if new_months != previous:
        synced = st.session_state.get(SYNCED_HISTORY_MONTHS_KEY)
        if synced is None or new_months != synced:
            _request_resync_for_history_change()
    symbol = str(st.session_state.get("ta_chart_symbol") or "").strip().upper()
    if symbol:
        from portfolio_app.services.ta_woi_service import _lock_ta_symbol_focus

        _lock_ta_symbol_focus(symbol)
    mark_preserve_table_selection()


def _sync_slider_from_persisted() -> int:
    months = history_months()
    st.session_state[HISTORY_MONTHS_WIDGET_KEY] = months
    return months


def render_history_months_controls(col, *, hist=None) -> None:
    """Center of expanded ⋮ toolbar row — between Portfolio and File actions."""
    months = _sync_slider_from_persisted()
    synced = st.session_state.get(SYNCED_HISTORY_MONTHS_KEY)
    span = hist_month_span_label(hist) if hist is not None else None
    with col:
        st.markdown(
            '<div class="portfolio-toolbar-ta-history-anchor"></div>',
            unsafe_allow_html=True,
        )
        label_col, slider_col, note_col = st.columns(
            [0.95, 2.8, 1.6],
            gap="small",
            vertical_alignment="center",
        )
        with label_col:
            st.markdown(
                '<span class="portfolio-toolbar-group-label">Price history</span>',
                unsafe_allow_html=True,
            )
        with slider_col:
            st.slider(
                "History (months)",
                min_value=HISTORY_MONTHS_MIN,
                max_value=HISTORY_MONTHS_MAX,
                key=HISTORY_MONTHS_WIDGET_KEY,
                on_change=on_history_months_change,
                label_visibility="collapsed",
                help=(
                    f"Months of Yahoo price history to fetch on sync ({HISTORY_MONTHS_MIN}–"
                    f"{HISTORY_MONTHS_MAX}). Shorter = faster sync. Applies to Trends and "
                    "Technical Analysis."
                ),
            )
        with note_col:
            if span and span != "no data":
                sync_note = ""
                if synced is not None and months != synced:
                    sync_note = " · sync pending"
                st.caption(f"**{months}** mo · **{span}**{sync_note}")
            elif synced is not None and months != synced:
                st.caption(f"**{months}** mo · sync pending")
            else:
                st.caption(f"**{months}** mo · max {HISTORY_MONTHS_MAX}")


def portfolio_ohlc_from_pick(pick: dict) -> pd.DataFrame:
    """OHLC for TA/export from synced portfolio history (no separate Yahoo fetch)."""
    hist = pick.get("hist") if pick else None
    return normalize_ohlc_hist(hist)


def load_portfolio_ohlc_history(symbol: str, pick: dict) -> pd.DataFrame:
    """TA chart history — always from last sync, scoped by the global history window."""
    hist = portfolio_ohlc_from_pick(pick)
    st.session_state["_ta_loaded_month_options"] = month_options_from_hist(hist)
    return hist


# Backward-compatible aliases (TA-specific names)
ta_history_months = history_months
set_ta_history_months = set_history_months
on_ta_history_months_change = on_history_months_change
render_ta_history_months_controls = render_history_months_controls
load_ta_ohlc_history = load_portfolio_ohlc_history
