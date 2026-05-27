"""Portfolio table views, multi-row selection, inline ROI editing, and styling."""
import pandas as pd
import streamlit as st

from portfolio_app.config import (
    METADATA_COLS,
    METADATA_LATE_COLS,
    TABLE_CURRENCY_COLS,
    TABLE_GRADIENT_EXCLUDE,
    TABLE_NUMBER_COLUMN_FORMAT,
    TABLE_PERCENT_COLS,
    TABLE_PNL_COLS,
    TABLE_VIEW_COLUMNS,
)
from portfolio_app.data.market_data import validate_symbol
from portfolio_app.data.metadata import portfolio_metadata_progress, prioritize_metadata_symbol
from portfolio_app.services.session_context import invalidate_analysis, load_active_portfolio
from portfolio_app.ui.toolbar import is_portfolio_more_open
from portfolio_app.ui.components import get_table_click_modifiers

_PRESERVE_SELECTION_KEY = "_preserve_table_selection"
_SKIP_SELECTION_APPLY_KEY = "_skip_table_selection_apply"
from portfolio_app.ui.holdings import (
    ROI_EDITABLE_COLUMNS,
    append_symbol_to_draft,
    clear_holdings_draft,
    display_df_to_holdings,
    enrich_summary_with_currency,
    get_editable_holdings_df,
    holdings_to_roi_display_df,
    merge_holdings_into_roi_display,
    prepare_roi_editor_df,
    save_holdings_from_df,
    set_holdings_draft,
    validate_roi_editor_df,
)
from portfolio_app.ui.table_style import style_signed_column


def normalize_table_selection_rows(raw_rows, prev_rows, shift_held=False, alt_held=False):
    """
    Plain click -> only that row. Shift+click -> contiguous range.
    Alt+click -> toggle one row. Uncheck -> keep the rest.
    """
    new_rows = sorted({int(r) for r in raw_rows})
    prev_rows = sorted({int(r) for r in (prev_rows or [])})

    if not new_rows:
        return []

    added = set(new_rows) - set(prev_rows)
    removed = set(prev_rows) - set(new_rows)
    is_contiguous = new_rows[-1] - new_rows[0] + 1 == len(new_rows)

    if alt_held:
        if not new_rows:
            return []
        # Uncheck: widget keeps the other selected rows.
        if len(removed) == 1 and not added:
            return new_rows
        # Check: widget adds one row without dropping others.
        if len(added) == 1 and not removed:
            return sorted(set(prev_rows) | added)
        # Widget replaced selection with only the clicked row — toggle that row.
        if len(new_rows) == 1:
            t = new_rows[0]
            if t in prev_rows:
                return sorted(r for r in prev_rows if r != t)
            return sorted(set(prev_rows) | {t})
        # One new row while others dropped from widget state — still add it.
        if len(added) == 1:
            return sorted(set(prev_rows) | added)
        return new_rows

    # Plain click: replace selection with the newly clicked row.
    if not shift_held:
        if len(added) == 1 and len(removed) == 1:
            return [next(iter(added))]
        if len(added) == 1 and prev_rows and len(new_rows) > 1:
            return [next(iter(added))]

    if len(new_rows) == 1:
        return new_rows

    if len(removed) == 1 and not added:
        return new_rows

    if shift_held and is_contiguous and len(new_rows) >= 2:
        return new_rows
    if len(added) >= 2 and is_contiguous:
        return new_rows

    if len(added) == 1:
        return [next(iter(added))]

    return [new_rows[-1]]


def rows_to_symbols(row_indices, summary_df):
    symbols = []
    last_row_idx = None
    for row_idx in sorted(row_indices):
        if row_idx < 0 or row_idx >= len(summary_df):
            continue
        sym = str(summary_df.iloc[row_idx]["Symbol"])
        symbols.append(sym)
        last_row_idx = row_idx
    return symbols, last_row_idx


