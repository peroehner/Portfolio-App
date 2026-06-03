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
    ROI_FOOTER_SUM_COLUMNS,
    TABLE_VIEW_COLUMNS,
    VALUATION_COLS,
    VALUATION_LATE_COLS,
)
from portfolio_app.analysis.returns import value_to_target_gap_pct
from portfolio_app.data.market_data import validate_symbol
from portfolio_app.data.portfolio_loader import parse_shares_number
from portfolio_app.data.metadata import portfolio_metadata_progress, prioritize_metadata_symbol
from portfolio_app.analysis.valuation_scores import build_valuation_legend_sections
from portfolio_app.data.valuation_metadata import (
    portfolio_valuation_progress,
    prioritize_valuation_symbol,
)
from portfolio_app.services.session_context import invalidate_analysis, load_active_portfolio
from portfolio_app.ui.components import render_financial_data_loading_umbrella
from portfolio_app.ui.portfolio_grid import portfolio_grid
from portfolio_app.session_keys import (
    PRESERVE_TABLE_SELECTION_KEY,
    portfolio_grid_widget_key,
)
from portfolio_app.ui.toolbar import render_portfolio_more_button
from portfolio_app.ui.holdings import (
    HOLDINGS_EDITOR_COLUMNS,
    ROI_EDITABLE_COLUMNS,
    append_symbol_to_draft,
    get_editable_holdings_df,
    get_holdings_editor_column_config,
    has_holdings_draft,
    holdings_editor_duplicates_hint,
    holdings_editor_widget_key,
    holdings_to_roi_display_df,
    merge_holdings_into_roi_display,
    parse_holdings_editor_df,
    prepare_holdings_editor_df,
    prepare_roi_editor_df,
    render_holdings_save_error,
    save_holdings_from_df,
    set_holdings_draft,
    set_holdings_save_error,
    validate_holdings_editor_df,
)
from portfolio_app.ui.table_sort import (
    apply_table_sort,
    handle_sort_header_click,
    row_indices_for_symbols,
    sort_header_suffix,
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


_HANDLED_SORT_CLICK_ID_KEY = "_portfolio_handled_sort_click_id"


def _handle_grid_sort_click(result, view_name: str, display_df: pd.DataFrame) -> bool:
    """Process header sort click from AG Grid; returns True if sort changed."""
    sort_click = result.get("sort_click") if isinstance(result, dict) else None
    if not sort_click or not sort_click.get("column"):
        return False
    click_id = sort_click.get("id")
    if click_id is not None:
        last_id = st.session_state.get(_HANDLED_SORT_CLICK_ID_KEY)
        if last_id is not None and int(click_id) <= int(last_id):
            return False
        st.session_state[_HANDLED_SORT_CLICK_ID_KEY] = int(click_id)
    handle_sort_header_click(
        view_name,
        sort_click["column"],
        display_df=display_df,
    )
    return True


def apply_grid_selection(result, summary_df, *, skip_if_sort: bool = False) -> None:
    """Apply AG Grid component output — selection intent is already resolved in JS."""
    if not result:
        return
    if skip_if_sort and result.get("sort_click"):
        return
    rows = sorted({int(r) for r in (result.get("rows") or [])})
    stored = sorted({int(r) for r in st.session_state.get("table_sel_rows", [])})
    if rows == stored:
        return
    commit_selection_state(rows, summary_df)


def _grid_selected_rows(table_key: str | None = None) -> list[int]:
    if table_key is None:
        table_key = portfolio_grid_widget_key()
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
        from portfolio_app.session_keys import clear_portfolio_table_widget

        clear_portfolio_table_widget()
        return

    if st.session_state.pop(PRESERVE_TABLE_SELECTION_KEY, False):
        prev_rows = st.session_state.get("table_sel_rows", [])
        if prev_rows:
            commit_selection_state(prev_rows, summary_df)
        return

    if _technical_controls_changed():
        prev_rows = st.session_state.get("table_sel_rows", [])
        if prev_rows:
            commit_selection_state(prev_rows, summary_df)


def _column_display_name(column: str) -> str:
    """Plain header labels for the ROI data editor."""
    labels = {
        "🌐 Price": "Price",
        "📈 Target": "Target",
        "📈 Total %": "Total %",
        "∆ Act-Target %": "Δ Act-Target %",
        "∆ Act-Est Target %": "Δ Act-Est Target %",
        "Ø CAGR": "CAGR",
    }
    return labels.get(column, column)


def _gap_pct_series(value: pd.Series, target: pd.Series) -> pd.Series:
    """Vectorized value_to_target_gap_pct — matches Total row logic."""
    v = pd.to_numeric(value, errors="coerce")
    t = pd.to_numeric(target, errors="coerce")
    gap = (t - v) / v * 100.0
    return gap.where((v > 0) & v.notna() & t.notna())


def enrich_roi_calculated_columns(df: pd.DataFrame) -> pd.DataFrame:
    """ROI-only $ columns and Δ Tgt% / Δ Est% from Value vs target $ totals."""
    if df is None or df.empty:
        return df
    out = df.copy()
    shares = pd.to_numeric(out.get("Shares"), errors="coerce")
    price = pd.to_numeric(out.get("🌐 Price"), errors="coerce")
    cost = pd.to_numeric(out.get("Cost/Share"), errors="coerce")
    target = pd.to_numeric(out.get("📈 Target"), errors="coerce")
    est_target = pd.to_numeric(out.get("Est Target"), errors="coerce")
    out["Value"] = shares * price
    out["Invest"] = shares * cost
    out["📈 Target Val"] = shares * target
    out["Est Target Val"] = shares * est_target
    out["∆ Act-Target %"] = _gap_pct_series(out["Value"], out["📈 Target Val"])
    out["∆ Act-Est Target %"] = _gap_pct_series(out["Value"], out["Est Target Val"])
    return out


def _grid_header_name(column: str) -> str:
    """Compact AG Grid headers to fit more columns without horizontal scroll."""
    labels = {
        "🌐 Price": "Price",
        "📈 Target": "Target",
        "📈 Total %": "Total %",
        "∆ Act-Target %": "Δ Tgt%",
        "∆ Act-Est Target %": "Δ Est%",
        "Ø CAGR": "CAGR",
        "PurchaseDate": "Purch",
        "Cost/Share": "Cost",
        "Div Income": "Div $",
        "Est Target": "Est Tgt",
        "Div Yield": "Div%",
        "Value": "Value",
        "Invest": "Invest",
        "📈 Target Val": "Tgt Val",
        "Est Target Val": "Est Val",
        "Trailing P/E": "Trail P/E",
        "Forward P/E": "Fwd P/E",
        "Rev Growth %": "Rev Gr%",
        "Op Margin %": "Op Mgn%",
        "PEG P-Score": "PEG PS",
        "Rev P-Score": "Rev PS",
        "Margin P-Score": "Mrg PS",
        "P-Score": "P-Scr",
    }
    return labels.get(column, column)


def _grid_min_width(column: str) -> int:
    if column == "Symbol":
        return 54
    if column in {
        "5D", "1M", "6M", "12M", "PEG", "Grade", "Shares", "P-Score",
        "Value", "Invest", "📈 Target Val", "Est Target Val",
    }:
        return 44
    if column in {"Change %", "Upside %", "Div Yield"}:
        return 48
    if column == "PurchaseDate":
        return 54
    return 50


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


_ROI_COMPACT_CURRENCY_COLS = {
    "Value", "Invest", "Div Income", "📈 Target Val", "Est Target Val",
}
_ROI_WHOLE_PERCENT_COLS = {"∆ Act-Target %", "∆ Act-Est Target %"}


def _grid_cell_format(column: str) -> str | None:
    """AG Grid valueFormatter key — None means show raw text."""
    if column in {"Symbol", "Grade", "Currency"}:
        return None
    if column == "PurchaseDate":
        return "date"
    if column in _ROI_COMPACT_CURRENCY_COLS:
        return "currency0"
    if column in _ROI_WHOLE_PERCENT_COLS:
        return "percent0"
    if column in TABLE_CURRENCY_COLS:
        return "currency"
    if column in TABLE_PERCENT_COLS:
        return "percent2"
    if column == "Div Yield":
        return "percent1"
    if column == "Shares":
        return "shares"
    if column in {"Trailing P/E", "Forward P/E", "PEG"}:
        return "number2"
    if column in {"PEG P-Score", "Rev P-Score", "Margin P-Score"}:
        return "number0"
    if column == "P-Score":
        return "number1"
    return None


def _grid_cell_value(column: str, value):
    """Raw cell values for AG Grid — numeric columns stay numeric so sort works."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if column in {"Symbol", "Grade", "Currency"}:
        return str(value)
    if column == "PurchaseDate":
        try:
            return pd.Timestamp(value).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
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


def _roi_pinned_bottom_row(
    display_df: pd.DataFrame, columns: list[str] | None = None
) -> dict | None:
    """Footer row: Total $ sums plus portfolio Δ Tgt% / Δ Est% from value vs target totals."""
    if display_df is None or display_df.empty:
        return None
    cols = columns if columns is not None else list(display_df.columns)
    row: dict = {"Symbol": "Total", "__isFooter": True}
    for col in cols:
        if col != "Symbol":
            row[col] = None
    has_content = False
    for col in ROI_FOOTER_SUM_COLUMNS:
        if col not in display_df.columns:
            continue
        total = pd.to_numeric(display_df[col], errors="coerce").sum(min_count=1)
        if pd.notna(total):
            row[col] = float(total)
            has_content = True

    total_value = row.get("Value")
    total_tgt_val = row.get("📈 Target Val")
    total_est_val = row.get("Est Target Val")
    if total_value is not None and total_tgt_val is not None:
        tgt_pct = value_to_target_gap_pct(float(total_value), float(total_tgt_val))
        if tgt_pct is not None:
            row["∆ Act-Target %"] = tgt_pct
            has_content = True
    if total_value is not None and total_est_val is not None:
        est_pct = value_to_target_gap_pct(float(total_value), float(total_est_val))
        if est_pct is not None:
            row["∆ Act-Est Target %"] = est_pct
            has_content = True

    return row if has_content else None


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
            rec[col] = _grid_cell_value(col, row[col])
        records.append(rec)
    return records


def _grid_column_defs(columns, gradient_cols, view_name: str) -> list[dict]:
    gradient_set = set(gradient_cols)
    defs = []
    for col in columns:
        spec = {
            "field": col,
            "headerName": _grid_header_name(col) + sort_header_suffix(col),
            "sortable": False,
            "resizable": True,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
        }
        if col in gradient_set:
            spec["gradient"] = True
        cell_format = _grid_cell_format(col)
        if cell_format:
            spec["cellFormat"] = cell_format
        if col == "Symbol":
            spec["pinned"] = "left"
            spec["flex"] = 0
            spec["width"] = 64
            spec["minWidth"] = 54
            spec["maxWidth"] = 80
        else:
            spec["flex"] = 1
            spec["minWidth"] = _grid_min_width(col)
        defs.append(spec)
    return defs


def _grid_height(row_count: int, *, footer_rows: int = 0) -> int:
    return min(max(118, 40 + 30 * max(row_count + footer_rows, 1)), 520)


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
    configured = TABLE_VIEW_COLUMNS[view_name]
    if view_name == "ROI":
        cols = list(configured)
    elif summary_df is None or summary_df.empty:
        cols = list(configured)
    else:
        cols = [c for c in configured if c in summary_df.columns]
    if (
        summary_df is not None
        and not summary_df.empty
        and "Symbol" in summary_df.columns
        and "Symbol" not in cols
    ):
        cols = ["Symbol"] + cols
    return cols


def _render_add_symbol_bar(portfolio_id: int) -> bool:
    st.markdown('<div class="portfolio-edit-anchor"></div>', unsafe_allow_html=True)
    add_col, del_col, sym_col, shares_col, cur_col, save_col = st.columns(
        [0.85, 1.05, 2.0, 0.95, 0.65, 1.0], gap="small", vertical_alignment="center"
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
            help=(
                "Remove all draft lots for each selected symbol. "
                "To drop a single lot, delete its row in the holdings table below."
            ),
        )
    with sym_col:
        raw = st.text_input(
            "Symbol",
            placeholder="e.g. QBTS",
            key=f"portfolio_add_symbol_{portfolio_id}",
            label_visibility="collapsed",
        )
    with shares_col:
        shares_raw = st.text_input(
            "Shares",
            placeholder="Shares",
            key=f"portfolio_add_shares_{portfolio_id}",
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

        shares = parse_shares_number((shares_raw or "").strip())
        if pd.isna(shares) or shares <= 0:
            st.warning("Enter a positive share amount (e.g. 100 or 1.500 for 1,500).")
            return save_clicked

        try:
            holdings = get_editable_holdings_df()
            updated = append_symbol_to_draft(
                portfolio_id, holdings, normalized, currency, float(shares)
            )
            set_holdings_draft(portfolio_id, updated)
            st.session_state["_pending_expand_edit_portfolio"] = True
            st.session_state[_edit_portfolio_expander_open_key(portfolio_id)] = True
            # Defer tab switch until next run (before the radio widget is created).
            st.session_state["_pending_portfolio_table_view"] = "ROI"
            st.success(
                f"Added {normalized}: {shares:g} shares ({currency}) at the **top** of the holdings table. "
                "Set avg cost and target, then Save portfolio."
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
    table_key: str | None = None,
):
    """AG Grid table for all portfolio views (ROI read-only grid + analysis views)."""
    if table_key is None:
        table_key = portfolio_grid_widget_key()
    display_df, cols, gradient_cols = _prepare_grid_display_df(
        view_name, summary_df, holdings_df=holdings_df
    )

    # Unsorted df for header-click handling; display order applied after sort state.
    pre_sort_df = display_df.copy()

    display_df = apply_table_sort(display_df, view_name)

    selected_symbols = st.session_state.get("selected_symbols") or []
    if selected_symbols and "Symbol" in display_df.columns:
        remapped = row_indices_for_symbols(display_df, selected_symbols)
        if remapped:
            st.session_state.table_sel_rows = remapped

    sel_rows = _grid_selected_rows(table_key)

    pinned_bottom = None
    footer_rows = 0
    if view_name == "ROI":
        pinned_bottom = _roi_pinned_bottom_row(display_df, cols)
        footer_rows = 1 if pinned_bottom else 0

    result = portfolio_grid(
        rows=_rows_for_grid(display_df, gradient_cols),
        column_defs=_grid_column_defs(cols, gradient_cols, view_name),
        selected_rows=sel_rows,
        pinned_bottom_row=pinned_bottom,
        height=_grid_height(len(display_df), footer_rows=footer_rows),
        key=table_key,
        default=None,
    )
    sort_changed = _handle_grid_sort_click(result, view_name, pre_sort_df) if result else False
    if sort_changed:
        st.rerun()
    apply_grid_selection(result, selection_df, skip_if_sort=sort_changed)


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
    cols = _view_columns(view_name, summary_df)
    if summary_df is not None and not summary_df.empty:
        base_cols = [c for c in cols if c in summary_df.columns]
        display_df = summary_df[base_cols].copy()
    else:
        display_df = holdings_to_roi_display_df(holdings_df)
    display_df = prepare_roi_editor_df(display_df)
    display_df = merge_holdings_into_roi_display(display_df, holdings_df)
    display_df = enrich_roi_calculated_columns(display_df)
    display_df = display_df[[c for c in cols if c in display_df.columns]]
    return format_display_numerics(display_df)


def render_portfolio_table_roi(
    summary_df,
    holdings_df,
    selection_df: pd.DataFrame,
) -> None:
    """ROI view: AG Grid for selection and sorting."""
    render_portfolio_table_grid(
        selection_df,
        summary_df=summary_df,
        view_name="ROI",
        holdings_df=holdings_df,
    )


def _edit_portfolio_expander_open_key(portfolio_id: int) -> str:
    return f"portfolio_edit_expander_open_{portfolio_id}"


def _is_edit_portfolio_expander_open(portfolio_id: int) -> bool:
    """
    Keep Edit portfolio expanded across data_editor reruns (e.g. Tab between cells).
    Streamlit reruns the whole page on each edit; expanded=False collapses the section.
    """
    open_key = _edit_portfolio_expander_open_key(portfolio_id)
    if st.session_state.pop("_pending_expand_edit_portfolio", False):
        st.session_state[open_key] = True
    if has_holdings_draft(portfolio_id):
        st.session_state[open_key] = True
    if holdings_editor_widget_key(portfolio_id) in st.session_state:
        st.session_state[open_key] = True
    return bool(st.session_state.get(open_key, False))


def _render_edit_portfolio_expander(
    portfolio_id: int,
    holdings_df: pd.DataFrame,
) -> tuple[bool, pd.DataFrame]:
    """Holdings-only editor (six columns); available in every table view."""
    editor_df = prepare_holdings_editor_df(holdings_df)
    save_clicked = False
    draft_label = " (unsaved edits)" if has_holdings_draft(portfolio_id) else ""
    open_key = _edit_portfolio_expander_open_key(portfolio_id)
    with st.expander(
        f"Edit portfolio{draft_label}",
        expanded=_is_edit_portfolio_expander_open(portfolio_id),
    ):
        st.caption(
            "Your holdings only — the views above show **merged** totals per symbol until you save. "
            "New lots are inserted at the **top** of this table."
        )
        save_clicked = _render_add_symbol_bar(portfolio_id)
        edited = _holdings_editor_fragment(editor_df, portfolio_id=portfolio_id)
    st.session_state[open_key] = True
    return save_clicked, edited


@st.fragment
def _holdings_editor_fragment(editor_df: pd.DataFrame, *, portfolio_id: int) -> pd.DataFrame:
    """Isolate data_editor reruns so the parent expander does not flash collapsed."""
    return _render_holdings_data_editor(editor_df, portfolio_id=portfolio_id)


def _render_holdings_data_editor(editor_df: pd.DataFrame, *, portfolio_id: int) -> pd.DataFrame:
    """Editable holdings table (Symbol, Shares, AvgCost, PurchaseDate, Target, Currency)."""
    st.markdown('<div class="roi-table-anchor"></div>', unsafe_allow_html=True)
    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config=get_holdings_editor_column_config(),
        column_order=list(HOLDINGS_EDITOR_COLUMNS),
        key=holdings_editor_widget_key(portfolio_id),
    )

    render_holdings_save_error(portfolio_id, edited)

    dup_hint = holdings_editor_duplicates_hint(edited)
    if dup_hint:
        st.info(dup_hint)

    return edited


def _view_tab_label(view_name: str) -> str:
    """Short labels for Gmail-style view tabs."""
    return {
        "Valuation Growth": "Valuation",
    }.get(view_name, view_name)


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
    pending_view = st.session_state.pop("_pending_portfolio_table_view", None)
    if pending_view in view_options:
        st.session_state.portfolio_table_view = pending_view
    default_view = st.session_state.get("portfolio_table_view", view_options[0])
    if default_view not in view_options:
        default_view = view_options[0]

    if "portfolio_table_view" not in st.session_state:
        st.session_state.portfolio_table_view = default_view

    save_clicked = False
    edited = holdings_df

    # View switcher (+ ⋮) before selection reconcile so reruns keep the active tab.
    st.markdown('<div class="portfolio-view-tabs-anchor"></div>', unsafe_allow_html=True)
    view_col, more_col = st.columns([11.2, 0.55], gap="small", vertical_alignment="center")
    with view_col:
        view_name = st.radio(
            "View",
            view_options,
            horizontal=True,
            key="portfolio_table_view",
            label_visibility="collapsed",
            format_func=_view_tab_label,
        )
    with more_col:
        render_portfolio_more_button()

    selection_df = _selection_df_for_view(view_name, summary_df, holdings_df)
    if not selection_df.empty:
        prepare_table_selection_before_render(selection_df)

    render_financial_data_loading_umbrella(view_name)
    portfolio_metadata_progress()
    portfolio_valuation_progress()

    has_holdings = holdings_df is not None and not holdings_df.empty

    if view_name == "ROI":
        if not has_holdings:
            st.caption("No symbols yet — add one in **Edit portfolio** below.")
        render_portfolio_table_roi(summary_df, holdings_df, selection_df)
    elif not summary_df.empty:
        render_portfolio_table_readonly(summary_df, view_name, selection_df)
    else:
        st.caption("Load symbols to see analysis views (Standard, Trends, Valuation Growth).")

    save_clicked, edited = _render_edit_portfolio_expander(portfolio_id, holdings_df)

    if save_clicked:
        editor_errors = validate_holdings_editor_df(edited)
        try:
            holdings_out = parse_holdings_editor_df(edited)
        except ValueError as e:
            set_holdings_save_error(portfolio_id, str(e))
            st.rerun()
        else:
            if editor_errors:
                st.warning("Optional fixes before save:")
                for msg in editor_errors:
                    st.caption(msg)
            try:
                save_holdings_from_df(portfolio_id, holdings_out)
                st.success("Portfolio saved.")
                st.rerun()
            except ValueError as e:
                set_holdings_save_error(portfolio_id, str(e))
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")

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
