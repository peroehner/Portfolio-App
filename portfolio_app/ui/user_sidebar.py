"""User identity (email) — shown in the app header."""
import re

import streamlit as st

from portfolio_app.services.session_context import (
    get_session_email,
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
        st.rerun()


def render_account_in_header():
    """Compact user switcher + manual email entry in the title row."""
    current_email = get_session_email()
    known_users = list_session_users()
    emails = [u.email for u in known_users]
    options = emails + [_MANUAL_ACCOUNT_OPTION]

    default = current_email if current_email in emails else _MANUAL_ACCOUNT_OPTION
    selected = st.selectbox(
        "Account",
        options=options,
        index=options.index(default),
        key="header_user_select",
        help="Switch active user to isolate portfolio sets.",
        label_visibility="collapsed",
    )

    if selected != _MANUAL_ACCOUNT_OPTION:
        _switch_session_user(selected)
        return

    with st.form("manual_user_switch_form", clear_on_submit=False):
        manual = st.text_input(
            "Account email",
            value=current_email if current_email not in emails else "",
            key="header_user_email_manual",
            placeholder="user@example.com",
            help="Enter an email to create/switch user.",
            label_visibility="collapsed",
        )
        apply_switch = st.form_submit_button("Switch")
    if apply_switch:
        _switch_session_user(manual)
