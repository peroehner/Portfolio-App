"""Portfolio load, KPI strip, table, and refresh handling."""
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
    start_metadata_background_load,
    start_metadata_for_new_symbols,
)
from portfolio_app.data.valuation_data import (
    fetch_portfolio_valuation_parallel,
    get_symbol_valuation,
)
from portfolio_app.data.valuation_metadata import (
    apply_valuation_to_results,
    start_valuation_background_load,
    start_valuation_for_new_symbols,
    valuation_map_from_results,
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
from portfolio_app.ui.table import render_portfolio_table_section


def _clear_analysis_session():
    st.session_state.all_results = []
    st.session_state.total_depot_value = 0.0
    st.session_state.total_depot_cost = 0.0
    st.session_state.total_depot_target = 0.0
    st.session_state.total_depot_div_income = 0.0
    st.session_state.portfolio_symbols = tuple()
    st.session_state.ticker_liste = []
    st.session_state.selected_symbols = []
    st.session_state.table_sel_rows = []


def load_portfolio_into_session(df_port, *, refetch_metadata: bool = True):
    """Fetch prices and build session results when portfolio holdings change."""
    if df_port is None or df_port.empty:
        _clear_analysis_session()
        return

    unique_symbols = tuple(sorted(df_port["Symbol"].unique().tolist()))
    prior_symbols = set(st.session_state.get("portfolio_symbols", ()))
    needs_eur = (df_port["Currency"] == "EUR").any()
    eur_rate = get_exchange_rate() if needs_eur else None

    metadata_map = None
    valuation_map = None
    if not refetch_metadata and "all_results" in st.session_state:
        metadata_map = metadata_map_from_results(st.session_state.all_results)
        valuation_map = valuation_map_from_results(st.session_state.all_results)

    with st.spinner("Loading prices..."):
        bulk_close = fetch_bulk_close(unique_symbols, TABLE_HISTORY_PERIOD)
        hist_by_symbol = build_hist_by_symbol(bulk_close, unique_symbols)

    (
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
    ) = build_portfolio_results(df_port, hist_by_symbol, eur_rate, metadata_map=metadata_map)

    apply_valuation_to_results(results_temp, valuation_map or {})

    st.session_state.all_results = results_temp
    st.session_state.total_depot_value = total_depot_value
    st.session_state.total_depot_cost = total_depot_cost
    st.session_state.total_depot_target = total_depot_target
    st.session_state.total_depot_div_income = total_depot_div_income
    st.session_state.ticker_liste = [x["data"]["Symbol"] for x in results_temp]
    if results_temp:
        first_symbol = results_temp[0]["data"]["Symbol"]
        st.session_state.selected_symbol = first_symbol
        st.session_state.selected_symbols = []
        st.session_state.table_sel_rows = []
        st.session_state.ticker_index = 0
        st.session_state.clear_table_selection = True
        st.session_state["fibo_needs_refresh"] = True
        clear_portfolio_table_widget()
    st.session_state.portfolio_symbols = unique_symbols
    if refetch_metadata:
        start_metadata_background_load(unique_symbols)
        start_valuation_background_load(unique_symbols)
    else:
        new_symbols = set(unique_symbols) - prior_symbols
        if new_symbols:
            start_metadata_for_new_symbols(tuple(sorted(new_symbols)))
            start_valuation_for_new_symbols(tuple(sorted(new_symbols)))


def handle_refresh(refresh_clicked):
    if not refresh_clicked:
        return
    fetch_bulk_close.clear()
    get_ticker_ohlc_history.clear()
    get_exchange_rate.clear()
    get_symbol_metadata.clear()
    fetch_portfolio_metadata_parallel.clear()
    get_symbol_valuation.clear()
    fetch_portfolio_valuation_parallel.clear()
    clear_session_keys(REFRESH_CLEAR_KEYS)
    clear_portfolio_table_widget()
    st.rerun()


def _analysis_key(portfolio_id: int, portfolio_name: str) -> str:
    return f"{portfolio_id}:{get_portfolio_data_version()}:{portfolio_name}"


def _holdings_symbol_set(df_port) -> frozenset:
    if df_port is None or df_port.empty:
        return frozenset()
    return frozenset(df_port["Symbol"].astype(str).str.upper().tolist())


def _needs_analysis_reload(df_port, portfolio_id: int, portfolio_name: str) -> bool:
    if get_analysis_portfolio_key() != _analysis_key(portfolio_id, portfolio_name):
        return True
    loaded = frozenset(st.session_state.get("portfolio_symbols", ()))
    return _holdings_symbol_set(df_port) != loaded


def render_portfolio_page(df_port, portfolio_name, refresh_clicked):
    """Load portfolio data and show analysis table (portfolio bar is in toolbar row)."""
    active = load_active_portfolio()
    if _needs_analysis_reload(df_port, active.portfolio_id, portfolio_name):
        st.session_state.current_loaded_name = portfolio_name
        set_analysis_portfolio_key(_analysis_key(active.portfolio_id, portfolio_name))
        refetch_metadata = consume_refetch_metadata_flag()
        load_portfolio_into_session(df_port, refetch_metadata=refetch_metadata)

    handle_refresh(refresh_clicked)

    holding_count = len(df_port) if df_port is not None and not df_port.empty else 0
    result_count = len(st.session_state.get("all_results") or [])
    if holding_count > 0 and result_count == 0:
        st.caption("Holdings loaded — market data pending.")

    if df_port is None or df_port.empty:
        st.info(
            "No symbols yet — tap **⋮** for **Add symbol**, **Save portfolio**, or **📁** CSV import."
        )

    render_portfolio_table_section()
