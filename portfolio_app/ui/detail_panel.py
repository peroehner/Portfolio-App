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
from portfolio_app.services.ta_woi_service import (
    STICKY_WOI_CHECKBOX_KEY,
    STICKY_WOI_SESSION_KEY,
    export_windows_for_symbols,
    ensure_ta_window_for_symbol,
    get_default_window,
    get_sticky_woi,
    load_sticky_woi_for_portfolio,
    on_sticky_woi_toggle,
    on_window_controls_change,
    sticky_woi_note_html,
)
from portfolio_app.services.session_context import load_active_portfolio


def _analysis_symbols() -> list[str]:
    """Symbols to browse in Technical Analysis (table selection, else portfolio list)."""
    selected = [s for s in (st.session_state.get("selected_symbols") or []) if s]
    if selected:
        return selected
    if st.session_state.get("table_sel_rows"):
        focus = st.session_state.get("selected_symbol")
        if focus:
            return [focus]
        return []
    focus = st.session_state.get("selected_symbol")
    ticker_liste = st.session_state.get("ticker_liste") or []
    if focus and focus in ticker_liste:
        return [focus]
    return list(ticker_liste)


def _ta_chip_focus_locked(symbols: list[str]) -> bool:
    """True when the user explicitly picked the active symbol via a TA chip."""
    chart_sym = str(st.session_state.get("ta_chart_symbol") or "").strip()
    selected = str(st.session_state.get("selected_symbol") or "").strip()
    return bool(chart_sym and chart_sym == selected and chart_sym in symbols)


def _resolve_ta_chart_symbol(symbols: list[str]) -> str:
    """Single source of truth for which symbol the TA panel charts."""
    if not symbols:
        return ""
    selected = str(st.session_state.get("selected_symbol") or "").strip()
    chart_sym = str(st.session_state.get("ta_chart_symbol") or "").strip()
    if (
        selected in symbols
        and chart_sym in symbols
        and selected != chart_sym
        and not _ta_chip_focus_locked(symbols)
    ):
        sym = selected
    elif chart_sym in symbols:
        sym = chart_sym
    elif selected in symbols:
        sym = selected
    else:
        sym = symbols[0]
    idx = symbols.index(sym)
    st.session_state.ta_nav_index = idx
    st.session_state.ta_chart_symbol = sym
    st.session_state.selected_symbol = sym
    st.session_state["_ta_sync_focus"] = sym
    st.session_state["_ta_selection_key"] = tuple(symbols)
    return sym


def _sync_ta_chart_symbol(symbols: list[str]) -> str:
    return _resolve_ta_chart_symbol(symbols)


def _ta_active_symbol(symbols: list[str]) -> tuple[str, int]:
    """Symbol and index for the highlighted TA chip."""
    if not symbols:
        return "", 0
    chart_sym = str(st.session_state.get("ta_chart_symbol") or "").strip()
    if chart_sym in symbols:
        idx = symbols.index(chart_sym)
        return chart_sym, idx
    idx = int(st.session_state.get("ta_nav_index", 0))
    idx = max(0, min(idx, len(symbols) - 1))
    return symbols[idx], idx


def _symbol_window(symbols: list[str], index: int, *, window: int = 7) -> tuple[int, int]:
    half = window // 2
    start = max(0, index - half)
    end = min(len(symbols), start + window)
    start = max(0, end - window)
    return start, end


def _ta_select_symbol(idx: int) -> None:
    symbols = st.session_state.get("_ta_nav_symbols") or []
    if 0 <= idx < len(symbols):
        sym = symbols[idx]
        st.session_state.ta_nav_index = idx
        st.session_state.ta_chart_symbol = sym
        st.session_state.selected_symbol = sym
        st.session_state["_ta_sync_focus"] = sym
        # Survives portfolio grid sync on the rerun triggered by this click.
        st.session_state["_ta_pending_chart_symbol"] = sym
        mark_preserve_table_selection()
        st.rerun()


