"""Upload, reset, and refresh toolbar."""
import streamlit as st

from portfolio_app.data.portfolio_loader import _read_portfolio_csv
from portfolio_app.services.import_engine import ImportMode
from portfolio_app.services.session_context import (
    get_portfolio_service,
    load_active_portfolio,
    queue_portfolio_activation,
)
from portfolio_app.ui.holdings import clear_holdings_draft, get_editable_holdings_df
from portfolio_app.session_keys import notify_portfolio_toolbar_layout_changed
from portfolio_app.ui.portfolio_bar import (
    render_portfolio_controls,
    render_portfolio_toolbar_actions_row,
)


def ensure_uploader_key():
    """Init upload counter and clear legacy import session keys."""
    for stale in (
        "portfolio_upload_popover",
        "pending_close_upload_popover",
        "_table_tab_for_upload_guard",
        "upload_pending_df",
        "upload_pending_name",
        "upload_pending_valid_df",
        "upload_replace_confirmed",
        "upload_empty_replace_confirmed",
        "uploaded_portfolio_df",
        "uploaded_portfolio_name",
        "uploaded_portfolio_cache_key",
    ):
        st.session_state.pop(stale, None)
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


def _clear_upload_pending():
    for key in (
        "upload_pending_raw_df",
        "upload_pending_key",
        "upload_empty_replace_confirmed",
    ):
        st.session_state.pop(key, None)


def _dismiss_upload_dialog():
    st.session_state.show_upload_dialog = False
    _clear_upload_pending()


def _format_symbol_list(symbols: list[str], limit: int = 12) -> str:
    if not symbols:
        return "—"
    if len(symbols) <= limit:
        return ", ".join(symbols)
    head = ", ".join(symbols[:limit])
    return f"{head}, … (+{len(symbols) - limit} more)"


def _render_import_preview(preview) -> None:
    mode_label = "Replace" if preview.mode == ImportMode.REPLACE else "Merge"
    st.markdown(f"**Preview ({mode_label})** — **{preview.result_symbol_count}** symbol(s) after import")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Add", len(preview.added))
    c2.metric("Update", len(preview.updated))
    c3.metric("Remove", len(preview.removed))
    c4.metric("Unchanged", len(preview.unchanged))

    if preview.added:
        st.caption(f"Add: {_format_symbol_list(preview.added)}")
    if preview.updated:
        st.caption(f"Update: {_format_symbol_list(preview.updated)}")
    if preview.removed:
        st.caption(f"Remove: {_format_symbol_list(preview.removed)}")
    if preview.warnings:
        for warning in preview.warnings[:5]:
            st.warning(warning)
        if len(preview.warnings) > 5:
            st.caption(f"…and {len(preview.warnings) - 5} more warning(s).")
    if preview.rejected:
        st.error(f"{len(preview.rejected)} row(s) rejected (skipped):")
        for issue in preview.rejected[:8]:
            sym = issue.symbol or "?"
            st.caption(f"Row {issue.row_number} ({sym}): {issue.reason}")
        if len(preview.rejected) > 8:
            st.caption(f"…and {len(preview.rejected) - 8} more.")


