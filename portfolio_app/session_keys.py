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


def clear_portfolio_table_widget():
    import streamlit as st

    if "portfolio_table" in st.session_state:
        del st.session_state["portfolio_table"]
