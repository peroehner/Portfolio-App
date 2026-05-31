"""Session-scoped user and portfolio identity."""
import streamlit as st

from portfolio_app.domain.models import ActivePortfolio, User
from portfolio_app.services.portfolio_service import PortfolioService
from portfolio_app.session_keys import (
    PORTFOLIO_RESET_KEYS,
    clear_portfolio_table_widget,
    clear_session_keys,
)

_DEFAULT_EMAIL = "user@local"


def get_portfolio_service() -> PortfolioService:
    if "portfolio_service" not in st.session_state:
        st.session_state.portfolio_service = PortfolioService()
    return st.session_state.portfolio_service


def get_session_email() -> str:
    return st.session_state.get("user_email", _DEFAULT_EMAIL).strip().lower()


def set_session_email(email: str):
    st.session_state.user_email = email.strip().lower()


def get_session_user() -> User:
    return get_portfolio_service().get_or_create_user(get_session_email())

def list_session_users() -> list[User]:
    return get_portfolio_service().list_users()


def switch_session_user(email: str) -> bool:
    """
    Switch active session user and reset portfolio-scoped UI state.

    Returns True only when a switch was performed.
    """
    normalized = email.strip().lower()
    if not normalized or normalized == get_session_email():
        return False

    # Set identity first so downstream loads resolve the target user's data.
    set_session_email(normalized)

    # Clear user-bound active selection and table/widget state.
    st.session_state.pop("active_portfolio_id", None)
    st.session_state.pop("analysis_portfolio_key", None)
    st.session_state.pop("portfolio_selector", None)
    st.session_state.pop("portfolio_table_roi_editor", None)
    st.session_state.pop("portfolio_more_open", None)
    st.session_state.pop("show_upload_dialog", None)
    clear_session_keys(PORTFOLIO_RESET_KEYS)
    clear_portfolio_table_widget()
    invalidate_analysis(refetch_metadata=True)
    return True


def get_active_portfolio_id() -> int | None:
    return st.session_state.get("active_portfolio_id")


def set_active_portfolio_id(portfolio_id: int):
    st.session_state.active_portfolio_id = portfolio_id


def get_portfolio_data_version() -> int:
    return int(st.session_state.get("portfolio_data_version", 0))


def bump_portfolio_data_version():
    st.session_state.portfolio_data_version = get_portfolio_data_version() + 1


def get_analysis_portfolio_key() -> str | None:
    return st.session_state.get("analysis_portfolio_key")


def set_analysis_portfolio_key(key: str):
    st.session_state.analysis_portfolio_key = key


def invalidate_analysis(*, refetch_metadata: bool = True):
    """Force portfolio analysis reload on next render."""
    st.session_state.pop("analysis_portfolio_key", None)
    st.session_state.pop("current_loaded_name", None)
    st.session_state["_pending_refetch_metadata"] = refetch_metadata
    bump_portfolio_data_version()


def consume_refetch_metadata_flag() -> bool:
    """One-shot flag: whether the pending reload should restart analyst fetch."""
    return st.session_state.pop("_pending_refetch_metadata", True)


def _reset_portfolio_display_state() -> None:
    """Clear analysis/KPI session data so a portfolio switch never flashes stale rows."""
    st.session_state.all_results = []
    st.session_state.total_depot_value = 0.0
    st.session_state.total_depot_cost = 0.0
    st.session_state.total_depot_target = 0.0
    st.session_state.total_depot_div_income = 0.0
    st.session_state.portfolio_symbols = tuple()
    st.session_state.ticker_liste = []
    clear_portfolio_table_widget()


def queue_portfolio_activation(portfolio_id: int, *, refetch_metadata: bool = True) -> None:
    """Apply portfolio switch on the next full app run (required after st.dialog actions)."""
    st.session_state["_pending_portfolio_id"] = int(portfolio_id)
    st.session_state["_pending_portfolio_refetch"] = refetch_metadata


def consume_pending_portfolio_activation() -> bool:
    """Switch to a portfolio queued from a dialog; returns True when applied."""
    pending_id = st.session_state.pop("_pending_portfolio_id", None)
    if pending_id is None:
        return False
    refetch = st.session_state.pop("_pending_portfolio_refetch", True)
    user = get_session_user()
    active = get_portfolio_service().load_portfolio(user.id, int(pending_id))
    if not active:
        return False
    activate_portfolio(active, refetch_metadata=refetch)
    return True


def activate_portfolio(active: ActivePortfolio, *, refetch_metadata: bool = True):
    """Switch session to a portfolio and invalidate analysis."""
    previous_id = get_active_portfolio_id()
    set_active_portfolio_id(active.portfolio_id)
    get_portfolio_service().remember_last_portfolio(active.user_id, active.portfolio_id)
    st.session_state["portfolio_selector"] = active.name
    st.session_state["_force_portfolio_selector_sync"] = active.name
    if previous_id and previous_id != active.portfolio_id:
        st.session_state.pop(f"holdings_draft_{previous_id}", None)
    st.session_state.pop(f"holdings_draft_{active.portfolio_id}", None)
    st.session_state.pop("portfolio_table", None)
    st.session_state.pop("portfolio_table_roi_editor", None)
    st.session_state.pop("selected_symbol", None)
    st.session_state.pop("selected_symbols", None)
    st.session_state.pop("table_sel_rows", None)
    st.session_state.pop("ticker_index", None)
    st.session_state.pop("ta_nav_index", None)
    st.session_state.pop("ta_chart_symbol", None)
    st.session_state.pop("_ta_selection_key", None)
    st.session_state.pop("_ta_nav_symbols", None)
    _reset_portfolio_display_state()
    invalidate_analysis(refetch_metadata=refetch_metadata)


def load_active_portfolio() -> ActivePortfolio:
    svc = get_portfolio_service()
    user = get_session_user()
    portfolio_id = get_active_portfolio_id()
    if portfolio_id:
        active = svc.load_portfolio(user.id, portfolio_id)
        if active:
            return active
    active = svc.bootstrap_user_portfolio(user)
    set_active_portfolio_id(active.portfolio_id)
    return active