@st.dialog("Import CSV into current portfolio", on_dismiss=_dismiss_upload_dialog)
def upload_portfolio_dialog():
    """Import CSV into the active portfolio: replace all holdings or merge by symbol."""
    active = load_active_portfolio()
    st.caption(
        f"Target: **{active.name}** · semicolon-separated CSV "
        "(Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency)."
    )
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=["csv"],
        key=f"portfolio_upload_{st.session_state.uploader_key}",
    )

    if uploaded_file is not None:
        file_key = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
        if st.session_state.get("upload_pending_key") != file_key:
            try:
                if hasattr(uploaded_file, "seek"):
                    uploaded_file.seek(0)
                st.session_state.upload_pending_raw_df = _read_portfolio_csv(uploaded_file)
                st.session_state.upload_pending_key = file_key
                st.session_state.upload_empty_replace_confirmed = False
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
                _clear_upload_pending()

    raw_df = st.session_state.get("upload_pending_raw_df")
    if raw_df is None:
        if st.button("Close", use_container_width=True):
            _dismiss_upload_dialog()
            st.rerun()
        return

    mode_label = st.radio(
        "Import mode",
        options=["Replace current portfolio", "Merge into current portfolio"],
        horizontal=True,
        help=(
            "**Replace** — holdings become exactly what is in the CSV; symbols not in the file are removed. "
            "**Merge** — combine lots by symbol; symbols only in the portfolio are kept."
        ),
    )
    mode = (
        ImportMode.REPLACE
        if mode_label.startswith("Replace")
        else ImportMode.MERGE
    )

    svc = get_portfolio_service()
    try:
        preview = svc.preview_csv_import(active.portfolio_id, raw_df, mode)
    except ValueError as e:
        st.error(str(e))
        if st.button("Close", use_container_width=True):
            _dismiss_upload_dialog()
            st.rerun()
        return

    _render_import_preview(preview)

    empty_replace = (
        mode == ImportMode.REPLACE
        and preview.result_symbol_count == 0
        and not preview.rejected
    )
    empty_confirmed = st.session_state.get("upload_empty_replace_confirmed", False)
    if empty_replace:
        st.warning("The CSV has no valid rows. Replace will **clear all holdings** in this portfolio.")
        empty_confirmed = st.checkbox(
            "I understand — clear all holdings",
            value=empty_confirmed,
            key="upload_empty_replace_confirmed",
        )
    elif mode == ImportMode.REPLACE and preview.removed:
        st.warning(
            f"Replace will remove **{len(preview.removed)}** symbol(s) not present in the CSV."
        )

    import_disabled = not preview.can_apply or (empty_replace and not empty_confirmed)
    if st.button(
        "Apply import",
        type="primary",
        disabled=import_disabled,
        use_container_width=True,
    ):
        try:
            updated, applied = svc.import_csv_into_portfolio(
                active.portfolio_id,
                raw_df,
                mode,
                allow_empty_replace=empty_confirmed,
            )
            clear_holdings_draft(active.portfolio_id)
            queue_portfolio_activation(updated.portfolio_id, refetch_metadata=False)
            st.session_state.portfolio_table_view = "ROI"
            st.session_state.uploader_key += 1
            _clear_upload_pending()
            st.session_state.show_upload_dialog = False
            mode_word = "replaced" if mode == ImportMode.REPLACE else "merged"
            st.toast(
                f"Imported {applied.preview.result_symbol_count} symbol(s) ({mode_word}). "
                "Refresh financial data when ready.",
                icon="✅",
            )
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
    """Toggle expanded toolbar: Portfolio (DB) and File (CSV) action groups."""
    more_open = is_portfolio_more_open()
    active = load_active_portfolio()
    if more_open:
        help_text = (
            f'Hide portfolio and file actions for “{active.name}”'
        )
    else:
        help_text = (
            f'New, save as, rename, delete, reload, import, and export for “{active.name}”'
        )
    if st.button(
        "",
        help=help_text,
        use_container_width=True,
        key="portfolio_more_btn",
        icon=":material/more_vert:",
        type="primary" if more_open else "secondary",
    ):
        st.session_state.portfolio_more_open = not more_open
        notify_portfolio_toolbar_layout_changed()
        st.rerun()


def _open_import_dialog() -> None:
    st.session_state.show_upload_dialog = True
    st.rerun()


def render_toolbar_row():
    """
    Render portfolio controls and action buttons in one vertically centered row.

    Returns (placeholder_col, refresh_clicked).
    """
    st.markdown('<div class="portfolio-toolbar-anchor"></div>', unsafe_allow_html=True)

    df_port = get_editable_holdings_df()
    more_open = is_portfolio_more_open()
    active = load_active_portfolio()

    col_sel, col_kpis, col_refresh = st.columns(
        [1.85, 6.53, 0.38],
        gap="small",
        vertical_alignment="center",
    )

    render_portfolio_controls(
        col_sel,
        col_kpis,
        df_port,
    )

    with col_refresh:
        refresh_clicked = st.button(
            "",
            help=f'Refresh market data for “{active.name}”',
            use_container_width=True,
            key="toolbar_refresh_btn",
            icon=":material/sync:",
        )

    if more_open:
        st.markdown(
            '<div class="portfolio-toolbar-actions-anchor"></div>',
            unsafe_allow_html=True,
        )
        render_portfolio_toolbar_actions_row(on_import_click=_open_import_dialog)

    if st.session_state.get("show_upload_dialog"):
        upload_portfolio_dialog()

    return col_sel, refresh_clicked
