"""Portfolio selector, actions, and KPIs — single compact row."""
import streamlit as st

from portfolio_app.data.portfolio_loader import holdings_to_export_csv, portfolio_export_filename
from portfolio_app.services.session_context import (
    activate_portfolio,
    get_portfolio_service,
    get_session_user,
    invalidate_analysis,
    load_active_portfolio,
    queue_portfolio_activation,
)
from portfolio_app.ui.holdings import (
    clear_holdings_draft,
    get_editable_holdings_df,
    get_holdings_for_analysis_df,
    has_holdings_draft,
    parse_holdings_editor_df,
    validate_holdings_symbols,
)
from portfolio_app.ui.components import mark_preserve_table_selection


def _portfolio_options(portfolios) -> dict[str, int]:
    return {p.name: p.id for p in portfolios}


def _on_portfolio_selected() -> None:
    """Load the portfolio the user picked in the selector."""
    picked = st.session_state.get("portfolio_selector")
    if not picked:
        return

    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    if picked == active.name:
        return

    options = _portfolio_options(svc.list_portfolios(user.id))
    if picked not in options:
        return

    switched = svc.load_portfolio(user.id, options[picked])
    if switched:
        activate_portfolio(switched, refetch_metadata=False)


def _kpi_pct_vs_cost_html(amount: float, cost: float) -> str:
    """Return (+13%) / (-5%) markup vs cost basis, or empty if cost is zero."""
    if not cost or cost <= 0:
        return ""
    pct = (amount - cost) / cost * 100.0
    sign = "+" if pct >= 0 else ""
    trend = "up" if pct >= 0 else "down"
    return f'<span class="kpi-pct kpi-pct-{trend}">({sign}{pct:.0f}%)</span>'


def _kpi_strip_html(
    *,
    symbol_count: int,
    value: float,
    cost: float,
    target: float,
    div_income: float,
    last_sync_label: str,
) -> str:
    """Single-row KPI bar: label · amount · optional % vs cost (matches toolbar mockup)."""
    value_pct = _kpi_pct_vs_cost_html(value, cost)
    target_pct = _kpi_pct_vs_cost_html(target, cost)
    items = (
        ("Symbols", f"{symbol_count:,}", ""),
        ("Value", f"${value:,.0f}", value_pct),
        ("Cost", f"${cost:,.0f}", ""),
        ("Target", f"${target:,.0f}", target_pct),
        ("Div Income", f"${div_income:,.0f}", ""),
    )
    sync_text = (
        f"Last sync: {last_sync_label}"
        if last_sync_label and last_sync_label != "—"
        else "Last sync: never"
    )
    parts = ['<div class="kpi-toolbar-slot">', '<div class="kpi-strip kpi-strip-toolbar">']
    for label, amount, pct in items:
        parts.append(
            '<span class="kpi-item">'
            f'<span class="kpi-lbl">{label}</span>'
            f'<span class="kpi-nums"><span class="kpi-val">{amount}</span>{pct}</span>'
            "</span>"
        )
    parts.append("</div>")
    parts.append(f'<div class="kpi-sync-footnote" title="{sync_text}">{sync_text}</div>')
    parts.append("</div>")
    return "".join(parts)


@st.dialog("New portfolio")
def _new_portfolio_dialog():
    name = st.text_input("Portfolio name", placeholder="My growth portfolio")
    st.caption("Start empty — add symbols in ROI view, then Save portfolio.")
    if st.button("Create", type="primary", use_container_width=True):
        if not name.strip():
            st.warning("Enter a portfolio name.")
            return
        try:
            user = get_session_user()
            svc = get_portfolio_service()
            active = svc.create_empty_portfolio(user.id, name.strip())
            queue_portfolio_activation(active.portfolio_id)
            st.session_state.portfolio_table_view = "ROI"
            st.session_state.portfolio_more_open = True
            from portfolio_app.session_keys import notify_portfolio_toolbar_layout_changed

            notify_portfolio_toolbar_layout_changed()
            st.rerun()
        except ValueError as e:
            st.error(str(e))


