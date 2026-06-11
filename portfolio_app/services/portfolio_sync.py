"""Load portfolio analysis from DB snapshots (startup) or Yahoo (refresh + persist)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

from portfolio_app.analysis.portfolio_build import build_portfolio_results
from portfolio_app.analysis.returns import (
    compute_annual_div_income,
    compute_position_cagr,
    holding_days_since_purchase,
    value_to_target_gap_pct,
)
from portfolio_app.analysis.valuation_scores import (
    COL_FORWARD_PE,
    COL_OP_MARGIN,
    COL_PEG,
    COL_REV_GROWTH,
    COL_TRAILING_PE,
    VALUATION_ALL_COLUMNS,
    VALUATION_RAW_COLUMNS,
    compute_portfolio_p_scores,
    metrics_from_row,
    raw_metrics_to_display,
)
from portfolio_app.config import HISTORY_MONTHS_DEFAULT, SYNCED_HISTORY_MONTHS_KEY
from portfolio_app.data.market_data import (
    clamp_history_months,
    download_close_prices,
    fetch_portfolio_metadata_parallel,
    get_exchange_rate,
)
from portfolio_app.data.valuation_data import fetch_portfolio_valuation_parallel
from portfolio_app.data.valuation_metadata import apply_valuation_to_results
from portfolio_app.domain.models import (
    SYNC_STATUS_FAILED,
    SYNC_STATUS_NEVER,
    SYNC_STATUS_PARTIAL,
    SYNC_STATUS_SUCCESS,
    PortfolioSyncState,
    SymbolFinancialSnapshot,
)
from portfolio_app.storage.repository import PortfolioRepository

_TREND_KEYS = ("5D", "1M", "6M", "12M")
_SNAPSHOT_RETURN_ATTRS = ("returns_5d", "returns_1m", "returns_6m", "returns_12m")


def format_last_sync_label(sync_state: PortfolioSyncState) -> str:
    """Human-readable last sync for KPI strip (local timezone)."""
    if sync_state.last_sync_status == SYNC_STATUS_NEVER or not sync_state.last_sync_at:
        return "Never synced"
    dt = sync_state.last_sync_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    stamp = local.strftime("%d %b %Y, %H:%M")
    req = sync_state.symbols_requested
    ok = sync_state.symbols_succeeded
    if sync_state.last_sync_status == SYNC_STATUS_FAILED:
        detail = sync_state.last_sync_error or "no symbols received prices"
        return f"Sync failed · {stamp} — {detail}"
    if sync_state.last_sync_status == SYNC_STATUS_PARTIAL and req and ok is not None:
        return f"Partial sync · {stamp} ({ok}/{req} symbols)"
    if sync_state.last_sync_error:
        return f"{stamp} — {sync_state.last_sync_error}"
    return stamp


def snapshots_by_symbol(
    snapshots: Iterable[SymbolFinancialSnapshot],
) -> dict[str, SymbolFinancialSnapshot]:
    return {snap.symbol.strip().upper(): snap for snap in snapshots}


def snapshot_to_metadata_tuple(snap: SymbolFinancialSnapshot) -> tuple:
    return (
        snap.est_target,
        snap.change_pct,
        snap.div_yield,
    )


def snapshot_to_valuation_fields(snap: SymbolFinancialSnapshot) -> dict:
    from portfolio_app.analysis.valuation_scores import (
        METRIC_FORWARD_PE,
        METRIC_OPERATING_MARGIN,
        METRIC_PEG,
        METRIC_REVENUE_GROWTH,
        METRIC_TRAILING_PE,
    )

    keyed = {
        METRIC_TRAILING_PE: snap.trailing_pe,
        METRIC_FORWARD_PE: snap.forward_pe,
        METRIC_PEG: snap.peg,
        METRIC_REVENUE_GROWTH: snap.rev_growth_pct,
        METRIC_OPERATING_MARGIN: snap.op_margin_pct,
    }
    return raw_metrics_to_display(keyed)


def build_portfolio_results_from_snapshots(
    df_port: pd.DataFrame,
    snapshot_by_symbol: dict[str, SymbolFinancialSnapshot],
    *,
    eur_rate: float | None = None,
) -> tuple:
    """Build screener rows from persisted snapshots — no network calls."""
    results_temp = []
    total_depot_value = 0.0
    total_depot_cost = 0.0
    total_depot_target = 0.0
    total_depot_div_income = 0.0

    for _, row in df_port.iterrows():
        symbol = str(row["Symbol"]).strip().upper()
        snap = snapshot_by_symbol.get(symbol)
        price = snap.price if snap and snap.price is not None else None
        has_price = price is not None and price > 0

        if has_price and snap:
            est_target = snap.est_target
            pct_change = snap.change_pct
            div_yield = snap.div_yield
            upside_pct = ((est_target / price) - 1) * 100 if est_target else None
            trends = {
                key: getattr(snap, attr)
                for key, attr in zip(_TREND_KEYS, _SNAPSHOT_RETURN_ATTRS)
            }
            hist = pd.DataFrame({"Close": [float(price)]})
        elif has_price:
            est_target, pct_change, div_yield, upside_pct = None, None, None, None
            trends = {k: None for k in _TREND_KEYS}
            hist = pd.DataFrame({"Close": [float(price)]})
        else:
            est_target, pct_change, div_yield, upside_pct = None, None, None, None
            trends = {k: None for k in _TREND_KEYS}
            hist = pd.DataFrame()

        cost_per_share = row["AvgCost"]
        target = row["TargetPrice"]
        if row["Currency"] == "EUR" and eur_rate:
            cost_per_share /= eur_rate
            target /= eur_rate

        purchase_date = row["PurchaseDate"]
        if pd.isna(purchase_date) or isinstance(purchase_date, str):
            try:
                purchase_date = pd.to_datetime(purchase_date)
            except Exception:
                purchase_date = None

        days_held = holding_days_since_purchase(purchase_date)
        current_shares = row["Shares"]
        current_cost = row["Shares"] * cost_per_share
        current_target = row["Shares"] * target
        total_depot_cost += current_cost
        total_depot_target += current_target

        if has_price:
            current_val = row["Shares"] * price
            total_depot_value += current_val
            diff_target_abs = abs(target - price)
            diff_target_pct = abs(target - price) / price if price != 0 else 0
            act_target_delta_pct = value_to_target_gap_pct(current_val, current_target)
            est_target_val = (
                current_shares * float(est_target)
                if est_target is not None and est_target
                else None
            )
            act_est_target_delta_pct = value_to_target_gap_pct(current_val, est_target_val)
            total_pct = ((current_val / current_cost) - 1) * 100 if current_cost else None
            total_dollar = current_val - current_cost
            cagr = compute_position_cagr(current_val, current_cost, days_held)
        else:
            diff_target_abs = None
            diff_target_pct = None
            act_target_delta_pct = None
            act_est_target_delta_pct = None
            total_pct = None
            total_dollar = None
            cagr = None

        div_income = None
        if has_price:
            div_income = compute_annual_div_income(current_shares, price, div_yield)
        if div_income is not None:
            total_depot_div_income += div_income

        res = {
            "Symbol": symbol,
            "🌐 Price": price,
            "Change %": pct_change,
            "Div Yield": div_yield,
            "Est Target": est_target,
            "Upside %": upside_pct,
            "Shares": current_shares,
            "Cost/Share": cost_per_share,
            "PurchaseDate": purchase_date.strftime("%Y-%m-%d")
            if purchase_date is not None and not pd.isna(purchase_date)
            else "Unknown",
            "📈 Target": target,
            "∆ Act-Target %": act_target_delta_pct,
            "∆ Act-Est Target %": act_est_target_delta_pct,
            "Target %": (diff_target_pct * 100) if diff_target_pct is not None else None,
            "Target $": diff_target_abs,
            "📈 Total %": total_pct,
            "Total $": total_dollar,
            "Div Income": div_income,
            "Ø CAGR": cagr,
        }
        res.update(trends)
        for col in VALUATION_ALL_COLUMNS:
            res[col] = None
        if snap:
            valuation_fields = snapshot_to_valuation_fields(snap)
            for col in VALUATION_RAW_COLUMNS:
                if col in valuation_fields:
                    res[col] = valuation_fields.get(col)
        results_temp.append({"data": res, "hist": hist})

    if results_temp:
        metrics_by_symbol = {
            item["data"]["Symbol"]: metrics_from_row(item["data"]) for item in results_temp
        }
        score_map = compute_portfolio_p_scores(metrics_by_symbol)
        for item in results_temp:
            symbol = item["data"]["Symbol"]
            if symbol in score_map:
                for col, val in score_map[symbol].items():
                    item["data"][col] = val

    return (
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
    )


def _apply_session_results(
    results_temp,
    total_depot_value,
    total_depot_cost,
    total_depot_target,
    total_depot_div_income,
    unique_symbols: tuple,
    *,
    enriched_symbols: set[str],
    valuation_enriched: set[str],
) -> None:
    import streamlit as st

    from portfolio_app.session_keys import clear_portfolio_table_widget

    st.session_state.all_results = results_temp
    st.session_state.total_depot_value = total_depot_value
    st.session_state.total_depot_cost = total_depot_cost
    st.session_state.total_depot_target = total_depot_target
    st.session_state.total_depot_div_income = total_depot_div_income
    st.session_state.ticker_liste = [x["data"]["Symbol"] for x in results_temp]
    st.session_state.portfolio_symbols = unique_symbols
    st.session_state.enriched_symbols = enriched_symbols
    st.session_state.valuation_enriched_symbols = valuation_enriched
    st.session_state.valuation_loaded = bool(valuation_enriched)
    st.session_state.metadata_bg_active = False
    st.session_state.metadata_queue = []
    st.session_state.metadata_enriched = True
    st.session_state.valuation_bg_active = False
    st.session_state.valuation_queue = []
    if results_temp:
        first_symbol = results_temp[0]["data"]["Symbol"]
        st.session_state.selected_symbol = first_symbol
        st.session_state.selected_symbols = []
        st.session_state.table_sel_rows = []
        st.session_state.ticker_index = 0
        st.session_state.clear_table_selection = True
        st.session_state["fibo_needs_refresh"] = True
        clear_portfolio_table_widget()


def load_analysis_from_snapshots(
    df_port: pd.DataFrame,
    portfolio_id: int,
    repo: PortfolioRepository | None = None,
) -> PortfolioSyncState:
    """Startup / portfolio switch — rebuild table from DB snapshots only."""
    repo = repo or PortfolioRepository()
    sync_state = repo.get_sync_state(portfolio_id)
    if df_port is None or df_port.empty:
        return sync_state

    unique_symbols = tuple(sorted(df_port["Symbol"].astype(str).str.upper().unique().tolist()))
    needs_eur = (df_port["Currency"] == "EUR").any()
    eur_rate = None
    if needs_eur:
        import streamlit as st

        # Reuse last refresh rate — no FX fetch on startup (spec §10.1).
        eur_rate = st.session_state.get("last_eur_rate") or 1.0

    snapshots = repo.list_symbol_snapshots(portfolio_id)
    snap_map = snapshots_by_symbol(snapshots)

    (
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
    ) = build_portfolio_results_from_snapshots(df_port, snap_map, eur_rate=eur_rate)

    enriched = {
        s
        for s in unique_symbols
        if s in snap_map
        and (
            snap_map[s].est_target is not None
            or snap_map[s].change_pct is not None
            or snap_map[s].div_yield is not None
        )
    }
    valuation_enriched = {
        s
        for s in unique_symbols
        if s in snap_map
        and any(
            getattr(snap_map[s], attr) is not None
            for attr in ("trailing_pe", "forward_pe", "peg", "rev_growth_pct", "op_margin_pct")
        )
    }

    _apply_session_results(
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
        unique_symbols,
        enriched_symbols=enriched,
        valuation_enriched=valuation_enriched,
    )
    return sync_state


def _display_row_to_snapshot(
    portfolio_id: int,
    item: dict,
    synced_at: datetime,
) -> SymbolFinancialSnapshot:
    d = item["data"]
    rev = d.get(COL_REV_GROWTH)
    margin = d.get(COL_OP_MARGIN)
    return SymbolFinancialSnapshot(
        portfolio_id=portfolio_id,
        symbol=str(d["Symbol"]).strip().upper(),
        synced_at=synced_at,
        price=d.get("🌐 Price"),
        change_pct=d.get("Change %"),
        div_yield=d.get("Div Yield"),
        est_target=d.get("Est Target"),
        trailing_pe=d.get(COL_TRAILING_PE),
        forward_pe=d.get(COL_FORWARD_PE),
        peg=d.get(COL_PEG),
        rev_growth_pct=(rev / 100.0) if rev is not None else None,
        op_margin_pct=(margin / 100.0) if margin is not None else None,
        returns_5d=d.get("5D"),
        returns_1m=d.get("1M"),
        returns_6m=d.get("6M"),
        returns_12m=d.get("12M"),
    )


def resolve_history_months(history_months: int | None = None) -> int:
    """Session history window for sync, or explicit override (tests)."""
    if history_months is not None:
        return clamp_history_months(history_months)
    try:
        import streamlit as st

        from portfolio_app.ui.history_controls import history_months as session_history_months

        return session_history_months()
    except Exception:
        return HISTORY_MONTHS_DEFAULT


def run_network_refresh(
    df_port: pd.DataFrame,
    portfolio_id: int,
    repo: PortfolioRepository | None = None,
    *,
    history_months: int | None = None,
) -> PortfolioSyncState:
    """Refresh button — fetch Yahoo data, persist snapshots, update sync state."""
    repo = repo or PortfolioRepository()
    if df_port is None or df_port.empty:
        repo.update_sync_state(portfolio_id, last_sync_status=SYNC_STATUS_NEVER)
        return repo.get_sync_state(portfolio_id)

    unique_symbols = tuple(sorted(df_port["Symbol"].astype(str).str.upper().unique().tolist()))
    needs_eur = (df_port["Currency"] == "EUR").any()
    eur_rate = get_exchange_rate() if needs_eur else None
    if needs_eur and eur_rate:
        import streamlit as st

        st.session_state.last_eur_rate = eur_rate

    months = resolve_history_months(history_months)
    bulk_close, price_fetch_note = download_close_prices(
        list(unique_symbols), history_months=months
    )
    from portfolio_app.analysis.portfolio_build import build_hist_by_symbol

    hist_by_symbol = build_hist_by_symbol(bulk_close, unique_symbols)
    metadata_map = fetch_portfolio_metadata_parallel(unique_symbols)
    valuation_map = fetch_portfolio_valuation_parallel(unique_symbols)

    (
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
    ) = build_portfolio_results(df_port, hist_by_symbol, eur_rate, metadata_map=metadata_map)

    apply_valuation_to_results(results_temp, valuation_map)

    from portfolio_app.data.valuation_metadata import recompute_all_p_scores

    recompute_all_p_scores(results_temp)

    synced_at = datetime.now(timezone.utc)
    snapshots = [
        _display_row_to_snapshot(portfolio_id, item, synced_at) for item in results_temp
    ]
    requested = len(unique_symbols)
    succeeded = sum(
        1
        for sym in unique_symbols
        if any(item["data"]["Symbol"] == sym and item["data"].get("🌐 Price") for item in results_temp)
    )

    repo.upsert_symbol_snapshots(portfolio_id, snapshots)
    repo.prune_symbol_snapshots(portfolio_id, unique_symbols)

    if succeeded == 0:
        status = SYNC_STATUS_FAILED
    elif succeeded < requested:
        status = SYNC_STATUS_PARTIAL
    else:
        status = SYNC_STATUS_SUCCESS

    sync_error = price_fetch_note
    if succeeded == 0 and not sync_error:
        sync_error = (
            f"Yahoo returned no prices for {requested} symbol(s) on this host."
        )
    elif succeeded < requested and not sync_error:
        sync_error = f"Prices for {succeeded}/{requested} symbols only."

    sync_state = repo.update_sync_state(
        portfolio_id,
        last_sync_at=synced_at,
        last_sync_status=status,
        last_sync_error=sync_error,
        symbols_requested=requested,
        symbols_succeeded=succeeded,
    )

    _apply_session_results(
        results_temp,
        total_depot_value,
        total_depot_cost,
        total_depot_target,
        total_depot_div_income,
        unique_symbols,
        enriched_symbols=set(metadata_map.keys()),
        valuation_enriched=set(valuation_map.keys()),
    )
    import streamlit as st

    st.session_state[SYNCED_HISTORY_MONTHS_KEY] = months
    return sync_state
