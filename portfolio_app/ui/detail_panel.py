"""Technical analysis detail: chart, trends, Fibonacci, export sidebar."""
import pandas as pd
import streamlit as st

from portfolio_app.analysis.fibonacci import compute_fibonacci_levels
from portfolio_app.analysis.trends import find_multiple_trends
from portfolio_app.config import DETAIL_HISTORY_PERIOD
from portfolio_app.data.market_data import get_symbol_metadata, get_ticker_ohlc_history
from portfolio_app.data.metadata import enrich_symbol_metadata, prioritize_metadata_symbol
from portfolio_app.ui.charts import create_chart
from portfolio_app.ui.components import get_trend_icon_html
from portfolio_app.ui.export import build_multi_export_datasets
from portfolio_app.ui.components import mark_preserve_table_selection


def _sync_ticker_selection(ticker_liste):
    if st.session_state.get("selected_symbol") not in ticker_liste:
        st.session_state.selected_symbol = ticker_liste[0]
        st.session_state.ticker_index = 0
    elif (
        "ticker_index" not in st.session_state
        or st.session_state.ticker_index >= len(ticker_liste)
    ):
        st.session_state.ticker_index = ticker_liste.index(
            st.session_state.selected_symbol
        )


def _clamp_month_in_options(value, month_options, default):
    if value in month_options:
        return value
    return default


def _ensure_month_range(month_options):
    if not month_options:
        return

    start_default = month_options[0]
    end_default = month_options[-1]

    if st.session_state.get("fibo_needs_refresh", False):
        st.session_state["calc_fib_start"] = start_default
        st.session_state["calc_fib_end"] = end_default
        st.session_state["sel_start_ui"] = start_default
        st.session_state["sel_end_ui"] = end_default
        st.session_state["fibo_needs_refresh"] = False
    else:
        start = _clamp_month_in_options(
            st.session_state.get("sel_start_ui"), month_options, start_default
        )
        end = _clamp_month_in_options(
            st.session_state.get("sel_end_ui"), month_options, end_default
        )
        if month_options.index(start) > month_options.index(end):
            start, end = start_default, end_default
        st.session_state["sel_start_ui"] = start
        st.session_state["sel_end_ui"] = end

        calc_start = _clamp_month_in_options(
            st.session_state.get("calc_fib_start"), month_options, start
        )
        calc_end = _clamp_month_in_options(
            st.session_state.get("calc_fib_end"), month_options, end
        )
        if month_options.index(calc_start) > month_options.index(calc_end):
            calc_start, calc_end = start, end
        st.session_state["calc_fib_start"] = calc_start
        st.session_state["calc_fib_end"] = calc_end

    # Chart viewport — must exist before _compute_chart_data (controls row sets again after widgets)
    st.session_state["ui_fib_start"] = st.session_state["sel_start_ui"]
    st.session_state["ui_fib_end"] = st.session_state["sel_end_ui"]


def _load_hist_for_ticker(selected_ticker, pick):
    hist_full = get_ticker_ohlc_history(selected_ticker, DETAIL_HISTORY_PERIOD)
    if hist_full.empty:
        hist_full = pick["hist"].copy()
        if getattr(hist_full.index, "tz", None) is not None:
            hist_full.index = hist_full.index.tz_localize(None)
        if "High" not in hist_full.columns:
            hist_full["High"] = hist_full["Close"]
            hist_full["Low"] = hist_full["Close"]
    return hist_full


def is_trend_overlay_enabled():
    """Read overlay flag from session (survives reruns triggered before toggle renders)."""
    return bool(st.session_state.get("fibo_trend_inspect", True))


def _main_trend_summary_html(main_trend, fib_trends) -> str:
    """Compact one-line trend label for the controls row."""
    if not main_trend:
        return '<span class="tech-trend-slot tech-trend-empty">No trend in window</span>'
    main_trend_type = main_trend["type"]
    trend_cls = "trend-bull" if main_trend_type == "Bullish" else "trend-bear"
    trend_icon = get_trend_icon_html(main_trend_type)
    return (
        f'<span class="tech-trend-slot tech-trend-line {trend_cls}">'
        f"{trend_icon}<b>{main_trend_type}</b> · "
        f"{main_trend['f_start'].strftime('%Y-%m-%d')} → {main_trend['f_end'].strftime('%Y-%m-%d')} · "
        f"{main_trend['move_pct'] * 100:+.1f}% · {len(fib_trends)} trend(s)"
        "</span>"
    )


def _bump_start_forward():
    opts = st.session_state["_tech_month_options"]
    idx_start = opts.index(st.session_state["sel_start_ui"])
    idx_end = opts.index(st.session_state["sel_end_ui"])
    st.session_state["sel_start_ui"] = opts[min(idx_start + 3, idx_end)]
    mark_preserve_table_selection()


