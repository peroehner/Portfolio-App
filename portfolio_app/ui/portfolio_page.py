"""Portfolio load, KPI strip, table, and refresh handling."""
import html

import streamlit as st

from portfolio_app.analysis.portfolio_build import (
    build_hist_by_symbol,
    build_portfolio_results,
)
from portfolio_app.config import TABLE_HISTORY_PERIOD
from portfolio_app.data.market_data import (
    fetch_bulk_close,
    fetch_portfolio_metadata_parallel,
    get_exchange_rate,
    get_ticker_ohlc_history,
    get_symbol_metadata,
)
from portfolio_app.data.metadata import (
    metadata_map_from_results,
    portfolio_metadata_progress,
    start_metadata_background_load,
    start_metadata_for_new_symbols,
)
from portfolio_app.services.session_context import (
    consume_refetch_metadata_flag,
    get_analysis_portfolio_key,
    get_portfolio_data_version,
    load_active_portfolio,
    set_analysis_portfolio_key,
)
from portfolio_app.session_keys import (
    REFRESH_CLEAR_KEYS,
    clear_portfolio_table_widget,
    clear_session_keys,
)
from portfolio_app.ui.holdings_editor import render_holdings_editor
from portfolio_app.ui.table import render_portfolio_table_section


def render_kpi_strip(kpi_col, df_port, portfolio_name):
    safe_filename = html.escape(str(portfolio_name))
    with kpi_col:
        st.markdown(
            f'<div class="kpi-strip">'
            f'<span class="kpi-item kpi-file" title="{safe_filename}">'
            f'<b>File</b> <span class="kpi-val">{safe_filename}</span></span>'
            f'<span class="kpi-item"><b>Symbols</b> <span class="kpi-val">{len(df_port):,}</span></span>'
            f'<span class="kpi-item"><b>Value</b> <span class="kpi-val">${st.session_state.total_depot_value:,.0f}</span></span>'
            f'<span class="kpi-item"><b>Cost</b> <span class="kpi-val">${st.session_state.total_depot_cost:,.0f}</span></span>'
            f'<span class="kpi-item"><b>Target</b> <span class="kpi-val">${st.session_state.total_depot_target:,.0f}</span></span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def load_portfolio_into_session(df_port, *, refetch_metadata: bool = True):
    """Fetch prices and build session results when portfolio holdings change."""
    unique_symbols = tuple(sorted(df_port["Symbol"].unique().tolist()))
    prior_symbols = set(st.session_state.get("portfolio_symbols", ()))
    needs_eur = (df_port["Currency"] == "EUR").any()
    eur_rate = get_exchange_rate() if needs_eur else None

    metadata_map = None
    if not refetch_metadata and "all_results" in st.session_state:
        metadata_map = metadata_map_from_results(st.session_state.all_results)

    with st.spinner("Loading prices..."):
        bulk_close = fetch_bulk_close(unique_symbols, TABLE_HISTORY_PERIOD)
        hist_by_symbol = build_hist_by_symbol(bulk_close, unique_symbols)

    results_temp, total_depot_value, total_depot_cost, total_depot_target = (
        build_portfolio_results(df_port, hist_by_symbol, eur_rate, metadata_map=metadata_map)
    )

    st.session_state.all_results = results_temp
    st.session_state.total_depot_value = total_depot_value
    st.session_state.total_depot_cost = total_depot_cost
    st.session_state.total_depot_target = total_depot_target
    st.session_state.ticker_liste = [x["data"]["Symbol"] for x in results_temp]
    if results_temp:
        first_symbol = results_temp[0]["data"]["Symbol"]
        st.session_state.selected_symbol = first_symbol
        st.session_state.selected_symbols = []
        st.session_state.table_sel_rows = []
        st.session_state.ticker_index = 0
        st.session_state.clear_table_selection = True
        clear_portfolio_table_widget()
    st.session_state.portfolio_symbols = unique_symbols
    if refetch_metadata:
        start_metadata_background_load(unique_symbols)
    else:
        new_symbols = set(unique_symbols) - prior_symbols
        if new_symbols:
            start_metadata_for_new_symbols(tuple(sorted(new_symbols)))


def handle_refresh(refresh_clicked):
    if not refresh_clicked:
        return
    fetch_bulk_close.clear()
    get_ticker_ohlc_history.clear()
    get_exchange_rate.clear()
    get_symbol_metadata.clear()
    fetch_portfolio_metadata_parallel.clear()
    clear_session_keys(REFRESH_CLEAR_KEYS)
    clear_portfolio_table_widget()
    st.rerun()


def _analysis_key(portfolio_name: str) -> str:
    active = load_active_portfolio()
    return f"{active.portfolio_id}:{get_portfolio_data_version()}:{portfolio_name}"


def render_portfolio_page(kpi_col, df_port, portfolio_name, refresh_clicked):
    """Load portfolio data, show KPIs, holdings editor, analysis table."""
    analysis_key = _analysis_key(portfolio_name)
    if get_analysis_portfolio_key() != analysis_key:
        st.session_state.current_loaded_name = portfolio_name
        set_analysis_portfolio_key(analysis_key)
        refetch_metadata = consume_refetch_metadata_flag()
        load_portfolio_into_session(df_port, refetch_metadata=refetch_metadata)

    render_kpi_strip(kpi_col, df_port, portfolio_name)
    handle_refresh(refresh_clicked)

    if "all_results" in st.session_state and len(st.session_state.all_results) > 0:
        st.subheader("Analysis")
        render_portfolio_table_section()
        portfolio_metadata_progress()

    render_holdings_editor()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
