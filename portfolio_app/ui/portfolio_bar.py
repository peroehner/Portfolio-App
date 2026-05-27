"""Portfolio selector, actions, and KPIs — single compact row."""
import streamlit as st

from portfolio_app.data.portfolio_loader import holdings_to_export_csv, portfolio_export_filename
from portfolio_app.services.session_context import (
    activate_portfolio,
    get_portfolio_service,
    get_session_user,
    invalidate_analysis,
    load_active_portfolio,
)
from portfolio_app.ui.holdings import clear_holdings_draft
from portfolio_app.ui.components import mark_preserve_table_selection


def _portfolio_options(portfolios) -> dict[str, int]:
    return {p.name: p.id for p in portfolios}


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
) -> str:
    """Single-row KPI bar: label · amount · optional % vs cost (matches toolbar mockup)."""
    value_pct = _kpi_pct_vs_cost_html(value, cost)
    target_pct = _kpi_pct_vs_cost_html(target, cost)
    items = (
        ("Symbols", f"{symbol_count:,}", ""),
        ("Value", f"${value:,.0f}", value_pct),
        ("Cost", f"${cost:,.0f}", ""),
        ("Target", f"${target:,.0f}", target_pct),
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
            activate_portfolio(active, refetch_metadata=True)
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
            activate_portfolio(renamed, refetch_metadata=False)
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
        activate_portfolio(next_active, refetch_metadata=True)
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

    symbol_count = len(df_port) if df_port is not None and not df_port.empty else 0
    value = st.session_state.get("total_depot_value", 0)
    cost = st.session_state.get("total_depot_cost", 0)
    target = st.session_state.get("total_depot_target", 0)

    with col_sel:
        if options:
            try:
                index = names.index(active.name)
            except ValueError:
                index = 0
            picked = st.selectbox(
                "Portfolio",
                names,
                index=index,
                key="portfolio_selector",
                label_visibility="collapsed",
            )
            if picked != active.name:
                switched = svc.load_portfolio(user.id, options[picked])
                if switched:
                    activate_portfolio(switched, refetch_metadata=True)
                    st.rerun()
        else:
            st.caption("—")

    if col_up is not None:
        with col_up:
            export_disabled = df_port is None or df_port.empty
            st.download_button(
                "",
                data=holdings_to_export_csv(df_port),
                file_name=portfolio_export_filename(active.name),
                mime="text/csv",
                help="Export portfolio to CSV",
                key="portfolio_export_btn",
                icon=":material/download:",
                disabled=export_disabled,
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
            ),
            unsafe_allow_html=True,
        )