def _bump_end_backward():
    opts = st.session_state["_tech_month_options"]
    idx_start = opts.index(st.session_state["sel_start_ui"])
    idx_end = opts.index(st.session_state["sel_end_ui"])
    st.session_state["sel_end_ui"] = opts[max(idx_end - 3, idx_start)]
    mark_preserve_table_selection()


def _apply_reanalyse():
    st.session_state["calc_fib_start"] = st.session_state["sel_start_ui"]
    st.session_state["calc_fib_end"] = st.session_state["sel_end_ui"]
    mark_preserve_table_selection()


def _render_tech_controls_row(month_options, main_trend, fib_trends):
    """One row: trend summary · From/To window · Re-Analyse · Trend overlay (right)."""
    st.session_state["_tech_month_options"] = month_options

    st.markdown('<div class="tech-controls-anchor"></div>', unsafe_allow_html=True)
    (
        t_col_trend,
        t_col_start_sel,
        t_col_start_btn,
        t_col_end_btn,
        t_col_end_sel,
        t_col_action,
        t_col_toggle,
    ) = st.columns(
        [2.45, 0.82, 0.26, 0.26, 0.82, 0.78, 0.72],
        gap="small",
        vertical_alignment="center",
    )

    with t_col_trend:
        st.markdown(_main_trend_summary_html(main_trend, fib_trends), unsafe_allow_html=True)

    with t_col_start_sel:
        st.selectbox(
            "From",
            options=month_options,
            key="sel_start_ui",
            label_visibility="collapsed",
        )
    with t_col_start_btn:
        st.button(
            "»",
            help="Move start forward 3 months",
            use_container_width=True,
            on_click=_bump_start_forward,
        )
    with t_col_end_btn:
        st.button(
            "«",
            help="Move end back 3 months",
            use_container_width=True,
            on_click=_bump_end_backward,
        )
    with t_col_end_sel:
        st.selectbox(
            "To",
            options=month_options,
            key="sel_end_ui",
            label_visibility="collapsed",
        )

    st.session_state["ui_fib_start"] = st.session_state["sel_start_ui"]
    st.session_state["ui_fib_end"] = st.session_state["sel_end_ui"]

    window_changed = (
        st.session_state["sel_start_ui"] != st.session_state["calc_fib_start"]
        or st.session_state["sel_end_ui"] != st.session_state["calc_fib_end"]
    )

    with t_col_action:
        st.button(
            "Re-Analyse",
            disabled=not window_changed,
            help="Recalculate Fibonacci levels and trends for the selected time window",
            use_container_width=True,
            on_click=_apply_reanalyse,
        )

    with t_col_toggle:
        st.toggle("Trend overlay", value=True, key="fibo_trend_inspect")


def _compute_chart_data(hist_full):
    calc_mask = (hist_full.index >= pd.to_datetime(st.session_state["calc_fib_start"])) & (
        hist_full.index
        <= (pd.to_datetime(st.session_state["calc_fib_end"]) + pd.offsets.MonthEnd(0))
    )
    calc_hist = hist_full.loc[calc_mask]
    fib_trends = find_multiple_trends(calc_hist, max_trends=4, strong_threshold=0.05)
    main_trend = fib_trends[0] if fib_trends else None
    dynamic_fibs, fib_anchor = compute_fibonacci_levels(calc_hist, main_trend)

    ui_start = st.session_state.get("ui_fib_start", st.session_state["sel_start_ui"])
    ui_end = st.session_state.get("ui_fib_end", st.session_state["sel_end_ui"])
    vis_mask = (hist_full.index >= pd.to_datetime(ui_start)) & (
        hist_full.index <= (pd.to_datetime(ui_end) + pd.offsets.MonthEnd(0))
    )
    vis_hist = hist_full.loc[vis_mask]
    return vis_hist, fib_trends, main_trend, dynamic_fibs, fib_anchor


