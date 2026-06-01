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
    VALUATION_COLS,
    VALUATION_LATE_COLS,
)
from portfolio_app.data.market_data import validate_symbol
from portfolio_app.data.metadata import portfolio_metadata_progress, prioritize_metadata_symbol
from portfolio_app.analysis.valuation_scores import build_valuation_legend_sections
from portfolio_app.data.valuation_metadata import (
    portfolio_valuation_progress,
    prioritize_valuation_symbol,
)
from portfolio_app.services.session_context import invalidate_analysis, load_active_portfolio
from portfolio_app.ui.portfolio_grid import portfolio_grid
from portfolio_app.ui.toolbar import is_portfolio_more_open

_PRESERVE_SELECTION_KEY = "_preserve_table_selection"
from portfolio_app.ui.holdings import (
    ROI_EDITABLE_COLUMNS,
    append_symbol_to_draft,
    clear_holdings_draft,
    display_df_to_holdings,
    get_editable_holdings_df,
    holdings_to_roi_display_df,
    merge_holdings_into_roi_display,
    prepare_roi_editor_df,
    save_holdings_from_df,
    set_holdings_draft,
    validate_roi_editor_df,
)
from portfolio_app.ui.table_style import gradient_backgrounds



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
        prioritize_metadata_symbol(focus)
        prioritize_valuation_symbol(focus)


def apply_grid_selection(result, summary_df) -> None:
    """Apply AG Grid component output — selection intent is already resolved in JS."""
    if not result:
        return
    rows = sorted({int(r) for r in (result.get("rows") or [])})
    stored = sorted({int(r) for r in st.session_state.get("table_sel_rows", [])})
    if rows == stored:
        return
    commit_selection_state(rows, summary_df)


def _grid_selected_rows(table_key: str = "portfolio_grid") -> list[int]:
    """Row indices to pass into the grid — prefer live widget value over session lag."""
    widget = st.session_state.get(table_key)
    if isinstance(widget, dict) and widget.get("rows") is not None:
        return sorted({int(r) for r in widget["rows"]})
    return sorted({int(r) for r in st.session_state.get("table_sel_rows", [])})


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


def prepare_table_selection_before_render(summary_df) -> None:
    """Preserve or clear AG Grid row selection across non-table reruns."""
    if st.session_state.pop("clear_table_selection", False):
        st.session_state.table_sel_rows = []
        st.session_state.selected_symbols = []
        st.session_state.pop("portfolio_grid", None)
        return

    if st.session_state.pop(_PRESERVE_SELECTION_KEY, False):
        prev_rows = st.session_state.get("table_sel_rows", [])
        if prev_rows:
            commit_selection_state(prev_rows, summary_df)
        return

    if _technical_controls_changed():
        prev_rows = st.session_state.get("table_sel_rows", [])
        if prev_rows:
            commit_selection_state(prev_rows, summary_df)


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
    Column config for the ROI st.data_editor — disabled= locks non-editable columns.
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
    if "Grade" in columns:
        config["Grade"] = st.column_config.TextColumn("Grade", width="small")

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


