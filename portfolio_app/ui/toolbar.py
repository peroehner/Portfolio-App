"""Upload, reset, and refresh toolbar."""
import os

import streamlit as st

from portfolio_app.data.portfolio_loader import _read_uploaded_portfolio
from portfolio_app.services.session_context import (
    get_portfolio_service,
    get_session_user,
    queue_portfolio_activation,
)
from portfolio_app.ui.holdings import get_editable_holdings_df
from portfolio_app.ui.portfolio_bar import render_portfolio_controls


def ensure_uploader_key():
    """Init upload counter and clear legacy popover session keys."""
    for stale in (
        "portfolio_upload_popover",
        "pending_close_upload_popover",
        "_table_tab_for_upload_guard",
        "upload_pending_df",
        "upload_pending_name",
        "upload_pending_key",
        "upload_replace_confirmed",
    ):
        st.session_state.pop(stale, None)
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


def _clear_upload_pending():
    for key in (
        "upload_pending_df",
        "upload_pending_name",
        "upload_pending_key",
        "upload_replace_confirmed",
    ):
        st.session_state.pop(key, None)


def _dismiss_upload_dialog():
    st.session_state.show_upload_dialog = False
    _clear_upload_pending()


@st.dialog("Load portfolio from CSV", on_dismiss=_dismiss_upload_dialog)
def upload_portfolio_dialog():
    """Import CSV into a named portfolio; confirm when replacing an existing name."""
    st.caption(
        "Semicolon-separated CSV (Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency). "
        "Or build a portfolio manually via **+** and **Add symbol**."
    )
    uploaded_file = st.file_uploader(
        "Choose file",
        type=["csv"],
        key=f"portfolio_upload_{st.session_state.uploader_key}",
    )

    if uploaded_file is not None:
        file_key = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
        if st.session_state.get("upload_pending_key") != file_key:
            try:
                st.session_state.upload_pending_df = _read_uploaded_portfolio(uploaded_file)
                st.session_state.upload_pending_name = os.path.splitext(uploaded_file.name)[0]
                st.session_state.upload_pending_key = file_key
                st.session_state.upload_replace_confirmed = False
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
                _clear_upload_pending()

    pending_df = st.session_state.get("upload_pending_df")
    if pending_df is None:
        if st.button("Close", use_container_width=True):
            _dismiss_upload_dialog()
            st.rerun()
        return

    default_name = st.session_state.get("upload_pending_name", "Imported portfolio")
    portfolio_name = st.text_input("Portfolio name", value=default_name)

    user = get_session_user()
    svc = get_portfolio_service()
    existing = svc.find_portfolio_by_name(user.id, portfolio_name.strip())

    replace_confirmed = st.session_state.get("upload_replace_confirmed", False)
    if existing:
        st.warning(
            f'**"{existing.name}"** already exists ({len(svc.repo.list_positions(existing.id))} positions). '
            "Importing will **permanently replace** all holdings in that portfolio."
        )
        replace_confirmed = st.checkbox(
            "I understand — replace this portfolio",
            value=replace_confirmed,
            key="upload_replace_confirmed",
        )

    import_disabled = bool(existing) and not replace_confirmed
    if st.button("Import CSV", type="primary", disabled=import_disabled, use_container_width=True):
        try:
            imported = svc.import_csv_to_portfolio(
                user.id,
                portfolio_name.strip(),
                pending_df,
                replace_existing=bool(existing),
            )
            queue_portfolio_activation(imported.portfolio_id)
            st.session_state.portfolio_table_view = "ROI"
            st.session_state.uploader_key += 1
            _clear_upload_pending()
            st.session_state.show_upload_dialog = False
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Import failed: {e}")

    if st.button("Close", use_container_width=True):
        _dismiss_upload_dialog()
        st.rerun()


def is_portfolio_more_open() -> bool:
    return bool(st.session_state.get("portfolio_more_open", False))


def render_portfolio_more_button() -> None:
    """Toggle expanded portfolio actions (Add symbol, CSV, etc.)."""
    more_open = is_portfolio_more_open()
    if st.button(
        "",
        help="Hide extra actions" if more_open else "More portfolio actions",
        use_container_width=True,
        key="portfolio_more_btn",
        icon=":material/more_vert:",
        type="primary" if more_open else "secondary",
    ):
        st.session_state.portfolio_more_open = not more_open
        st.rerun()


def render_toolbar_row():
    """
    Render portfolio controls and action buttons in one vertically centered row.

    Returns (placeholder_col, refresh_clicked).
    """
    st.markdown('<div class="portfolio-toolbar-anchor"></div>', unsafe_allow_html=True)

    df_port = get_editable_holdings_df()
    more_open = is_portfolio_more_open()

    if more_open:
        col_sel, col_up, col_new, col_rename, col_delete, col_reload, col_kpis, col_upload, col_refresh = (
            st.columns(
                [1.45, 0.34, 0.34, 0.34, 0.34, 0.34, 4.41, 0.36, 0.36],
                gap="small",
                vertical_alignment="center",
            )
        )
    else:
        col_sel, col_kpis, col_refresh = st.columns(
            [1.85, 6.53, 0.38],
            gap="small",
            vertical_alignment="center",
        )
        col_up = col_new = col_rename = col_delete = col_reload = col_upload = None

    render_portfolio_controls(
        col_sel,
        col_kpis,
        df_port,
        col_up=col_up,
        col_new=col_new,
        col_rename=col_rename,
        col_delete=col_delete,
        col_reload=col_reload,
    )

    if col_upload is not None:
        with col_upload:
            if st.button(
                "",
                help="Load portfolio from CSV file",
                use_container_width=True,
                key="open_upload_dialog_btn",
                icon=":material/upload_file:",
            ):
                st.session_state.show_upload_dialog = True
                st.rerun()

    with col_refresh:
        refresh_clicked = st.button(
            "",
            help="Refresh prices & analyst data",
            use_container_width=True,
            key="toolbar_refresh_btn",
            icon=":material/sync:",
        )

    if st.session_state.get("show_upload_dialog"):
        upload_portfolio_dialog()

    return col_sel, refresh_clicked
