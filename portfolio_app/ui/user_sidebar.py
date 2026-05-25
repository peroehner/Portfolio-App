"""User identity (email) — shown in the app header."""
import streamlit as st

from portfolio_app.services.session_context import (
    get_session_email,
    invalidate_analysis,
    set_session_email,
)


def render_account_in_header():
    """Compact email field in the title row (replaces sidebar account block)."""
    email = st.text_input(
        "Account",
        value=get_session_email(),
        key="header_user_email",
        placeholder="user@local",
        help="Identifies your portfolio (local SQLite, no login yet).",
        label_visibility="collapsed",
    )
    if email and email.strip().lower() != get_session_email():
        set_session_email(email)
        st.session_state.pop("active_portfolio_id", None)
        st.session_state.pop("analysis_portfolio_key", None)
        invalidate_analysis()
        st.rerun()