def _apply_ta_pending_symbol(symbols: list[str]) -> None:
    """Re-apply a TA chip click after portfolio table sync on the same rerun."""
    pending = str(st.session_state.pop("_ta_pending_chart_symbol", "") or "").strip()
    if not pending or pending not in symbols:
        return
    st.session_state.ta_nav_index = symbols.index(pending)
    st.session_state.ta_chart_symbol = pending
    st.session_state.selected_symbol = pending
    st.session_state["_ta_sync_focus"] = pending


def _ta_export_bundle() -> tuple[str, str, str, bool, str]:
    export_symbols = st.session_state.get("selected_symbols") or []
    default_start, default_end = get_default_window()
    if not default_start or not default_end:
        default_start = st.session_state.get("sel_start_ui")
        default_end = st.session_state.get("sel_end_ui")
    export_ready = bool(export_symbols and default_start and default_end)
    export_data = ""
    if export_ready:
        symbol_windows = export_windows_for_symbols(
            export_symbols,
            default_start,
            default_end,
        )
        export_data = build_multi_export_datasets(
            export_symbols,
            default_start,
            default_end,
            st.session_state.all_results,
            symbol_windows=symbol_windows,
        )
    export_label = (
        f"Export ({len(export_symbols)})"
        if export_symbols
        else "Export"
    )
    file_name = (
        f"Analysis_{len(export_symbols)}_symbols_"
        f"{default_start}_{default_end}.txt"
        if export_ready
        else "Analysis.txt"
    )
    help_text = (
        "Export technical datasets for all selected table rows using the default "
        f"From–To window ({default_start or '—'} → {default_end or '—'}). "
        "Symbols with a pinned WoI use their saved range instead."
    )
    return export_label, export_data, file_name, export_ready, help_text