def commit_selection_state(rows, summary_df):
    """Persist normalized row indices to export list and detail focus."""
    st.session_state.table_sel_rows = rows
    symbols, last_row_idx = rows_to_symbols(rows, summary_df)
    st.session_state.selected_symbols = symbols
    if not symbols:
        return
    focus = symbols[-1]
    if st.session_state.get("selected_symbol") != focus:
        st.session_state.selected_symbol = focus
        st.session_state.ticker_index = last_row_idx
        st.session_state["fibo_needs_refresh"] = True
        prioritize_metadata_symbol(focus)


def _raw_selection_rows(table_key: str, event_state=None) -> list[int]:
    """Read row indices from dataframe widget state or its return value."""
    sources = (event_state, st.session_state.get(table_key))
    for src in sources:
        if src is None:
            continue
        selection = src.get("selection") if hasattr(src, "get") else getattr(src, "selection", None)
        if not selection:
            continue
        rows = selection.get("rows") if hasattr(selection, "get") else getattr(selection, "rows", None)
        if rows is not None:
            return [int(r) for r in rows]
    return []


def _selection_widget_state(rows: list[int]) -> dict:
    return {"selection": {"rows": list(rows)}}


def _pending_selection_key(table_key: str) -> str:
    return f"_{table_key}_pending_rows"


def _apply_pending_widget_selection(summary_df, table_key: str) -> bool:
    """Apply normalized rows to widget state before st.dataframe (Streamlit requirement)."""
    pending_key = _pending_selection_key(table_key)
    pending = st.session_state.pop(pending_key, None)
    if pending is None:
        return False
    rows = sorted({int(r) for r in pending})
    commit_selection_state(rows, summary_df)
    st.session_state[table_key] = _selection_widget_state(rows)
    return True


def _technical_controls_changed() -> bool:
    """Detect TA control-only reruns to avoid mutating table selection."""
    current = {
        "sel_start_ui": st.session_state.get("sel_start_ui"),
        "sel_end_ui": st.session_state.get("sel_end_ui"),
        "calc_fib_start": st.session_state.get("calc_fib_start"),
        "calc_fib_end": st.session_state.get("calc_fib_end"),
        "fibo_trend_inspect": st.session_state.get("fibo_trend_inspect"),
    }
    previous = st.session_state.get("_last_tech_controls_state")
    st.session_state["_last_tech_controls_state"] = current
    if not previous:
        return False
    return any(current.get(k) != previous.get(k) for k in current)


def prepare_table_selection_before_render(summary_df, table_key: str = "portfolio_table") -> None:
    """Clear selection, apply pending normalization, or preserve on TA-only reruns."""
    _apply_pending_widget_selection(summary_df, table_key)

    if st.session_state.pop(_PRESERVE_SELECTION_KEY, False):
        prev_rows = st.session_state.get("table_sel_rows", [])
        if prev_rows:
            commit_selection_state(prev_rows, summary_df)
            st.session_state[table_key] = _selection_widget_state(prev_rows)
        st.session_state[_SKIP_SELECTION_APPLY_KEY] = True

    if st.session_state.pop("clear_table_selection", False):
        st.session_state.table_sel_rows = []
        st.session_state.selected_symbols = []
        st.session_state[table_key] = _selection_widget_state([])
        return

    if _technical_controls_changed():
        prev_rows = st.session_state.get("table_sel_rows", [])
        commit_selection_state(prev_rows, summary_df)
        st.session_state[table_key] = _selection_widget_state(prev_rows)


def apply_table_selection_after_widget(
    event,
    summary_df,
    table_key: str = "portfolio_table",
) -> None:
    """
    Normalize selection from the dataframe's current event (after user click).
    Must run after st.dataframe so the click is visible in widget state.
    """
    if st.session_state.pop(_SKIP_SELECTION_APPLY_KEY, False):
        return

    raw_rows = _raw_selection_rows(table_key, event_state=event)
    if not raw_rows and not st.session_state.get("table_sel_rows"):
        return

    prev_rows = st.session_state.get("table_sel_rows", [])
    shift_held, alt_held = get_table_click_modifiers()
    rows = normalize_table_selection_rows(
        raw_rows, prev_rows, shift_held=shift_held, alt_held=alt_held
    )
    commit_selection_state(rows, summary_df)

    canonical = sorted({int(r) for r in raw_rows})
    normalized = sorted({int(r) for r in rows})
    if normalized != canonical:
        # Widget state cannot be written after st.dataframe; fix on the next run.
        st.session_state[_pending_selection_key(table_key)] = normalized
        st.rerun()


