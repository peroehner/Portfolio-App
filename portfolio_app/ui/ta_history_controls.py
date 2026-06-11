"""Backward-compatible re-exports — use portfolio_app.ui.history_controls."""
from portfolio_app.ui.history_controls import (  # noqa: F401
    hist_month_span_label,
    history_months,
    load_portfolio_ohlc_history,
    load_ta_ohlc_history,
    month_options_from_hist,
    on_history_months_change,
    on_ta_history_months_change,
    portfolio_ohlc_from_pick,
    render_history_months_controls,
    render_ta_history_months_controls,
    set_history_months,
    set_ta_history_months,
    ta_history_months,
)
