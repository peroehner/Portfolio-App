"""Portfolio table sort — one global order (symbol sequence) shared across all views."""
from __future__ import annotations

import pandas as pd
import streamlit as st

SORT_ASC = "asc"
SORT_DESC = "desc"

TABLE_SORT_KEY = "portfolio_table_sort"
# Legacy keys from per-view / Ctrl+click model — cleared on read.
_LEGACY_VIEW_SORTS_KEY = "portfolio_view_sorts"
_LEGACY_STICKY_SORT_KEY = "portfolio_sticky_sort"


def _clear_legacy_sort_keys() -> None:
    st.session_state.pop(_LEGACY_VIEW_SORTS_KEY, None)
    st.session_state.pop(_LEGACY_STICKY_SORT_KEY, None)


def get_table_sort() -> dict | None:
    _clear_legacy_sort_keys()
    state = st.session_state.get(TABLE_SORT_KEY)
    if not state or not state.get("column"):
        return None
    return state


def clear_table_sort() -> None:
    st.session_state.pop(TABLE_SORT_KEY, None)


def _cycle_sort(current: dict | None, column: str) -> dict | None:
    """asc → desc → cleared."""
    if not current or current.get("column") != column:
        return {"column": column, "direction": SORT_ASC}
    if current.get("direction") == SORT_ASC:
        return {"column": column, "direction": SORT_DESC}
    return None


def _sort_series(df: pd.DataFrame, column: str, direction: str) -> pd.Series:
    """Sort key for one column (numeric-aware)."""
    if column not in df.columns:
        return pd.Series(range(len(df)), index=df.index)
    series = df[column]
    if column == "Symbol":
        keys = series.astype(str).str.upper()
    elif column == "PurchaseDate":
        keys = pd.to_datetime(series, errors="coerce")
    else:
        keys = pd.to_numeric(series, errors="coerce")
    ascending = direction == SORT_ASC
    return keys.rank(method="first", ascending=ascending, na_option="bottom")


def sort_dataframe(df: pd.DataFrame, column: str, direction: str) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns:
        return df
    out = df.copy()
    out["_sort_key"] = _sort_series(out, column, direction)
    if "Symbol" in out.columns and column != "Symbol":
        out["_sym_key"] = out["Symbol"].astype(str).str.upper()
        out = out.sort_values(
            ["_sort_key", "_sym_key"],
            ascending=[True, True],
            kind="mergesort",
        )
        out = out.drop(columns=["_sort_key", "_sym_key"])
    else:
        out = out.sort_values("_sort_key", ascending=True, kind="mergesort")
        out = out.drop(columns=["_sort_key"])
    return out.reset_index(drop=True)


def symbol_order_from_sorted_df(df: pd.DataFrame) -> list[str]:
    """Unique symbols in display order (shared across tab views)."""
    if df is None or df.empty or "Symbol" not in df.columns:
        return []
    seen: set[str] = set()
    order: list[str] = []
    for sym in df["Symbol"].astype(str).str.strip().str.upper():
        if not sym or sym in seen:
            continue
        seen.add(sym)
        order.append(sym)
    return order


def reorder_by_symbol_order(df: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    if df is None or df.empty or not symbols or "Symbol" not in df.columns:
        return df
    rank = {sym: i for i, sym in enumerate(symbols)}
    out = df.copy()
    sym = out["Symbol"].astype(str).str.strip().str.upper()
    out["_sym_rank"] = sym.map(lambda s: rank.get(s, len(rank) + 1))
    out["_row_seq"] = range(len(out))
    out = out.sort_values(
        ["_sym_rank", "_row_seq"],
        ascending=[True, True],
        kind="mergesort",
    )
    return out.drop(columns=["_sym_rank", "_row_seq"]).reset_index(drop=True)


def apply_table_sort(df: pd.DataFrame, view_name: str = "") -> pd.DataFrame:
    """Apply global symbol order from the active sort (all views)."""
    del view_name  # kept for call-site compatibility
    if df is None or df.empty:
        return df
    active = get_table_sort()
    if not active:
        return df.reset_index(drop=True)
    symbols = active.get("symbols") or []
    if symbols:
        return reorder_by_symbol_order(df, symbols)
    column = active.get("column")
    direction = active.get("direction", SORT_ASC)
    if column and column in df.columns:
        return sort_dataframe(df, column, direction)
    return df.reset_index(drop=True)


def handle_sort_header_click(
    view_name: str,
    column: str,
    *,
    display_df: pd.DataFrame,
) -> None:
    """Header click: ^ → ↓ → clear; symbol order applies in every view."""
    column = str(column).strip()
    if not column:
        return

    current = get_table_sort()
    new_state = _cycle_sort(current, column)
    if not new_state:
        clear_table_sort()
        return

    sorted_df = sort_dataframe(display_df, column, new_state["direction"])
    st.session_state[TABLE_SORT_KEY] = {
        "column": column,
        "direction": new_state["direction"],
        "symbols": symbol_order_from_sorted_df(sorted_df),
        "source_view": view_name,
    }


def sort_header_suffix(column: str) -> str:
    """Header decoration: ^ / ↓ on the active sort column."""
    active = get_table_sort()
    if active and active.get("column") == column:
        return " ↓" if active.get("direction") == SORT_DESC else " ^"
    return ""


def row_indices_for_symbols(df: pd.DataFrame, symbols: list[str]) -> list[int]:
    """Map selected symbols to row positions in the current display order."""
    if df is None or df.empty or not symbols:
        return []
    want = {str(s).strip().upper() for s in symbols if str(s).strip()}
    return [
        i
        for i in range(len(df))
        if str(df.iloc[i].get("Symbol", "")).strip().upper() in want
    ]