@st.dialog("Rename portfolio")
def _rename_portfolio_dialog():
    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    name = st.text_input("New portfolio name", value=active.name)
    if st.button("Save name", type="primary", use_container_width=True):
        if not name.strip():
            st.warning("Enter a portfolio name.")
            return
        try:
            renamed = svc.rename_portfolio(user.id, active.portfolio_id, name.strip())
            queue_portfolio_activation(renamed.portfolio_id, refetch_metadata=False)
            st.success("Portfolio renamed.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def _suggest_save_as_name(user_id: int, source_name: str) -> str:
    svc = get_portfolio_service()
    existing = {p.name for p in svc.list_portfolios(user_id)}
    candidate = f"{source_name} copy"
    if candidate not in existing:
        return candidate
    n = 2
    while True:
        candidate = f"{source_name} copy {n}"
        if candidate not in existing:
            return candidate
        n += 1


@st.dialog("Save portfolio as…")
def _save_as_portfolio_dialog():
    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    st.caption(
        f'Create a new portfolio from **"{active.name}"** — holdings, snapshots, and last sync are copied.'
    )
    name = st.text_input(
        "New portfolio name",
        value=_suggest_save_as_name(user.id, active.name),
    )
    has_draft = has_holdings_draft(active.portfolio_id)
    include_unsaved = True
    if has_draft:
        include_unsaved = st.checkbox(
            "Include unsaved editor changes",
            value=True,
            help=(
                f'Use the editor draft instead of last-saved holdings for "{active.name}".'
            ),
        )
    if st.button("Create portfolio", type="primary", use_container_width=True):
        if not name.strip():
            st.warning("Enter a portfolio name.")
            return
        try:
            if include_unsaved and has_draft:
                holdings = parse_holdings_editor_df(get_editable_holdings_df())
            else:
                saved = svc.load_portfolio(user.id, active.portfolio_id)
                if not saved:
                    st.error("Portfolio not found.")
                    return
                holdings = saved.holdings_df.copy()
            if holdings.empty:
                st.warning("Nothing to copy — add at least one holding.")
                return
            with st.spinner("Validating symbols…"):
                validate_holdings_symbols(holdings)
            new_active = svc.save_as_portfolio(
                user.id,
                active.portfolio_id,
                name.strip(),
                holdings,
            )
            queue_portfolio_activation(new_active.portfolio_id, refetch_metadata=False)
            st.session_state.portfolio_more_open = True
            from portfolio_app.session_keys import notify_portfolio_toolbar_layout_changed

            notify_portfolio_toolbar_layout_changed()
            st.toast(f'Saved as "{new_active.name}".', icon="✅")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


@st.dialog("Delete portfolio")
def _delete_portfolio_dialog():
    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    portfolios = svc.list_portfolios(user.id)
    st.warning(
        f'You are about to permanently delete **"{active.name}"** '
        f"with {len(active.holdings_df)} position(s)."
    )
    if len(portfolios) <= 1:
        st.info("You have one portfolio left. A Demo Portfolio will be created automatically.")
    confirm = st.checkbox("I understand — delete this portfolio permanently")
    if st.button("Delete portfolio", type="primary", use_container_width=True, disabled=not confirm):
        next_active = svc.delete_portfolio(user.id, active.portfolio_id)
        queue_portfolio_activation(next_active.portfolio_id)
        st.success("Portfolio deleted.")
        st.rerun()


def render_portfolio_db_actions(col_db, *, active_name: str, portfolio_id: int) -> None:
    """Portfolio (DB) actions — label and icons left-aligned, tight icon cluster."""
    with col_db:
        col_lbl, col_icons = st.columns(
            [0.95, 2.5],
            gap="small",
            vertical_alignment="center",
        )
        with col_lbl:
            st.markdown(
                '<span class="portfolio-toolbar-group-label">Portfolio</span>',
                unsafe_allow_html=True,
            )
        c_new, c_save_as, c_rename, c_delete, c_reload = col_icons.columns(
            5,
            gap="small",
        )
        with c_new:
            if st.button(
                "",
                help=f"Create a new empty portfolio (current: “{active_name}”)",
                key="portfolio_new_btn",
                icon=":material/add_circle:",
            ):
                _new_portfolio_dialog()
        with c_save_as:
            if st.button(
                "",
                help=f'Save a copy of “{active_name}” as a new portfolio',
                key="portfolio_save_as_btn",
                icon=":material/save_as:",
            ):
                _save_as_portfolio_dialog()
        with c_rename:
            if st.button(
                "",
                help=f'Rename “{active_name}”',
                key="portfolio_rename_btn",
                icon=":material/edit:",
            ):
                _rename_portfolio_dialog()
        with c_delete:
            if st.button(
                "",
                help=f'Permanently delete “{active_name}”',
                key="portfolio_delete_btn",
                icon=":material/delete:",
            ):
                _delete_portfolio_dialog()
        with c_reload:
            if st.button(
                "",
                help=f'Reload “{active_name}” from database (discard unsaved edits)',
                key="portfolio_reload_btn",
                icon=":material/replay:",
            ):
                clear_holdings_draft(portfolio_id)
                invalidate_analysis(refetch_metadata=False)
                st.rerun()


def render_portfolio_file_actions(
    col_file,
    *,
    active_name: str,
    portfolio_id: int,
    on_import_click,
) -> None:
    """File (CSV) actions: import and export — distinct toolbar styling."""
    export_active = load_active_portfolio()
    export_df = export_active.holdings_df
    with col_file:
        col_lbl, col_icons = st.columns(
            [0.95, 1.0],
            gap="small",
            vertical_alignment="center",
        )
        with col_lbl:
            st.markdown(
                '<span class="portfolio-toolbar-group-label">File (CSV)</span>',
                unsafe_allow_html=True,
            )
        c_import, c_export = col_icons.columns(2, gap="small")
        with c_import:
            if st.button(
                "",
                help=f'Import CSV into “{active_name}” (replace or merge holdings)',
                key="open_upload_dialog_btn",
                icon=":material/upload_file:",
            ):
                on_import_click()
        with c_export:
            st.download_button(
                "",
                data=holdings_to_export_csv(export_df),
                file_name=portfolio_export_filename(export_active.name),
                mime="text/csv",
                help=f'Export “{active_name}” to CSV backup',
                key=f"portfolio_export_{portfolio_id}",
                icon=":material/download:",
                disabled=export_df is None,
                on_click=mark_preserve_table_selection,
            )


def render_portfolio_controls(
    col_sel,
    col_kpis,
    df_port,
    *,
    col_db=None,
    col_file=None,
    on_import_click=None,
):
    """Render portfolio picker, optional grouped actions, and KPI strip."""
    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    portfolios = svc.list_portfolios(user.id)
    options = _portfolio_options(portfolios)
    names = list(options.keys()) if options else []

    display_holdings = get_holdings_for_analysis_df()
    symbol_count = (
        len(display_holdings)
        if display_holdings is not None and not display_holdings.empty
        else 0
    )
    value = st.session_state.get("total_depot_value", 0)
    cost = st.session_state.get("total_depot_cost", 0)
    target = st.session_state.get("total_depot_target", 0)
    div_income = st.session_state.get("total_depot_div_income", 0)
    last_sync_label = st.session_state.get("portfolio_last_sync_label", "—")

    with col_sel:
        if options:
            force = st.session_state.pop("_force_portfolio_selector_sync", None)
            if force and force in names:
                st.session_state["portfolio_selector"] = force
            elif active.name in names and st.session_state.get("portfolio_selector") not in names:
                st.session_state["portfolio_selector"] = active.name

            try:
                index = names.index(active.name)
            except ValueError:
                index = 0
            st.selectbox(
                "Portfolio",
                names,
                index=index,
                key="portfolio_selector",
                label_visibility="collapsed",
                on_change=_on_portfolio_selected,
            )
        else:
            st.caption("—")

    if col_db is not None:
        render_portfolio_db_actions(
            col_db,
            active_name=active.name,
            portfolio_id=active.portfolio_id,
        )

    if col_file is not None and on_import_click is not None:
        render_portfolio_file_actions(
            col_file,
            active_name=active.name,
            portfolio_id=active.portfolio_id,
            on_import_click=on_import_click,
        )

    with col_kpis:
        st.html(
            _kpi_strip_html(
                symbol_count=symbol_count,
                value=value,
                cost=cost,
                target=target,
                div_income=div_income,
                last_sync_label=last_sync_label,
            ),
            unsafe_allow_javascript=False,
        )


def render_portfolio_toolbar_actions_row(*, on_import_click) -> None:
    """Second toolbar row: Portfolio left, File (CSV) right when ⋮ is expanded."""
    from portfolio_app.ui.history_controls import render_history_months_controls

    active = load_active_portfolio()
    col_db, col_spacer, col_file = st.columns(
        [2, 5, 2],
        gap="small",
        vertical_alignment="center",
    )
    render_portfolio_db_actions(
        col_db,
        active_name=active.name,
        portfolio_id=active.portfolio_id,
    )
    loaded_hist = st.session_state.get("_ta_detail_hist_preview")
    render_history_months_controls(col_spacer, hist=loaded_hist)
    render_portfolio_file_actions(
        col_file,
        active_name=active.name,
        portfolio_id=active.portfolio_id,
        on_import_click=on_import_click,
    )
