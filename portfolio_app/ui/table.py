"""Portfolio table views, multi-row selection, and styling."""
import pandas as pd
import streamlit as st

from portfolio_app.config import (
    METADATA_COLS,
    METADATA_LATE_COLS,
    TABLE_CURRENCY_COLS,
    TABLE_GRADIENT_EXCLUDE,
    TABLE_PERCENT_COLS,
    TABLE_PNL_COLS,
    TABLE_VIEW_COLUMNS,
)
from portfolio_app.data.metadata import prioritize_metadata_symbol
from portfolio_app.ui.components import get_table_click_modifiers
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
        if len(removed) == 1 and not added:
            return new_rows
        if len(added) == 1 and not removed:
            return sorted(set(prev_rows) | added)
        return new_rows

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


def reconcile_table_selection_before_render(summary_df, table_key="portfolio_table"):
    """
    Normalize selection before st.dataframe mounts.
    Streamlit updates session state from the UI before the script runs; we align
    it here so rapid clicks do not race with post-render corrections.
    """
    if st.session_state.pop("clear_table_selection", False):
        st.session_state.table_sel_rows = []
        st.session_state.selected_symbols = []
        st.session_state[table_key] = {"selection": {"rows": []}}
        return False

    raw_rows = []
    widget_state = st.session_state.get(table_key)
    if isinstance(widget_state, dict):
        raw_rows = list(widget_state.get("selection", {}).get("rows", []))

    prev_rows = st.session_state.get("table_sel_rows", [])
    shift_held, alt_held = get_table_click_modifiers()
    rows = normalize_table_selection_rows(
        raw_rows, prev_rows, shift_held=shift_held, alt_held=alt_held
    )
    commit_selection_state(rows, summary_df)

    canonical = sorted({int(r) for r in raw_rows})
    if rows != canonical:
        st.session_state[table_key] = {"selection": {"rows": rows}}
        st.rerun()
        return True
    return False


def get_table_format_dict(columns):
    """Column format strings for the styled portfolio table."""
    format_dict = {col: "{:.2f}%" for col in TABLE_PERCENT_COLS if col in columns}
    if "Div Yield" in columns:
        format_dict["Div Yield"] = "{:.1f}%"
    for col in TABLE_CURRENCY_COLS:
        if col in columns:
            format_dict[col] = "{:.2f} $"
    return format_dict


def render_portfolio_table(summary_df, view_name, table_key="portfolio_table"):
    """Render one table detail view; returns the dataframe selection event."""
    cols = [c for c in TABLE_VIEW_COLUMNS[view_name] if c in summary_df.columns]
    if "Symbol" in summary_df.columns and "Symbol" not in cols:
        cols = ["Symbol"] + cols

    display_df = summary_df[cols].copy()
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

    return st.dataframe(
        styled,
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=table_key,
    )


def render_portfolio_table_section():
    """Tabbed column views with one multi-select table on the active tab only."""
    summary_df = pd.DataFrame([x["data"] for x in st.session_state.all_results])
    if reconcile_table_selection_before_render(summary_df):
        return
    view_options = list(TABLE_VIEW_COLUMNS.keys())
    default_view = st.session_state.get("portfolio_table_view", view_options[0])
    if default_view not in view_options:
        default_view = view_options[0]

    tab_widgets = st.tabs(
        view_options,
        key="portfolio_table_view",
        default=default_view,
        on_change="rerun",
    )

    for view_name, tab in zip(view_options, tab_widgets):
        if tab.open:
            with tab:
                render_portfolio_table(summary_df, view_name, table_key="portfolio_table")

    selected_symbols = st.session_state.get("selected_symbols") or []
    focus = st.session_state.get("selected_symbol")
    if selected_symbols:
        sym_label = ", ".join(selected_symbols) if len(selected_symbols) <= 4 else (
            f"{', '.join(selected_symbols[:3])}, +{len(selected_symbols) - 3} more"
        )
        st.caption(
            f"**{len(selected_symbols)}** selected for export ({sym_label})"
            + (f" · Detail: **{focus}**" if focus else "")
        )
    else:
        st.caption(
            "Click = single row · **Shift+click** = range · **Alt+click** = toggle row · "
            "uncheck = remove"
        )
