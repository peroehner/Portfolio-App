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
from portfolio_app.ui.holdings import clear_holdings_draft, get_editable_holdings_df
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
        activate_portfolio(switched, refetch_metadata=True)
        st.rerun()


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
    parts = ['<div class="kpi-strip kpi-strip-toolbar">']
    for label, amount, pct in items:
        parts.append(
            '<span class="kpi-item">'
            f'<span class="kpi-lbl">{label}</span>'
            f'<span class="kpi-nums"><span class="kpi-val">{amount}</span>{pct}</span>'
            "</span>"
        )
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


def render_portfolio_controls(
    col_sel,
    col_kpis,
    df_port,
    *,
    col_up=None,
    col_new=None,
    col_rename=None,
    col_delete=None,
    col_reload=None,
):
    """Render portfolio picker, optional action buttons, and KPI strip."""
    user = get_session_user()
    svc = get_portfolio_service()
    active = load_active_portfolio()
    portfolios = svc.list_portfolios(user.id)
    options = _portfolio_options(portfolios)
    names = list(options.keys()) if options else []

    display_holdings = get_editable_holdings_df()
    symbol_count = (
        len(display_holdings)
        if display_holdings is not None and not display_holdings.empty
        else 0
    )
    value = st.session_state.get("total_depot_value", 0)
    cost = st.session_state.get("total_depot_cost", 0)
    target = st.session_state.get("total_depot_target", 0)
    div_income = st.session_state.get("total_depot_div_income", 0)

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

    if col_up is not None:
        with col_up:
            export_active = load_active_portfolio()
            export_df = get_editable_holdings_df()
            st.download_button(
                "",
                data=holdings_to_export_csv(export_df),
                file_name=portfolio_export_filename(export_active.name),
                mime="text/csv",
                help="Export portfolio to CSV",
                key=f"portfolio_export_{export_active.portfolio_id}",
                icon=":material/download:",
                disabled=export_df is None,
                use_container_width=True,
                on_click=mark_preserve_table_selection,
            )

    if col_new is not None:
        with col_new:
            if st.button(
                "",
                help="New empty portfolio",
                key="portfolio_new_btn",
                icon=":material/add_circle:",
            ):
                _new_portfolio_dialog()

    if col_rename is not None:
        with col_rename:
            if st.button(
                "",
                help="Rename active portfolio",
                key="portfolio_rename_btn",
                icon=":material/edit:",
            ):
                _rename_portfolio_dialog()

    if col_delete is not None:
        with col_delete:
            if st.button(
                "",
                help="Delete active portfolio",
                key="portfolio_delete_btn",
                icon=":material/delete:",
            ):
                _delete_portfolio_dialog()

    if col_reload is not None:
        with col_reload:
            if st.button(
                "",
                help="Reload from database",
                key="portfolio_reload_btn",
                icon=":material/replay:",
            ):
                clear_holdings_draft(active.portfolio_id)
                invalidate_analysis(refetch_metadata=False)
                st.rerun()

    with col_kpis:
        st.markdown(
            _kpi_strip_html(
                symbol_count=symbol_count,
                value=value,
                cost=cost,
                target=target,
                div_income=div_income,
            ),
            unsafe_allow_html=True,
        )