def _format_grid_cell(column: str, value) -> str:
    """Display strings for AG Grid cells."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    if column in TABLE_CURRENCY_COLS:
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)
    if column in TABLE_PERCENT_COLS:
        try:
            return f"{float(value):.2f}%"
        except (TypeError, ValueError):
            return str(value)
    if column == "Div Yield":
        try:
            return f"{float(value):.1f}%"
        except (TypeError, ValueError):
            return str(value)
    if column == "Shares":
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)
    if column in {"Trailing P/E", "Forward P/E", "PEG"}:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
    if column in {"PEG P-Score", "Rev P-Score", "Margin P-Score"}:
        try:
            return f"{float(value):.0f}"
        except (TypeError, ValueError):
            return str(value)
    if column == "P-Score":
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return str(value)
    if column == "PurchaseDate":
        if pd.isna(value):
            return "-"
        try:
            return pd.Timestamp(value).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _gradient_columns_for_view(display_df: pd.DataFrame, cols) -> list[str]:
    format_dict = get_table_format_dict(cols)
    actual_format_dict = {k: v for k, v in format_dict.items() if k in display_df.columns}
    pscore_cols = [
        c
        for c in ("PEG P-Score", "Rev P-Score", "Margin P-Score", "P-Score")
        if c in display_df.columns
    ]
    return [
        c
        for c in TABLE_PERCENT_COLS
        if c in display_df.columns
        and c in actual_format_dict
        and c not in TABLE_GRADIENT_EXCLUDE
    ] + [c for c in TABLE_PNL_COLS if c in display_df.columns] + pscore_cols


def _prepare_grid_display_df(
    view_name: str,
    summary_df: pd.DataFrame,
    holdings_df=None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    if view_name == "ROI":
        display_df = _build_roi_display_df(summary_df, holdings_df)
        skip_fillna = METADATA_COLS | METADATA_LATE_COLS
    else:
        cols = _view_columns(view_name, summary_df)
        display_df = format_display_numerics(summary_df[cols].copy())
        skip_fillna = METADATA_COLS | METADATA_LATE_COLS | VALUATION_COLS | VALUATION_LATE_COLS

    cols = list(display_df.columns)
    fill_cols = [
        c
        for c in TABLE_PERCENT_COLS + ["Div Yield"]
        if c in display_df.columns and c not in skip_fillna
    ]
    if fill_cols:
        display_df = display_df.copy()
        display_df[fill_cols] = display_df[fill_cols].fillna(0)

    gradient_cols = _gradient_columns_for_view(display_df, cols)
    return display_df, cols, gradient_cols


def _rows_for_grid(display_df: pd.DataFrame, gradient_cols: list[str]) -> list[dict]:
    style_columns = {}
    for col in gradient_cols:
        if col in display_df.columns:
            style_columns[col] = gradient_backgrounds(display_df[col])

    records = []
    for row_idx, (_, row) in enumerate(display_df.iterrows()):
        rec = {"__rowIndex": row_idx}
        styles = {}
        for col in gradient_cols:
            if col in style_columns:
                styles[col] = style_columns[col][row_idx]
        if styles:
            rec["__styles"] = styles
        for col in display_df.columns:
            rec[col] = _format_grid_cell(col, row[col])
        records.append(rec)
    return records


def _grid_column_defs(columns, gradient_cols) -> list[dict]:
    gradient_set = set(gradient_cols)
    defs = []
    for col in columns:
        spec = {
            "field": col,
            "headerName": _column_display_name(col),
            "sortable": True,
            "resizable": True,
        }
        if col in gradient_set:
            spec["gradient"] = True
        if col == "Symbol":
            spec["pinned"] = "left"
            spec["width"] = 96
            spec["minWidth"] = 80
        defs.append(spec)
    return defs


def _grid_height(row_count: int) -> int:
    return min(max(120, 42 + 32 * max(row_count, 1)), 520)


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


def render_portfolio_table_grid(
    selection_df,
    *,
    summary_df,
    view_name="Standard",
    holdings_df=None,
    table_key="portfolio_grid",
):
    """AG Grid table for all portfolio views (ROI read-only grid + analysis views)."""
    display_df, cols, gradient_cols = _prepare_grid_display_df(
        view_name, summary_df, holdings_df=holdings_df
    )

    widget = st.session_state.get(table_key)
    if isinstance(widget, dict):
        apply_grid_selection(widget, selection_df)

    sel_rows = _grid_selected_rows(table_key)

    result = portfolio_grid(
        rows=_rows_for_grid(display_df, gradient_cols),
        column_defs=_grid_column_defs(cols, gradient_cols),
        selected_rows=sel_rows,
        height=_grid_height(len(display_df)),
        key=table_key,
        default=None,
    )
    apply_grid_selection(result, selection_df)


def render_portfolio_table_readonly(summary_df, view_name, selection_df):
    """Read-only AG Grid (Standard / Trends / Valuation Growth)."""
    render_portfolio_table_grid(
        selection_df,
        summary_df=summary_df,
        view_name=view_name,
    )


def _build_roi_display_df(summary_df, holdings_df) -> pd.DataFrame:
    """Prepare ROI table data (analysis rows merged with holdings draft)."""
    view_name = "ROI"
    if summary_df is not None and not summary_df.empty:
        cols = _view_columns(view_name, summary_df)
        base_cols = [c for c in cols if c in summary_df.columns]
        display_df = summary_df[base_cols].copy()
    else:
        display_df = holdings_to_roi_display_df(holdings_df)
        cols = _view_columns(view_name, display_df)
    display_df = display_df[[c for c in cols if c in display_df.columns]]
    display_df = prepare_roi_editor_df(display_df)
    display_df = merge_holdings_into_roi_display(display_df, holdings_df)
    return format_display_numerics(display_df)


def render_portfolio_table_roi(
    summary_df,
    holdings_df,
    selection_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    ROI view: AG Grid for selection/sorting; st.data_editor below when ⋮ is open.
    """
    display_df = _build_roi_display_df(summary_df, holdings_df)
    render_portfolio_table_grid(
        selection_df,
        summary_df=summary_df,
        view_name="ROI",
        holdings_df=holdings_df,
    )
    if is_portfolio_more_open():
        with st.expander("Edit portfolio rows", expanded=False):
            return _render_roi_data_editor(display_df)
    return display_df


def _render_roi_data_editor(display_df: pd.DataFrame) -> pd.DataFrame:
    """Editable ROI table when ⋮ menu is open (st.data_editor)."""
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
    active = load_active_portfolio()
    portfolio_id = active.portfolio_id
    holdings_df = get_editable_holdings_df()

    results = st.session_state.get("all_results") or []
    if holdings_df.empty:
        summary_df = pd.DataFrame()
    elif results:
        summary_df = pd.DataFrame([x["data"] for x in results])
    else:
        summary_df = pd.DataFrame()

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
    portfolio_valuation_progress()

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
            edited = render_portfolio_table_roi(summary_df, holdings_df, selection_df)
        else:
            edited = render_portfolio_table_roi(summary_df, holdings_df, selection_df)
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
        render_portfolio_table_readonly(summary_df, view_name, selection_df)
    else:
        st.caption("Load symbols to see analysis views (Standard, Trends, Valuation Growth).")

    if view_name == "Valuation Growth":
        results = st.session_state.get("all_results") or []
        headline, detail_lines, holding_lines = build_valuation_legend_sections(
            results,
            portfolio_name=active.name,
            valuation_loaded=bool(st.session_state.get("valuation_loaded")),
            selected_symbols=st.session_state.get("selected_symbols") or [],
        )
        st.caption(headline)
        with st.expander("P-Score values — all holdings", expanded=False):
            if holding_lines:
                st.code("\n".join(holding_lines), language=None)
            for line in detail_lines:
                st.caption(line)

    table_visible = (view_name == "ROI" and has_holdings) or (
        view_name != "ROI" and not summary_df.empty
    )
    if table_visible:
        st.caption(
            "**Click** = select only that row · **Shift+click** = range · "
            "**Option+click** = toggle that row only"
        )
