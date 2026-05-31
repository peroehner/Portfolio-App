"""Background and on-demand analyst metadata loading."""
import time

import streamlit as st

from portfolio_app.config import (
    ANALYST_LOADED_NOTICE_SEC,
    METADATA_BATCH_SIZE,
    METADATA_POLL_SECONDS,
)
from portfolio_app.analysis.portfolio_build import compute_total_depot_div_income
from portfolio_app.analysis.returns import compute_annual_div_income
from portfolio_app.data.market_data import get_symbol_metadata
from portfolio_app.ui.components import mark_preserve_table_selection


def apply_metadata_to_item(item, est_target, pct_change, div_yield):
    """Write analyst fields into one portfolio row."""
    price = item["data"]["🌐 Price"]
    item["data"]["Change %"] = pct_change
    item["data"]["Div Yield"] = div_yield
    item["data"]["Est Target"] = est_target
    item["data"]["Upside %"] = ((est_target / price) - 1) * 100 if est_target and price else 0.0
    if est_target and price:
        item["data"]["∆ Act-Est Target %"] = ((price - est_target) / price * 100)
    else:
        item["data"]["∆ Act-Est Target %"] = None
    shares = item["data"].get("Shares")
    item["data"]["Div Income"] = compute_annual_div_income(shares, price, div_yield)


def enrich_results_with_metadata(all_results, metadata_map):
    """Merge optional analyst fields into an already-built portfolio."""
    for item in all_results:
        symbol = item["data"]["Symbol"]
        if symbol not in metadata_map:
            continue
        apply_metadata_to_item(item, *metadata_map[symbol])
    st.session_state.enriched_symbols = set(metadata_map.keys())
    st.session_state.total_depot_div_income = compute_total_depot_div_income(all_results)


def enrich_symbol_metadata(all_results, symbol):
    """Load and merge analyst data for a single symbol into session results."""
    meta = get_symbol_metadata(symbol)
    for item in all_results:
        if item["data"]["Symbol"] == symbol:
            apply_metadata_to_item(item, *meta)
    if "enriched_symbols" not in st.session_state:
        st.session_state.enriched_symbols = set()
    st.session_state.enriched_symbols.add(symbol)
    st.session_state.total_depot_div_income = compute_total_depot_div_income(all_results)


def metadata_map_from_results(all_results):
    """Rebuild analyst tuples from session rows already enriched."""
    enriched = st.session_state.get("enriched_symbols", set())
    if not enriched:
        return {}
    metadata_map = {}
    for item in all_results:
        symbol = item["data"]["Symbol"]
        if symbol not in enriched:
            continue
        metadata_map[symbol] = (
            item["data"].get("Est Target"),
            item["data"].get("Change %"),
            item["data"].get("Div Yield"),
        )
    return metadata_map


def start_metadata_background_load(symbols):
    """Queue analyst fields to load progressively after prices are shown."""
    symbol_list = list(dict.fromkeys(symbols))
    st.session_state.metadata_queue = symbol_list
    st.session_state.metadata_total = len(symbol_list)
    st.session_state.metadata_bg_active = bool(symbol_list)
    st.session_state.metadata_enriched = False
    st.session_state.enriched_symbols = set()
    st.session_state.pop("analyst_loaded_notice_at", None)


def start_metadata_for_new_symbols(symbols):
    """Queue analyst load only for symbols not yet in enriched_symbols."""
    enriched = st.session_state.get("enriched_symbols", set())
    new_symbols = [s for s in dict.fromkeys(symbols) if s not in enriched]
    if not new_symbols:
        return
    queue = list(st.session_state.get("metadata_queue", []))
    for symbol in new_symbols:
        if symbol not in queue:
            queue.append(symbol)
    st.session_state.metadata_queue = queue
    st.session_state.metadata_total = len(enriched) + len(queue)
    st.session_state.metadata_bg_active = True
    st.session_state.metadata_enriched = False


def prioritize_metadata_symbol(symbol):
    """Move symbol to front of background queue (e.g. on row click)."""
    if symbol in st.session_state.get("enriched_symbols", set()):
        return
    queue = list(st.session_state.get("metadata_queue", []))
    if symbol in queue:
        queue.remove(symbol)
        st.session_state.metadata_queue = [symbol] + queue
    elif st.session_state.get("metadata_bg_active"):
        st.session_state.metadata_queue = [symbol] + queue
    else:
        enrich_symbol_metadata(st.session_state.all_results, symbol)


def process_metadata_background_batch():
    """
    Fetch next batch of analyst data.

    Returns (more_work_remaining, just_finished).
    """
    if not st.session_state.get("metadata_bg_active"):
        return False, False
    queue = list(st.session_state.get("metadata_queue", []))
    if not queue:
        st.session_state.metadata_bg_active = False
        st.session_state.metadata_enriched = True
        st.session_state.analyst_loaded_notice_at = time.time()
        return False, True
    batch = queue[:METADATA_BATCH_SIZE]
    st.session_state.metadata_queue = queue[METADATA_BATCH_SIZE:]
    for symbol in batch:
        enrich_symbol_metadata(st.session_state.all_results, symbol)
    return bool(st.session_state.metadata_queue), False


@st.fragment(run_every=METADATA_POLL_SECONDS)
def portfolio_metadata_progress():
    """Background analyst loader only — table stays in main app for row selection."""
    if "all_results" not in st.session_state or not st.session_state.all_results:
        return

    _, just_finished = process_metadata_background_batch()
    if just_finished:
        mark_preserve_table_selection()
        st.rerun()

    total = st.session_state.get("metadata_total", 0)
    remaining = len(st.session_state.get("metadata_queue", []))
    done = total - remaining

    if st.session_state.get("metadata_bg_active") and total > 0:
        next_sym = (
            st.session_state.metadata_queue[0]
            if st.session_state.metadata_queue
            else "…"
        )
        st.progress(
            min(1.0, done / total),
            text=f"Loading analyst data: {done}/{total} · Next: {next_sym}",
        )
    elif st.session_state.get("metadata_enriched"):
        notice_at = st.session_state.get("analyst_loaded_notice_at")
        if notice_at and (time.time() - notice_at) < ANALYST_LOADED_NOTICE_SEC:
            st.progress(1.0, text="✓ Analyst data loaded.")
        elif notice_at:
            st.session_state.pop("analyst_loaded_notice_at", None)