def _column_display_name(column: str) -> str:
    """Plain header labels for the data editor."""
    labels = {
        "🌐 Price": "Price",
        "📈 Target": "Target",
        "📈 Total %": "Total %",
        "∆ Act-Target %": "Δ Act-Target %",
        "∆ Act-Est Target %": "Δ Act-Est Target %",
        "Ø CAGR": "CAGR",
    }
    return labels.get(column, column)


def format_display_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """Round numeric cells for consistent US-style display in tables."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if col not in TABLE_NUMBER_COLUMN_FORMAT:
            continue
        numeric = pd.to_numeric(out[col], errors="coerce")
        if col == "Div Yield":
            out[col] = numeric.round(1)
        elif col == "Shares":
            out[col] = numeric.round(2)
        else:
            out[col] = numeric.round(2)
    return out


def get_portfolio_table_column_config(columns, *, editable: bool = False):
    """
    Column config; Symbol pinned. Consistent $ / % formats on numeric columns.

    For st.dataframe (read-only), omit disabled= so every column can be sorted.
    For st.data_editor, disabled= locks non-editable columns (and blocks their sort).
    """
    config = {}
    if "Symbol" in columns:
        sym_kw: dict = {"pinned": True, "width": "small"}
        if editable:
            sym_kw["disabled"] = "Symbol" not in ROI_EDITABLE_COLUMNS
        config["Symbol"] = st.column_config.TextColumn("Symbol", **sym_kw)
    if "PurchaseDate" in columns:
        pd_kw: dict = {}
        if editable:
            pd_kw["disabled"] = "PurchaseDate" not in ROI_EDITABLE_COLUMNS
        pd_kw["format"] = "YYYY-MM-DD"
        config["PurchaseDate"] = st.column_config.DateColumn("Purchase date", **pd_kw)
    if "Currency" in columns:
        cur_kw: dict = {"options": ["USD", "EUR"], "required": True}
        if editable:
            cur_kw["disabled"] = "Currency" not in ROI_EDITABLE_COLUMNS
        config["Currency"] = st.column_config.SelectboxColumn("Currency", **cur_kw)

    editable_numeric = set(ROI_EDITABLE_COLUMNS) if editable else set()
    for col, fmt in TABLE_NUMBER_COLUMN_FORMAT.items():
        if col not in columns:
            continue
        kwargs: dict = {
            "label": _column_display_name(col),
            "format": fmt,
        }
        if editable:
            kwargs["disabled"] = col not in editable_numeric
            if col in editable_numeric:
                kwargs["min_value"] = 0
        config[col] = st.column_config.NumberColumn(**kwargs)

    return config


def get_table_format_dict(columns):
    """Pandas Styler formats — $ prefix, % suffix, thousands separators."""
    format_dict = {}
    for col in TABLE_PERCENT_COLS:
        if col in columns:
            format_dict[col] = "{:.2f}%"
    if "Div Yield" in columns:
        format_dict["Div Yield"] = "{:.1f}%"
    for col in TABLE_CURRENCY_COLS:
        if col in columns:
            format_dict[col] = "${:,.2f}"
    if "Shares" in columns:
        format_dict["Shares"] = "{:,.2f}"
    return format_dict


def _view_columns(view_name, summary_df):
    cols = [c for c in TABLE_VIEW_COLUMNS[view_name] if c in summary_df.columns]
    if view_name == "ROI" and "Currency" not in cols:
        if "Cost/Share" in cols:
            cols.insert(cols.index("Cost/Share") + 1, "Currency")
        else:
            cols.append("Currency")
    if "Symbol" in summary_df.columns and "Symbol" not in cols:
        cols = ["Symbol"] + cols
    return cols


def _render_add_symbol_bar(portfolio_id: int) -> bool:
    st.markdown('<div class="portfolio-edit-anchor"></div>', unsafe_allow_html=True)
    add_col, del_col, sym_col, cur_col, save_col = st.columns(
        [0.95, 1.15, 2.8, 0.75, 1.05], gap="small", vertical_alignment="center"
    )
    with add_col:
        add_clicked = st.button(
            "Add symbol",
            use_container_width=True,
            key=f"portfolio_add_btn_{portfolio_id}",
            help="Add ticker (validated via Yahoo Finance)",
        )
    with del_col:
        selected_symbols = [
            str(s).strip().upper()
            for s in (st.session_state.get("selected_symbols") or [])
            if str(s).strip()
        ]
        delete_clicked = st.button(
            "Delete selected",
            use_container_width=True,
            key=f"portfolio_delete_selected_btn_{portfolio_id}",
            disabled=not selected_symbols,
            help="Delete checked rows from this portfolio draft",
        )
    with sym_col:
        raw = st.text_input(
            "Symbol",
            placeholder="e.g. AAPL",
            key=f"portfolio_add_symbol_{portfolio_id}",
            label_visibility="collapsed",
        )
    with cur_col:
        currency = st.selectbox(
            "Currency",
            options=["USD", "EUR"],
            key=f"portfolio_add_currency_{portfolio_id}",
            label_visibility="collapsed",
        )
    with save_col:
        save_clicked = st.button(
            "Save portfolio",
            type="primary",
            use_container_width=True,
            key=f"portfolio_save_btn_{portfolio_id}",
        )

    if delete_clicked:
        holdings = get_editable_holdings_df()
        if holdings is None or holdings.empty:
            st.info("No rows to delete.")
            return save_clicked
        before = len(holdings)
        updated = holdings[
            ~holdings["Symbol"].astype(str).str.strip().str.upper().isin(selected_symbols)
        ].reset_index(drop=True)
        removed = before - len(updated)
        if removed <= 0:
            st.info("No matching selected rows to delete.")
            return save_clicked
        set_holdings_draft(portfolio_id, updated)
        st.session_state.clear_table_selection = True
        st.session_state.selected_symbols = []
        invalidate_analysis(refetch_metadata=False)
        st.success(f"Deleted {removed} row(s).")
        st.rerun()

    if add_clicked:
        symbol_input = (raw or "").strip()
        if not symbol_input:
            st.warning("Enter a ticker symbol.")
            return save_clicked

        with st.spinner(f"Checking {symbol_input.upper()}…"):
            valid, normalized, _ = validate_symbol(symbol_input)

        if not valid:
            st.error(
                f'"{symbol_input.upper()}" was not found on Yahoo Finance. '
                "Check the ticker and try again."
            )
            return save_clicked

        try:
            holdings = get_editable_holdings_df()
            updated = append_symbol_to_draft(
                portfolio_id, holdings, normalized, currency
            )
            set_holdings_draft(portfolio_id, updated)
            invalidate_analysis(refetch_metadata=False)
            st.session_state.portfolio_table_view = "ROI"
            st.success(
                f"Added {normalized} ({currency}). Fill in shares/cost, then Save portfolio."
            )
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    return save_clicked


def render_portfolio_table_readonly(
    summary_df,
    view_name,
    selection_df,
    table_key="portfolio_table",
):
    """Read-only styled table (Standard / Trends views)."""
    cols = _view_columns(view_name, summary_df)
    display_df = format_display_numerics(summary_df[cols].copy())
    format_dict = get_table_format_dict(cols)
    actual_format_dict = {k: v for k, v in format_dict.items() if k in display_df.columns}

    skip_fillna = METADATA_COLS | METADATA_LATE_COLS
    fill_cols = [
        c for c in TABLE_PERCENT_COLS + ["Div Yield"]
        if c in display_df.columns and c not in skip_fillna
    ]
    if fill_cols:
        display_df[fill_cols] = display_df[fill_cols].fillna(0)

    gradient_cols = [
        c
        for c in TABLE_PERCENT_COLS
        if c in display_df.columns
        and c in actual_format_dict
        and c not in TABLE_GRADIENT_EXCLUDE
    ] + [c for c in TABLE_PNL_COLS if c in display_df.columns]
    styled = display_df.style.format(actual_format_dict, na_rep="-").set_properties(
        **{"background-color": "white", "color": "black"}
    )
    if gradient_cols:
        styled = styled.apply(style_signed_column, subset=gradient_cols, axis=0)

    sel_rows = st.session_state.get("table_sel_rows", [])
    selection_default = _selection_widget_state(sel_rows) if sel_rows else None

    event = st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config=get_portfolio_table_column_config(cols, editable=False),
        on_select="rerun",
        selection_mode="multi-row",
        selection_default=selection_default,
        key=table_key,
    )
    apply_table_selection_after_widget(event, selection_df, table_key=table_key)


def _build_roi_display_df(summary_df, holdings_df) -> pd.DataFrame:
    """Prepare ROI table data (analysis rows merged with holdings draft)."""
    view_name = "ROI"
    if summary_df is not None and not summary_df.empty:
        cols = _view_columns(view_name, summary_df)
        base_cols = [c for c in cols if c in summary_df.columns]
        display_df = enrich_summary_with_currency(summary_df[base_cols], holdings_df)
    else:
        display_df = holdings_to_roi_display_df(holdings_df)
        cols = _view_columns(view_name, display_df)
    display_df = display_df[[c for c in cols if c in display_df.columns]]
    display_df = prepare_roi_editor_df(display_df)
    display_df = merge_holdings_into_roi_display(display_df, holdings_df)
    return format_display_numerics(display_df)


def _style_roi_dataframe(display_df: pd.DataFrame):
    """Same gradients/formatting as Standard/Trends for the sortable ROI view."""
    cols = list(display_df.columns)
    format_dict = get_table_format_dict(cols)
    actual_format_dict = {k: v for k, v in format_dict.items() if k in display_df.columns}

    skip_fillna = METADATA_COLS | METADATA_LATE_COLS
    fill_cols = [
        c
        for c in TABLE_PERCENT_COLS + ["Div Yield"]
        if c in display_df.columns and c not in skip_fillna
    ]
    out = display_df.copy()
    if fill_cols:
        out[fill_cols] = out[fill_cols].fillna(0)

    gradient_cols = [
        c
        for c in TABLE_PERCENT_COLS
        if c in out.columns
        and c in actual_format_dict
        and c not in TABLE_GRADIENT_EXCLUDE
    ] + [c for c in TABLE_PNL_COLS if c in out.columns]
    styled = out.style.format(actual_format_dict, na_rep="-").set_properties(
        **{"background-color": "white", "color": "black"}
    )
    if gradient_cols:
        styled = styled.apply(style_signed_column, subset=gradient_cols, axis=0)
    return styled


def _render_roi_dataframe(
    display_df: pd.DataFrame,
    selection_df: pd.DataFrame,
    table_key: str = "portfolio_table",
):
    """Sortable ROI table (st.dataframe — same key/state model as Standard/Trends)."""
    cols = list(display_df.columns)
    sel_rows = st.session_state.get("table_sel_rows", [])
    selection_default = _selection_widget_state(sel_rows) if sel_rows else None
    event = st.dataframe(
        _style_roi_dataframe(display_df),
        use_container_width=True,
        hide_index=True,
        column_config=get_portfolio_table_column_config(cols, editable=False),
        on_select="rerun",
        selection_mode="multi-row",
        selection_default=selection_default,
        key=table_key,
    )
    apply_table_selection_after_widget(event, selection_df, table_key=table_key)


def _render_roi_data_editor(display_df: pd.DataFrame) -> pd.DataFrame:
    """Editable ROI table when ⋮ menu is open (st.data_editor — limited column sort)."""
    disabled = [c for c in display_df.columns if c not in ROI_EDITABLE_COLUMNS]

    st.markdown('<div class="roi-table-anchor"></div>', unsafe_allow_html=True)
    edited = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config=get_portfolio_table_column_config(
            list(display_df.columns), editable=True
        ),
        disabled=disabled,
        key="portfolio_table_roi_editor",
    )

    roi_errors = validate_roi_editor_df(edited)
    if roi_errors:
        st.caption("Fix these fields in the table before saving:")
        for msg in roi_errors:
            st.warning(msg)

    return edited


def render_portfolio_table_roi(
    summary_df,
    holdings_df,
    selection_df: pd.DataFrame,
    table_key: str = "portfolio_table",
) -> pd.DataFrame:
    """
    ROI view: always show a sortable dataframe (like Standard/Trends).
    When ⋮ is open, an edit table appears below for inline holdings changes.
    """
    display_df = _build_roi_display_df(summary_df, holdings_df)
    _render_roi_dataframe(display_df, selection_df, table_key=table_key)
    if is_portfolio_more_open():
        with st.expander("Edit portfolio rows", expanded=False):
            return _render_roi_data_editor(display_df)
    return display_df


def _selection_df_for_view(view_name: str, summary_df: pd.DataFrame, holdings_df) -> pd.DataFrame:
    """Row index source for selection reconcile — must match the rendered table."""
    if view_name == "ROI":
        has_holdings = holdings_df is not None and not holdings_df.empty
        if not has_holdings and summary_df.empty:
            return pd.DataFrame()
        return _build_roi_display_df(summary_df, holdings_df)
    return summary_df


def render_portfolio_table_section():
    """Portfolio table with view switcher; ROI view supports inline holdings edits."""
    results = st.session_state.get("all_results") or []
    summary_df = pd.DataFrame([x["data"] for x in results]) if results else pd.DataFrame()

    active = load_active_portfolio()
    portfolio_id = active.portfolio_id
    holdings_df = get_editable_holdings_df()

    view_options = list(TABLE_VIEW_COLUMNS.keys())
    default_view = st.session_state.get("portfolio_table_view", view_options[0])
    if default_view not in view_options:
        default_view = view_options[0]

    if "portfolio_table_view" not in st.session_state:
        st.session_state.portfolio_table_view = default_view

    save_clicked = False
    if is_portfolio_more_open():
        save_clicked = _render_add_symbol_bar(portfolio_id)

    # Render view switcher before selection reconcile so reruns keep the active tab.
    view_name = st.radio(
        "View",
        view_options,
        horizontal=True,
        key="portfolio_table_view",
        label_visibility="collapsed",
    )

    selection_df = _selection_df_for_view(view_name, summary_df, holdings_df)
    if not selection_df.empty:
        prepare_table_selection_before_render(selection_df)

    portfolio_metadata_progress()

    has_holdings = holdings_df is not None and not holdings_df.empty

    if view_name == "ROI":
        if not has_holdings:
            if is_portfolio_more_open():
                st.caption("No symbols yet — add one above, then **Save portfolio**.")
            else:
                st.caption("No symbols yet — open **⋮** to add holdings.")
            edited = holdings_df
        elif summary_df.empty:
            st.caption("Edit holdings below, then **Save portfolio** (prices load after save).")
            edited = render_portfolio_table_roi(
                summary_df, holdings_df, selection_df, table_key="portfolio_table"
            )
        else:
            edited = render_portfolio_table_roi(
                summary_df, holdings_df, selection_df, table_key="portfolio_table"
            )
        if save_clicked:
            roi_errors = validate_roi_editor_df(edited)
            if roi_errors:
                st.error("Cannot save — complete all required fields in the ROI table:")
                for msg in roi_errors:
                    st.warning(msg)
            else:
                try:
                    if summary_df.empty and has_holdings:
                        holdings_out = display_df_to_holdings(edited)
                    elif summary_df.empty:
                        holdings_out = get_editable_holdings_df()
                        if holdings_out.empty:
                            raise ValueError("Add at least one symbol before saving.")
                    else:
                        holdings_out = display_df_to_holdings(edited)
                    save_holdings_from_df(portfolio_id, holdings_out)
                    st.success("Portfolio saved.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Could not save: {e}")
    elif not summary_df.empty:
        render_portfolio_table_readonly(
            summary_df, view_name, selection_df, table_key="portfolio_table"
        )
    else:
        st.caption("Load symbols to see Standard and Trends views.")

    if view_name != "ROI":
        st.caption(
            "Click = single row · **Shift+click** = range · **Alt/Option+click** = toggle row · "
            "uncheck = remove"
        )
