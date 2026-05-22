"""Upload, reset, and refresh toolbar."""
import streamlit as st

from portfolio_app.data.portfolio_loader import (
    _read_uploaded_portfolio,
    get_cli_filename,
)
from portfolio_app.session_keys import (
    PORTFOLIO_RESET_KEYS,
    clear_portfolio_table_widget,
    clear_session_keys,
)


def ensure_uploader_key():
    """Init upload counter and clear legacy popover session keys."""
    for stale in (
        "portfolio_upload_popover",
        "pending_close_upload_popover",
        "_table_tab_for_upload_guard",
    ):
        st.session_state.pop(stale, None)
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


def _dismiss_upload_dialog():
    st.session_state.show_upload_dialog = False


@st.dialog("Upload portfolio CSV", on_dismiss=_dismiss_upload_dialog)
def upload_portfolio_dialog():
    """Modal CSV picker — reads file here so it survives dialog fragment reruns."""
    st.caption("Semicolon-separated CSV (Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency)")
    uploaded_file = st.file_uploader(
        "Choose file",
        type=["csv"],
        key=f"portfolio_upload_{st.session_state.uploader_key}",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        file_key = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
        if st.session_state.get("upload_dismiss_key") != file_key:
            cache_key = (
                f"{st.session_state.uploader_key}:"
                f"{uploaded_file.name}:"
                f"{getattr(uploaded_file, 'size', 0)}"
            )
            df = _read_uploaded_portfolio(uploaded_file)
            st.session_state.uploaded_portfolio_cache_key = cache_key
            st.session_state.uploaded_portfolio_df = df
            st.session_state.uploaded_portfolio_name = uploaded_file.name
            st.session_state.upload_dismiss_key = file_key
            st.session_state.uploader_key += 1
            st.session_state.show_upload_dialog = False
            st.rerun()

    if st.button("Close", use_container_width=True):
        st.session_state.show_upload_dialog = False
        st.rerun()


def render_toolbar_row():
    """
    Render KPI/actions columns and toolbar buttons.

    Returns (kpi_col, uploaded_file, refresh_clicked).
    """
    kpi_col, actions_col = st.columns([6.2, 1.3], vertical_alignment="center")
    refresh_clicked = False

    with actions_col:
        btn_upload, btn_reset, btn_refresh = st.columns(3, gap="small")
        with btn_upload:
            if st.button(
                "📁",
                help="Upload portfolio CSV",
                use_container_width=True,
                key="open_upload_dialog_btn",
            ):
                st.session_state.show_upload_dialog = True
                st.rerun()
        with btn_reset:
            show_reset = (
                st.session_state.get("uploaded_portfolio_df") is not None
                or get_cli_filename() is not None
            )
            if show_reset and st.button(
                "❌",
                help="Clear upload & use default portfolio",
                use_container_width=True,
            ):
                st.session_state.uploader_key += 1
                st.session_state.show_upload_dialog = False
                clear_session_keys(PORTFOLIO_RESET_KEYS)
                clear_portfolio_table_widget()
                st.rerun()
        with btn_refresh:
            refresh_clicked = st.button(
                "🔄",
                help="Refresh prices & analyst data",
                use_container_width=True,
            )

    if st.session_state.get("show_upload_dialog"):
        upload_portfolio_dialog()

    return kpi_col, None, refresh_clicked
