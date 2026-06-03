"""Session state keys cleared on reset or refresh."""

PORTFOLIO_RESET_KEYS = (
    "all_results",
    "show_upload_dialog",
    "upload_dismiss_key",
    "metadata_enriched",
    "metadata_bg_active",
    "metadata_queue",
    "metadata_total",
    "enriched_symbols",
    "current_loaded_name",
    "analysis_portfolio_key",
    "analyst_loaded_notice_at",
    "valuation_queue",
    "valuation_total",
    "valuation_bg_active",
    "valuation_loaded",
    "valuation_enriched_symbols",
    "valuation_loaded_notice_at",
    "selected_symbol",
    "selected_symbols",
    "table_sel_rows",
    "ticker_index",
    "portfolio_table_view",
    "clear_table_selection",
)

REFRESH_CLEAR_KEYS = (
    "all_results",
    "current_loaded_name",
    "analysis_portfolio_key",
    "metadata_enriched",
    "metadata_bg_active",
    "metadata_queue",
    "metadata_total",
    "enriched_symbols",
    "analyst_loaded_notice_at",
    "valuation_queue",
    "valuation_total",
    "valuation_bg_active",
    "valuation_loaded",
    "valuation_enriched_symbols",
    "valuation_loaded_notice_at",
    "selected_symbol",
    "selected_symbols",
    "table_sel_rows",
    "ticker_index",
    "portfolio_table_view",
    "clear_table_selection",
)


def clear_session_keys(keys):
    import streamlit as st

    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


PRESERVE_TABLE_SELECTION_KEY = "_preserve_table_selection"


def portfolio_grid_widget_key() -> str:
    """Streamlit widget key — bump layout gen to remount grid after toolbar layout changes."""
    import streamlit as st

    gen = st.session_state.get("portfolio_grid_layout_gen", 0)
    return f"portfolio_grid_{gen}"


def bump_portfolio_grid_layout() -> None:
    """Force AG Grid remount when page layout above the table changes (e.g. ⋮ actions row)."""
    import streamlit as st

    st.session_state.portfolio_grid_layout_gen = (
        int(st.session_state.get("portfolio_grid_layout_gen", 0)) + 1
    )


def preserve_portfolio_table_selection() -> None:
    import streamlit as st

    st.session_state[PRESERVE_TABLE_SELECTION_KEY] = True


def notify_portfolio_toolbar_layout_changed() -> None:
    """Remount AG Grid after the expandable Portfolio/File actions row toggles."""
    bump_portfolio_grid_layout()
    clear_portfolio_table_widget()
    preserve_portfolio_table_selection()


def clear_portfolio_table_widget():
    import streamlit as st

    st.session_state.pop(portfolio_grid_widget_key(), None)
    if "portfolio_grid" in st.session_state:
        del st.session_state["portfolio_grid"]