def _render_symbol_nav_bar(symbols: list[str]) -> None:
    st.session_state["_ta_nav_symbols"] = symbols
    active_sym, active_idx = _ta_active_symbol(symbols)
    st.session_state.ta_nav_index = active_idx
    export_label, export_data, export_file, export_ready, export_help = _ta_export_bundle()
    start, end = _symbol_window(symbols, active_idx)

    st.markdown('<div class="ta-symbol-nav-row-anchor"></div>', unsafe_allow_html=True)
    list_col, export_col = st.columns([5.65, 1.05], gap="small", vertical_alignment="center")

    with list_col:
        st.markdown('<div class="ta-symbol-list-frame"></div>', unsafe_allow_html=True)

        weights: list[float] = []
        if start > 0:
            weights.append(0.2)
        weights.extend([1.0] * (end - start))
        if end < len(symbols):
            weights.append(0.2)

        cols = st.columns(weights, gap="small", vertical_alignment="center")
        col_i = 0

        if start > 0:
            with cols[col_i]:
                st.markdown('<span class="ta-sym-ellipsis">…</span>', unsafe_allow_html=True)
            col_i += 1

        for i in range(start, end):
            sym = symbols[i]
            is_active = sym == active_sym
            with cols[col_i]:
                if is_active:
                    st.markdown(
                        f'<span class="ta-sym-chip ta-sym-chip-active" title="Charting {sym}">{sym}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(
                        sym,
                        key=f"ta_sym_{i}_{sym}",
                        use_container_width=True,
                    ):
                        _ta_select_symbol(i)
            col_i += 1

        if end < len(symbols):
            with cols[col_i]:
                st.markdown('<span class="ta-sym-ellipsis">…</span>', unsafe_allow_html=True)

    with export_col:
        st.markdown('<div class="ta-export-outside-anchor"></div>', unsafe_allow_html=True)
        st.download_button(
            label=export_label,
            data=export_data,
            file_name=export_file,
            mime="text/plain",
            use_container_width=True,
            disabled=not export_ready,
            key="ta_export_btn",
            on_click=mark_preserve_table_selection,
            help=export_help,
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
        from portfolio_app.services.ta_woi_service import set_default_window

        set_default_window(start_default, end_default)
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
    """Compact trend card for the controls row."""
    if not main_trend:
        return (
            '<div class="ta-trend-card empty tech-trend-slot">'
            '<span>No significant trend in window</span>'
            "</div>"
        )
    main_trend_type = main_trend["type"]
    tone = "bull" if main_trend_type == "Bullish" else "bear"
    trend_icon = get_trend_icon_html(main_trend_type)
    move_pct = main_trend["move_pct"] * 100
    trend_id = main_trend.get("id", "T1")
    date_range = (
        f"{main_trend['f_start'].strftime('%Y-%m-%d')} → "
        f"{main_trend['f_end'].strftime('%Y-%m-%d')}"
    )
    trend_count = len(fib_trends)
    trend_noun = "trend" if trend_count == 1 else "trends"
    return (
        f'<div class="ta-trend-card {tone} tech-trend-slot">'
        f'<div class="ta-trend-leading">{trend_icon}</div>'
        f'<div class="ta-trend-body">'
        f'<div class="ta-trend-top">'
        f'<span class="ta-trend-badge">{main_trend_type}</span>'
        f'<span class="ta-trend-id">{trend_id}</span>'
        f"</div>"
        f'<div class="ta-trend-foot">'
        f'<span class="ta-trend-range">{date_range}</span>'
        f"</div>"
        f"</div>"
        f'<div class="ta-trend-stats">'
        f'<span class="ta-trend-pct">{move_pct:+.1f}%</span>'
        f'<span class="ta-trend-count">{trend_count} {trend_noun}</span>'
        f"</div>"
        f"</div>"
    )


def _bump_start_forward():
    opts = st.session_state["_tech_month_options"]
    idx_start = opts.index(st.session_state["sel_start_ui"])
    idx_end = opts.index(st.session_state["sel_end_ui"])
    st.session_state["sel_start_ui"] = opts[min(idx_start + 3, idx_end)]
    on_window_controls_change()
    mark_preserve_table_selection()


def _bump_end_backward():
    opts = st.session_state["_tech_month_options"]
    idx_start = opts.index(st.session_state["sel_start_ui"])
    idx_end = opts.index(st.session_state["sel_end_ui"])
    st.session_state["sel_end_ui"] = opts[max(idx_end - 3, idx_start)]
    on_window_controls_change()
    mark_preserve_table_selection()


def _apply_reanalyse():
    st.session_state["calc_fib_start"] = st.session_state["sel_start_ui"]
    st.session_state["calc_fib_end"] = st.session_state["sel_end_ui"]
    on_window_controls_change()
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
            on_change=on_window_controls_change,
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
            on_change=on_window_controls_change,
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

    symbol = str(st.session_state.get("ta_chart_symbol") or "").strip().upper()
    pin_col, pin_note_col = st.columns([0.72, 4.5], gap="small", vertical_alignment="center")
    with pin_col:
        st.checkbox(
            "Pin WoI",
            key=STICKY_WOI_CHECKBOX_KEY,
            on_change=on_sticky_woi_toggle,
            help=(
                "Pin the current From–To window to this symbol. "
                "Uncheck to remove and use the default TA window again."
            ),
        )
    with pin_note_col:
        sticky_note = sticky_woi_note_html(symbol)
        if sticky_note:
            st.markdown(sticky_note, unsafe_allow_html=True)


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


def _target_upside_pct(target, curr_p):
    try:
        if target is None or curr_p in (None, 0):
            return None
        if pd.isna(target) or pd.isna(curr_p):
            return None
        return ((float(target) / float(curr_p)) - 1) * 100
    except (TypeError, ValueError):
        return None


def _metric_card_html(label, target, curr_p):
    up_val = _target_upside_pct(target, curr_p)
    if up_val is None:
        return ""
    tone = "up" if up_val > 0 else ("down" if up_val < 0 else "flat")
    arrow = "↑" if up_val > 0 else ("↓" if up_val < 0 else "→")
    return (
        f'<div class="ta-metric-card {tone}">'
        f'<div class="ta-metric-top">'
        f'<span class="ta-metric-label">{label}</span>'
        f'<span class="ta-metric-value">${float(target):,.2f}</span>'
        f"</div>"
        f'<div class="ta-metric-foot">'
        f'<span class="ta-metric-delta">{arrow} {abs(up_val):.1f}%</span>'
        f'<span class="ta-metric-ref">vs ${float(curr_p):,.2f}</span>'
        f"</div>"
        f"</div>"
    )


def _fib_rows_html(dynamic_fibs, curr_p):
    if not dynamic_fibs or curr_p in (None, 0) or pd.isna(curr_p):
        return '<div class="ta-fib-empty">No levels in window</div>'

    rows = []
    nearest_label = None
    nearest_prox = float("inf")
    for label, val in dynamic_fibs.items():
        try:
            prox = abs(float(curr_p) - float(val)) / float(val) * 100 if val else float("inf")
        except (TypeError, ValueError, ZeroDivisionError):
            prox = float("inf")
        if prox < nearest_prox:
            nearest_prox = prox
            nearest_label = label

    for label, val in dynamic_fibs.items():
        try:
            prox = abs(float(curr_p) - float(val)) / float(val) * 100 if val else float("inf")
            price = float(val)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        row_cls = "ta-fib-row"
        if prox < 1.5:
            row_cls += " near"
        elif label == nearest_label and prox < 4.0:
            row_cls += " closest"
        short_label = label.replace(" Retracement", "").replace(" Center Line", "")
        prox_html = (
            f'<span class="ta-fib-prox">{prox:.1f}%</span>' if prox < 6.0 else ""
        )
        rows.append(
            f'<div class="{row_cls}">'
            f'<span class="ta-fib-lbl">{short_label}</span>'
            f'<span class="ta-fib-val">${price:,.2f}</span>'
            f"{prox_html}"
            f"</div>"
        )
    return '<div class="ta-fib-list">' + "".join(rows) + "</div>"


def _resolve_est_target(pick, selected_ticker, curr_p):
    try:
        target = pick["data"].get("Est Target")
        if target is None:
            est_target, _, _ = get_symbol_metadata(selected_ticker)
            target = est_target or 0
            pick["data"]["Est Target"] = target
            if target and curr_p:
                pick["data"]["Upside %"] = _target_upside_pct(target, curr_p)
        return target if target else None
    except Exception:
        return None


def _render_detail_sidebar(pick, selected_ticker, dynamic_fibs, fib_anchor):
    st.markdown('<div class="tech-sidebar-anchor"></div>', unsafe_allow_html=True)
    curr_p = pick["data"]["🌐 Price"]
    metric_cards = []

    try:
        price_txt = "—"
        if curr_p is not None and not pd.isna(curr_p):
            price_txt = f"${float(curr_p):,.2f}"
        metric_cards.append(
            f'<div class="ta-price-pill"><span>Current</span><strong>{price_txt}</strong></div>'
        )

        est_target = _resolve_est_target(pick, selected_ticker, curr_p)
        if est_target:
            metric_cards.append(_metric_card_html("Est Target", est_target, curr_p))
        else:
            metric_cards.append(
                '<div class="ta-metric-empty">Analyst target not loaded</div>'
            )

        personal_target = pick["data"].get("📈 Target")
        if personal_target is not None and not pd.isna(personal_target):
            metric_cards.append(
                _metric_card_html("Personal Target", personal_target, curr_p)
            )

        div_y = pick["data"].get("Div Yield")
        if div_y is not None and not pd.isna(div_y) and float(div_y) > 0:
            metric_cards.append(
                f'<div class="ta-metric-card div">'
                f'<div class="ta-metric-top">'
                f'<span class="ta-metric-label">Div Yield</span>'
                f'<span class="ta-metric-value">{float(div_y):.1f}%</span>'
                f"</div>"
                f'<div class="ta-metric-foot">'
                f'<span class="ta-metric-ref">annual estimate</span>'
                f"</div>"
                f"</div>"
            )
    except Exception:
        metric_cards = ['<div class="ta-metric-empty">Metrics unavailable</div>']

    window_start = st.session_state["calc_fib_start"]
    window_end = st.session_state["calc_fib_end"]
    sticky_badge = (
        '<span class="ta-fib-sticky-badge">Pin WoI</span>'
        if get_sticky_woi(selected_ticker)
        else ""
    )
    st.markdown(
        f"""
        <div class="ta-side-panel">
          <div class="ta-side-section">
            <div class="ta-side-heading">Metrics</div>
            <div class="ta-metric-stack">{"".join(metric_cards)}</div>
          </div>
          <div class="ta-side-section">
            <div class="ta-side-heading">Fibonacci</div>
            <div class="ta-fib-window">
              <span class="ta-fib-range">{window_start} → {window_end}</span>
              {sticky_badge}
            </div>
            <div class="ta-fib-anchor">{fib_anchor}</div>
            {_fib_rows_html(dynamic_fibs, curr_p)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ensure_analyst_data(selected_ticker, pick):
    if selected_ticker in st.session_state.get("enriched_symbols", set()):
        return pick
    prioritize_metadata_symbol(selected_ticker)
    if selected_ticker not in st.session_state.get("enriched_symbols", set()):
        with st.spinner(f"Loading analyst estimates for {selected_ticker}..."):
            enrich_symbol_metadata(st.session_state.all_results, selected_ticker)
    return next(
        (item for item in st.session_state.all_results if item["data"]["Symbol"] == selected_ticker),
        pick,
    )


def render_detail_panel():
    """Chart, Fibonacci, and export for the selected table row."""
    ticker_liste = st.session_state.get("ticker_liste", [])
    if not ticker_liste:
        st.markdown(
            """
            <div class="section-empty-state">
              <p class="section-empty-title">No symbol to analyze yet</p>
              <p class="section-empty-body">
                Add holdings in <strong>Portfolio Screener</strong> above, then select table rows
                and click a symbol chip below to view its chart.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    symbols = _analysis_symbols()
    _apply_ta_pending_symbol(symbols)
    if not symbols:
        st.markdown(
            """
            <div class="section-empty-state">
              <p class="section-empty-title">No symbol selected</p>
              <p class="section-empty-body">
                Select one or more rows in the <strong>Portfolio Screener</strong> table above.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_symbol_nav_bar(symbols)
    selected_ticker = _sync_ta_chart_symbol(symbols)

    pick = next(
        (item for item in st.session_state.all_results if item["data"]["Symbol"] == selected_ticker),
        None,
    )
    if not pick:
        st.error("Selected ticker could not be validated in session.")
        return

    pick = _ensure_analyst_data(selected_ticker, pick)
    if STICKY_WOI_SESSION_KEY not in st.session_state:
        active = load_active_portfolio()
        load_sticky_woi_for_portfolio(active.portfolio_id)
    hist_full = _load_hist_for_ticker(selected_ticker, pick)
    available_months = hist_full.index.to_period("M").unique()
    month_options = [d.strftime("%Y-%m") for d in available_months]
    ensure_ta_window_for_symbol(selected_ticker, month_options)
    _ensure_month_range(month_options)

    vis_hist, fib_trends, main_trend, dynamic_fibs, fib_anchor = _compute_chart_data(hist_full)
    _render_tech_controls_row(month_options, main_trend, fib_trends)
    inspect_active = is_trend_overlay_enabled()

    chart_col, sidebar_col = st.columns([3.2, 0.8])
    with chart_col:
        st.markdown(
            f'<div class="ta-chart-heading">'
            f'<span class="ta-chart-symbol">{selected_ticker}</span>'
            f'<span class="ta-chart-meta">Price · trends · Fibonacci</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
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
