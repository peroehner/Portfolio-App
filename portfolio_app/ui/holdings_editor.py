"""Editable holdings table (user-sourced columns)."""
from datetime import date

import pandas as pd
import streamlit as st

from portfolio_app.data.market_data import validate_symbol
from portfolio_app.domain.columns import SOURCE_LEGEND, ColumnSource
from portfolio_app.services.session_context import (
    get_portfolio_service,
    invalidate_analysis,
    load_active_portfolio,
)


def _draft_key(portfolio_id: int) -> str:
    return f"holdings_draft_{portfolio_id}"


def _editor_key(portfolio_id: int) -> str:
    return f"holdings_editor_{portfolio_id}"


def clear_holdings_draft(portfolio_id: int):
    st.session_state.pop(_draft_key(portfolio_id), None)


def _reset_holdings_editor_widget(portfolio_id: int):
    """Drop cached data_editor state so the draft dataframe is shown after add."""
    st.session_state.pop(_editor_key(portfolio_id), None)


def _editor_dataframe(portfolio_id: int, holdings_df: pd.DataFrame) -> pd.DataFrame:
    draft = st.session_state.get(_draft_key(portfolio_id))
    if draft is not None:
        return draft.copy()
    return holdings_df.copy()


def _append_symbol_row(df: pd.DataFrame, symbol: str, currency: str) -> pd.DataFrame:
    if symbol in df["Symbol"].astype(str).str.upper().values:
        raise ValueError(f"{symbol} is already in your holdings.")
    new_row = pd.DataFrame([{
        "Symbol": symbol,
        "Shares": 0.0,
        "AvgCost": 0.0,
        "PurchaseDate": pd.Timestamp(date.today()),
        "TargetPrice": 0.0,
        "Currency": currency,
    }])
    return pd.concat([df, new_row], ignore_index=True)


def set_holdings_panel_open(open_panel: bool = True):
    st.session_state.holdings_expanded = open_panel


def _render_add_symbol(portfolio_id: int, holdings_df: pd.DataFrame):
    sym_col, btn_col = st.columns([4, 1], vertical_alignment="bottom")
    with sym_col:
        raw = st.text_input(
            "Add symbol",
            placeholder="e.g. AAPL",
            key=f"add_symbol_input_{portfolio_id}",
        )
    with btn_col:
        add_clicked = st.button("Add symbol", use_container_width=True, key=f"add_symbol_btn_{portfolio_id}")

    if not add_clicked:
        return

    symbol_input = (raw or "").strip()
    if not symbol_input:
        st.warning("Enter a ticker symbol.")
        return

    with st.spinner(f"Checking {symbol_input.upper()}…"):
        valid, normalized, currency = validate_symbol(symbol_input)

    if not valid:
        st.error(f'"{symbol_input.upper()}" was not found on Yahoo Finance. Check the ticker and try again.')
        return

    try:
        df = _editor_dataframe(portfolio_id, holdings_df)
        updated = _append_symbol_row(df, normalized, currency or "USD")
        st.session_state[_draft_key(portfolio_id)] = updated
        _reset_holdings_editor_widget(portfolio_id)
        set_holdings_panel_open(True)
        st.success(f"Added {normalized}. Edit shares and cost, then Save holdings.")
        st.rerun()
    except ValueError as e:
        st.error(str(e))


def _validate_holdings_symbols(df: pd.DataFrame):
    for sym in df["Symbol"].astype(str).str.strip().str.upper().unique():
        if not sym:
            continue
        valid, _, _ = validate_symbol(sym)
        if not valid:
            raise ValueError(
                f'"{sym}" was not found on Yahoo Finance. Remove it or fix the ticker.'
            )


def _render_holdings_body(portfolio_id: int, holdings_df: pd.DataFrame, editor_df: pd.DataFrame):
    st.caption(SOURCE_LEGEND[ColumnSource.USER])
    _render_add_symbol(portfolio_id, holdings_df)

    column_config = {
        "Symbol": st.column_config.TextColumn("Symbol", required=True),
        "Shares": st.column_config.NumberColumn("Shares", min_value=0, format="%.4f"),
        "AvgCost": st.column_config.NumberColumn("Avg cost", min_value=0, format="%.2f"),
        "PurchaseDate": st.column_config.DateColumn("Purchase date"),
        "TargetPrice": st.column_config.NumberColumn("Target price", min_value=0, format="%.2f"),
        "Currency": st.column_config.TextColumn("Currency", help="USD or EUR"),
    }

    edited = st.data_editor(
        editor_df,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=_editor_key(portfolio_id),
    )

    save_col, _ = st.columns([1, 3])
    with save_col:
        if st.button("Save holdings", type="primary", use_container_width=True):
            try:
                with st.spinner("Validating symbols…"):
                    _validate_holdings_symbols(edited)
                svc = get_portfolio_service()
                saved = svc.save_holdings(portfolio_id, edited)
                clear_holdings_draft(portfolio_id)
                invalidate_analysis(refetch_metadata=False)
                st.session_state.active_portfolio_holdings = saved.holdings_df
                set_holdings_panel_open(True)
                st.success("Holdings saved.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Could not save: {e}")


def render_holdings_editor():
    active = load_active_portfolio()
    portfolio_id = active.portfolio_id
    symbol_count = len(active.holdings_df)
    expanded = st.session_state.get("holdings_expanded", False)

    with st.expander(
        f"Holdings ({symbol_count} symbols) — expand to edit or add symbols",
        expanded=expanded,
    ):
        editor_df = _editor_dataframe(portfolio_id, active.holdings_df)
        _render_holdings_body(portfolio_id, active.holdings_df, editor_df)
