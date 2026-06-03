"""User identity (email) — account selector in the portfolio panel."""
import streamlit as st

from portfolio_app.domain.user_identity import DEFAULT_LOCAL_EMAIL
from portfolio_app.services.session_context import (
    get_session_email,
    get_session_user,
    list_session_users,
    switch_session_user,
)
from portfolio_app.services.user_identity_service import get_user_identity_service

_MANUAL_ACCOUNT_OPTION = "Use another email…"
_PENDING_USER_SWITCH_KEY = "_pending_user_switch_email"


def _queue_user_switch(email: str) -> None:
    """Defer switch to the next run so widget keys are never mutated after render."""
    st.session_state[_PENDING_USER_SWITCH_KEY] = email
    st.rerun()


def _apply_pending_user_switch() -> None:
    """Run before header widgets — Streamlit forbids mutating widget keys after draw."""
    pending = st.session_state.pop(_PENDING_USER_SWITCH_KEY, None)
    if not pending:
        return
    identity = get_user_identity_service()
    ok, err = identity.validate_email(pending)
    if not ok:
        st.warning(err)
        return
    normalized = identity.normalize_email(pending)
    if normalized == get_session_email():
        return
    if switch_session_user(normalized):
        st.session_state.pop("_account_picked_manual", None)
        st.session_state["_force_header_user_select"] = normalized
        st.rerun()


def _account_options(current_email: str) -> list[str]:
    """Known users plus the active account (always listed) and manual entry."""
    get_session_user()
    emails = [u.email for u in list_session_users()]
    if current_email and current_email not in emails:
        emails.insert(0, current_email)
    elif current_email in emails:
        emails = [current_email] + [e for e in emails if e != current_email]
    return emails + [_MANUAL_ACCOUNT_OPTION]


def _on_account_select() -> None:
    if st.session_state.get("header_user_select") == _MANUAL_ACCOUNT_OPTION:
        st.session_state["_account_picked_manual"] = True
    else:
        st.session_state.pop("_account_picked_manual", None)


def _render_identity_status_hint() -> None:
    """Future verification UX — hidden while all local users are active."""
    user = get_session_user()
    identity = get_user_identity_service()
    if identity.is_verification_required(user):
        st.caption("Email verification pending — portfolios remain available for now.")


def render_account_in_header():
    """Compact user switcher; manual email entry only for 'Use another email…'."""
    _apply_pending_user_switch()

    forced = st.session_state.pop("_force_header_user_select", None)
    if forced is not None:
        st.session_state["header_user_select"] = forced

    current_email = get_session_email()
    options = _account_options(current_email)

    if st.session_state.get("header_user_select") not in options:
        st.session_state.header_user_select = current_email
    elif (
        st.session_state.get("header_user_select") == _MANUAL_ACCOUNT_OPTION
        and not st.session_state.get("_account_picked_manual")
    ):
        st.session_state.header_user_select = current_email

    selected = st.selectbox(
        "Account",
        options=options,
        key="header_user_select",
        help=(
            "Switch active user to isolate portfolio sets. "
            f"Each email maps to one account (default: {DEFAULT_LOCAL_EMAIL})."
        ),
        label_visibility="collapsed",
        on_change=_on_account_select,
    )

    _render_identity_status_hint()

    if selected == _MANUAL_ACCOUNT_OPTION:
        with st.form("manual_user_switch_form", clear_on_submit=False):
            manual = st.text_input(
                "Account email",
                value="",
                key="header_user_email_manual",
                placeholder="user@example.com",
                help="Enter an email to create or switch user.",
                label_visibility="collapsed",
            )
            apply_switch = st.form_submit_button("Switch")
        if apply_switch:
            _queue_user_switch(manual)
        return

    if selected != current_email:
        _queue_user_switch(selected)
