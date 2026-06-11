"""Portfolio load, KPI strip, table, and refresh handling."""
import pandas as pd
import streamlit as st

from portfolio_app.services.portfolio_sync import (
    load_analysis_from_snapshots,
    run_network_refresh,
)
from portfolio_app.services.session_context import (
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


def load_portfolio_into_session(df_port, *, from_network: bool = False):
    """Build session results from DB snapshots (default) or Yahoo refresh."""
    from portfolio_app.config import DB_PATH
    from portfolio_app.domain.models import SYNC_STATUS_FAILED, SYNC_STATUS_PARTIAL
    from portfolio_app.services.portfolio_sync import format_last_sync_label

    active = load_active_portfolio()
    if df_port is None or df_port.empty:
        _clear_analysis_session()
        st.session_state.pop("portfolio_last_sync_label", None)
        return

    if from_network:
        with st.spinner("Loading financial data…"):
            sync_state = run_network_refresh(
                df_port, active.portfolio_id
            )
    else:
        sync_state = load_analysis_from_snapshots(df_port, active.portfolio_id)

    st.session_state.portfolio_last_sync_label = format_last_sync_label(sync_state)
    st.session_state.portfolio_holdings_signature = _holdings_analysis_signature(df_port)

    if from_network:
        if sync_state.last_sync_status == SYNC_STATUS_FAILED:
            st.error(
                "Market data sync failed on this server. "
                f"{sync_state.last_sync_error or 'No prices returned.'} "
                f"Database: `{DB_PATH}`"
            )
        elif sync_state.last_sync_status == SYNC_STATUS_PARTIAL:
            st.warning(
                f"Partial sync ({sync_state.symbols_succeeded or 0}/"
                f"{sync_state.symbols_requested or 0} symbols). "
                f"{sync_state.last_sync_error or ''}".strip()
            )


def handle_refresh(refresh_clicked):
    if not refresh_clicked:
        return
    from portfolio_app.data.market_data import (
        fetch_bulk_close,
        fetch_portfolio_metadata_parallel,
        get_exchange_rate,
        get_symbol_metadata,
        get_ticker_ohlc_history,
    )
    from portfolio_app.data.valuation_data import (
        fetch_portfolio_valuation_parallel,
        get_symbol_valuation,
    )

    fetch_bulk_close.clear()
    get_ticker_ohlc_history.clear()
    get_exchange_rate.clear()
    get_symbol_metadata.clear()
    fetch_portfolio_metadata_parallel.clear()
    get_symbol_valuation.clear()
    fetch_portfolio_valuation_parallel.clear()
    clear_session_keys(REFRESH_CLEAR_KEYS)
    clear_portfolio_table_widget()
    st.session_state.pending_network_refresh = True
    st.session_state.pop("analysis_portfolio_key", None)
    st.rerun()


def _analysis_key(portfolio_id: int, portfolio_name: str) -> str:
    return f"{portfolio_id}:{get_portfolio_data_version()}:{portfolio_name}"


def _holdings_analysis_signature(df_port) -> tuple:
    """Fingerprint for reload — includes share/cost changes and consolidated lots."""
    if df_port is None or df_port.empty:
        return ()
    rows = []
    for _, row in df_port.sort_values(["Symbol", "PurchaseDate"]).iterrows():
        purchase = row.get("PurchaseDate")
        purchase_s = (
            pd.Timestamp(purchase).strftime("%Y-%m-%d")
            if purchase is not None and not pd.isna(purchase)
            else ""
        )
        rows.append(
            (
                str(row["Symbol"]).strip().upper(),
                round(float(row.get("Shares") or 0), 6),
                round(float(row.get("AvgCost") or 0), 6),
                purchase_s,
                round(float(row.get("TargetPrice") or 0), 6),
                str(row.get("Currency", "USD")).strip().upper(),
            )
        )
    return tuple(rows)


def _history_window_needs_resync() -> bool:
    from portfolio_app.config import SYNCED_HISTORY_MONTHS_KEY
    from portfolio_app.ui.history_controls import history_months

    synced = st.session_state.get(SYNCED_HISTORY_MONTHS_KEY)
    if synced is None:
        return False
    return history_months() != synced


def _needs_analysis_reload(df_port, portfolio_id: int, portfolio_name: str) -> bool:
    if get_analysis_portfolio_key() != _analysis_key(portfolio_id, portfolio_name):
        return True
    if st.session_state.get("pending_network_refresh"):
        return True
    if _history_window_needs_resync():
        st.session_state.pending_network_refresh = True
        return True
    loaded_sig = st.session_state.get("portfolio_holdings_signature")
    return _holdings_analysis_signature(df_port) != loaded_sig


def render_portfolio_page(df_port, portfolio_name, refresh_clicked):
    """Load portfolio data and show analysis table (portfolio bar is in toolbar row)."""
    active = load_active_portfolio()
    if _needs_analysis_reload(df_port, active.portfolio_id, portfolio_name):
        st.session_state.current_loaded_name = portfolio_name
        set_analysis_portfolio_key(_analysis_key(active.portfolio_id, portfolio_name))
        from_network = bool(st.session_state.pop("pending_network_refresh", False))
        load_portfolio_into_session(df_port, from_network=from_network)
    elif "portfolio_last_sync_label" not in st.session_state:
        from portfolio_app.services.portfolio_sync import format_last_sync_label
        from portfolio_app.storage.repository import PortfolioRepository

        sync_state = PortfolioRepository().get_sync_state(active.portfolio_id)
        st.session_state.portfolio_last_sync_label = format_last_sync_label(sync_state)

    handle_refresh(refresh_clicked)

    holding_count = len(df_port) if df_port is not None and not df_port.empty else 0
    result_count = len(st.session_state.get("all_results") or [])
    if holding_count > 0 and result_count == 0:
        st.caption("Holdings loaded — tap sync to load market data.")

    last_sync = st.session_state.get("portfolio_last_sync_label")
    if holding_count > 0 and last_sync == "Never synced":
        st.caption("Never synced — use the sync button in the toolbar to fetch market data.")

    if df_port is None or df_port.empty:
        st.info(
            "No symbols yet — tap **⋮** for **Add symbol**, **Save portfolio**, or **📁** CSV import."
        )

    render_portfolio_table_section()
