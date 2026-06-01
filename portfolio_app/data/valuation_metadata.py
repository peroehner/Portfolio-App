"""Background valuation ratio loading and portfolio P-Score computation."""
import time

import streamlit as st

from portfolio_app.analysis.valuation_scores import (
    VALUATION_ALL_COLUMNS,
    VALUATION_RAW_COLUMNS,
    VALUATION_SCORE_COLUMNS,
    compute_portfolio_p_scores,
    metrics_from_row,
)
from portfolio_app.config import METADATA_BATCH_SIZE, METADATA_POLL_SECONDS
from portfolio_app.data.valuation_data import get_symbol_valuation
from portfolio_app.ui.components import mark_preserve_table_selection


def apply_valuation_raw_to_item(item, valuation_fields: dict):
    for col in VALUATION_RAW_COLUMNS:
        if col in valuation_fields:
            item["data"][col] = valuation_fields.get(col)


def apply_valuation_scores_to_item(item, score_fields: dict):
    for col in VALUATION_SCORE_COLUMNS:
        if col in score_fields:
            item["data"][col] = score_fields.get(col)


def clear_valuation_scores(all_results):
    for item in all_results:
        for col in VALUATION_SCORE_COLUMNS:
            item["data"][col] = None


def valuation_map_from_results(all_results) -> dict[str, dict]:
    """Rebuild valuation fields from session rows already enriched."""
    enriched = st.session_state.get("valuation_enriched_symbols", set())
    if not isinstance(enriched, set):
        enriched = set(enriched)
    if not enriched:
        return {}
    out: dict[str, dict] = {}
    for item in all_results:
        symbol = item["data"]["Symbol"]
        if symbol not in enriched:
            continue
        out[symbol] = {col: item["data"].get(col) for col in VALUATION_ALL_COLUMNS}
    return out


def apply_valuation_to_results(all_results, valuation_map: dict[str, dict]) -> None:
    """Merge cached valuation columns into a freshly built portfolio."""
    if not valuation_map:
        return
    for item in all_results:
        symbol = item["data"]["Symbol"]
        fields = valuation_map.get(symbol)
        if not fields:
            continue
        for col in VALUATION_ALL_COLUMNS:
            if col in fields:
                item["data"][col] = fields.get(col)
    if st.session_state.get("valuation_loaded"):
        recompute_all_p_scores(all_results)


def recompute_all_p_scores(all_results):
    """Recompute peer z-scores and grades after raw metrics change."""
    metrics_by_symbol = {}
    for item in all_results:
        symbol = item["data"]["Symbol"]
        metrics_by_symbol[symbol] = metrics_from_row(item["data"])
    score_map = compute_portfolio_p_scores(metrics_by_symbol)
    for item in all_results:
        symbol = item["data"]["Symbol"]
        if symbol in score_map:
            apply_valuation_scores_to_item(item, score_map[symbol])


def enrich_symbol_valuation_raw(all_results, symbol):
    """Load yfinance ratios for one symbol; P-Scores are computed when the batch finishes."""
    fields = get_symbol_valuation(symbol)
    for item in all_results:
        if item["data"]["Symbol"] == symbol:
            apply_valuation_raw_to_item(item, fields)
    enriched = st.session_state.get("valuation_enriched_symbols", set())
    if not isinstance(enriched, set):
        enriched = set(enriched)
    enriched.add(symbol)
    st.session_state.valuation_enriched_symbols = enriched


def start_valuation_background_load(symbols):
    symbol_list = list(dict.fromkeys(symbols))
    st.session_state.valuation_queue = symbol_list
    st.session_state.valuation_total = len(symbol_list)
    st.session_state.valuation_bg_active = bool(symbol_list)
    st.session_state.valuation_loaded = False
    st.session_state.valuation_enriched_symbols = set()
    st.session_state.pop("valuation_loaded_notice_at", None)
    if symbol_list and "all_results" in st.session_state:
        clear_valuation_scores(st.session_state.all_results)


def start_valuation_for_new_symbols(symbols):
    enriched = st.session_state.get("valuation_enriched_symbols", set())
    if not isinstance(enriched, set):
        enriched = set(enriched)
    new_symbols = [s for s in dict.fromkeys(symbols) if s not in enriched]
    if not new_symbols:
        return
    queue = list(st.session_state.get("valuation_queue", []))
    for symbol in new_symbols:
        if symbol not in queue:
            queue.append(symbol)
    st.session_state.valuation_queue = queue
    st.session_state.valuation_total = len(enriched) + len(queue)
    st.session_state.valuation_bg_active = True
    st.session_state.valuation_loaded = False


def prioritize_valuation_symbol(symbol):
    if symbol in st.session_state.get("valuation_enriched_symbols", set()):
        return
    queue = list(st.session_state.get("valuation_queue", []))
    if symbol in queue:
        queue.remove(symbol)
        st.session_state.valuation_queue = [symbol] + queue
    elif st.session_state.get("valuation_bg_active"):
        st.session_state.valuation_queue = [symbol] + queue
    else:
        clear_valuation_scores(st.session_state.all_results)
        enrich_symbol_valuation_raw(st.session_state.all_results, symbol)
        recompute_all_p_scores(st.session_state.all_results)


def process_valuation_background_batch():
    if not st.session_state.get("valuation_bg_active"):
        return False, False
    queue = list(st.session_state.get("valuation_queue", []))
    if not queue:
        st.session_state.valuation_bg_active = False
        st.session_state.valuation_loaded = True
        st.session_state.valuation_loaded_notice_at = time.time()
        recompute_all_p_scores(st.session_state.all_results)
        return False, True
    batch = queue[:METADATA_BATCH_SIZE]
    st.session_state.valuation_queue = queue[METADATA_BATCH_SIZE:]
    for symbol in batch:
        enrich_symbol_valuation_raw(st.session_state.all_results, symbol)
    return bool(st.session_state.valuation_queue), False


@st.fragment(run_every=METADATA_POLL_SECONDS)
def portfolio_valuation_progress():
    if "all_results" not in st.session_state or not st.session_state.all_results:
        return

    _, just_finished = process_valuation_background_batch()
    view = st.session_state.get("portfolio_table_view", "")
    if just_finished and view == "Valuation Growth":
        mark_preserve_table_selection()
        st.rerun()

    if view != "Valuation Growth":
        return

    total = st.session_state.get("valuation_total", 0)
    remaining = len(st.session_state.get("valuation_queue", []))
    done = total - remaining

    if st.session_state.get("valuation_bg_active") and total > 0:
        next_sym = (
            st.session_state.valuation_queue[0]
            if st.session_state.valuation_queue
            else "…"
        )
        st.progress(
            min(1.0, done / total),
            text=f"Loading valuation data: {done}/{total} · Next: {next_sym}",
        )
    elif st.session_state.get("valuation_loaded"):
        notice_at = st.session_state.get("valuation_loaded_notice_at")
        if notice_at and (time.time() - notice_at) < 3:
            st.progress(1.0, text="✓ Valuation data and P-Scores updated.")
