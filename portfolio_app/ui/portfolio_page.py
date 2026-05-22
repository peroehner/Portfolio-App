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
    portfolio_metadata_progress,
    start_metadata_background_load,
)
from portfolio_app.session_keys import (
    REFRESH_CLEAR_KEYS,
    clear_portfolio_table_widget,
    clear_session_keys,
)
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


def load_portfolio_into_session(df_port):
    """Fetch prices and build session results when portfolio file changes."""
    unique_symbols = tuple(sorted(df_port["Symbol"].unique().tolist()))
    needs_eur = (df_port["Currency"] == "EUR").any()
    eur_rate = get_exchange_rate() if needs_eur else None

    with st.spinner("Loading prices..."):
        bulk_close = fetch_bulk_close(unique_symbols, TABLE_HISTORY_PERIOD)
        hist_by_symbol = build_hist_by_symbol(bulk_close, unique_symbols)

    results_temp, total_depot_value, total_depot_cost, total_depot_target = (
        build_portfolio_results(df_port, hist_by_symbol, eur_rate, metadata_map=None)
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
    start_metadata_background_load(unique_symbols)


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


def render_portfolio_page(kpi_col, df_port, portfolio_name, refresh_clicked):
    """Load portfolio data, show KPIs, table, and divider before detail panel."""
    if (
        "current_loaded_name" not in st.session_state
        or st.session_state.current_loaded_name != portfolio_name
    ):
        st.session_state.current_loaded_name = portfolio_name
        load_portfolio_into_session(df_port)

    render_kpi_strip(kpi_col, df_port, portfolio_name)
    handle_refresh(refresh_clicked)

    if "all_results" in st.session_state and len(st.session_state.all_results) > 0:
        portfolio_metadata_progress()
        render_portfolio_table_section()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