def _render_detail_sidebar(pick, selected_ticker, dynamic_fibs, fib_anchor):
    st.markdown('<div class="tech-sidebar-anchor"></div>', unsafe_allow_html=True)
    curr_p = pick["data"]["🌐 Price"]
    export_symbols = st.session_state.get("selected_symbols") or []
    export_window_start = st.session_state.get("sel_start_ui")
    export_window_end = st.session_state.get("sel_end_ui")
    export_ready = bool(export_symbols and export_window_start and export_window_end)
    export_data = ""
    if export_ready:
        export_data = build_multi_export_datasets(
            export_symbols,
            export_window_start,
            export_window_end,
            st.session_state.all_results,
        )
    export_label = (
        f"Export ({len(export_symbols)})"
        if export_symbols
        else "Export Datasets"
    )
    st.download_button(
        label=export_label,
        data=export_data,
        file_name=(
            f"Analysis_{len(export_symbols)}_symbols_"
            f"{export_window_start}_{export_window_end}.txt"
            if export_ready
            else "Analysis.txt"
        ),
        mime="text/plain",
        use_container_width=True,
        disabled=not export_ready,
        on_click=mark_preserve_table_selection,
        help=(
            "Export technical datasets for all selected table rows "
            f"using the current From–To window ({export_window_start or '—'} → "
            f"{export_window_end or '—'})."
        ),
    )

    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;margin:0.2rem 0 0.15rem 0;">Metrics</p>',
        unsafe_allow_html=True,
    )
    try:
        target = pick["data"].get("Est Target")
        if target is None:
            est_target, _, _ = get_symbol_metadata(selected_ticker)
            target = est_target or 0
            pick["data"]["Est Target"] = target
            if target and curr_p:
                pick["data"]["Upside %"] = ((target / curr_p) - 1) * 100
        if target:
            up_val = ((target / curr_p) - 1) * 100
            chip_cls = "metric-chip" if up_val > 0 else "metric-chip down"
            arrow = "↑" if up_val > 0 else "↓"
            st.markdown(
                f'<div class="{chip_cls}">Target {target:.2f} $ · {arrow} {abs(up_val):.1f}% vs {curr_p:.2f} $</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Analyst target not loaded")
    except Exception:
        st.caption("Analyst target unavailable")

    div_y = pick["data"].get("Div Yield")
    if div_y is not None and div_y > 0:
        st.markdown(
            f'<div class="metric-chip div">Div yield {div_y:.1f}%</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;margin:0.25rem 0 0.1rem 0;">Fibonacci</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{st.session_state['calc_fib_start']} – {st.session_state['calc_fib_end']} · {fib_anchor}"
    )
    fib_lines = []
    for label, val in dynamic_fibs.items():
        prox = abs(curr_p - val) / val * 100
        prefix = "🎯" if prox < 1.5 else "·"
        fib_lines.append(f"{prefix} {label}: {val:.2f}")
    st.markdown(
        "<span style='font-size:0.78rem;line-height:1.35'>" + "<br>".join(fib_lines) + "</span>",
        unsafe_allow_html=True,
    )


def _ensure_analyst_data(selected_ticker, pick):
    if selected_ticker in st.session_state.get("enriched_symbols", set()):
        return pick
    prioritize_metadata_symbol(selected_ticker)
    if selected_ticker not in st.session_state.get("enriched_symbols", set()):
        with st.spinner(f"Loading analyst data for {selected_ticker}..."):
            enrich_symbol_metadata(st.session_state.all_results, selected_ticker)
    return next(
        (item for item in st.session_state.all_results if item["data"]["Symbol"] == selected_ticker),
        pick,
    )


def render_detail_panel():
    """Chart, Fibonacci, and export for the selected table row."""
    ticker_liste = st.session_state.get("ticker_liste", [])
    if not ticker_liste:
        return

    _sync_ticker_selection(ticker_liste)
    selected_ticker = st.session_state.selected_symbol
    pick = next(
        (item for item in st.session_state.all_results if item["data"]["Symbol"] == selected_ticker),
        None,
    )
    if not pick:
        st.error("Selected ticker could not be validated in session.")
        return

    pick = _ensure_analyst_data(selected_ticker, pick)
    hist_full = _load_hist_for_ticker(selected_ticker, pick)
    available_months = hist_full.index.to_period("M").unique()
    month_options = [d.strftime("%Y-%m") for d in available_months]
    _ensure_month_range(month_options)

    st.markdown(
        f'<p class="tech-header">{selected_ticker} — Technical Analysis</p>',
        unsafe_allow_html=True,
    )

    vis_hist, fib_trends, main_trend, dynamic_fibs, fib_anchor = _compute_chart_data(hist_full)
    _render_tech_controls_row(month_options, main_trend, fib_trends)
    inspect_active = is_trend_overlay_enabled()

    chart_col, sidebar_col = st.columns([3.2, 0.8])
    with chart_col:
        chart_key = (
            f"ta_chart_{selected_ticker}_{st.session_state['ui_fib_start']}_"
            f"{st.session_state['ui_fib_end']}_{int(inspect_active)}"
        )
        st.plotly_chart(
            create_chart(selected_ticker, vis_hist, dynamic_fibs, fib_trends, inspect_active),
            use_container_width=True,
            key=chart_key,
        )
    with sidebar_col:
        _render_detail_sidebar(pick, selected_ticker, dynamic_fibs, fib_anchor)
