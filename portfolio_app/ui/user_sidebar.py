"""User identity (email) — account selector in the portfolio panel."""
import re

import streamlit as st

from portfolio_app.services.session_context import (
    get_session_email,
    get_session_user,
    list_session_users,
    switch_session_user,
)

_MANUAL_ACCOUNT_OPTION = "Use another email…"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def _switch_session_user(email: str):
    normalized = email.strip().lower()
    if not normalized:
        return
    if normalized == get_session_email():
        return
    if not _EMAIL_RE.match(normalized):
        st.warning("Enter a valid email (e.g. name@example.com).")
        return
    if switch_session_user(normalized):
        st.session_state["header_user_select"] = normalized
        st.session_state.pop("_account_picked_manual", None)
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


def render_account_in_header():
    """Compact user switcher; manual email entry only for 'Use another email…'."""
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
        help="Switch active user to isolate portfolio sets.",
        label_visibility="collapsed",
        on_change=_on_account_select,
    )

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
            _switch_session_user(manual)
        return

    if selected != current_email:
        _switch_session_user(selected)
