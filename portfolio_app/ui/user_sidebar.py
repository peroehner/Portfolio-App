"""User identity (email) for single-user Phase 1."""
import streamlit as st

from portfolio_app.services.session_context import (
    get_session_email,
    get_session_user,
    invalidate_analysis,
    set_session_email,
)


def render_user_sidebar():
    with st.sidebar:
        st.subheader("Account")
        email = st.text_input(
            "Email",
            value=get_session_email(),
            key="sidebar_user_email",
            help="Identifies your portfolio (local SQLite, no login yet).",
        )
        if email and email.strip().lower() != get_session_email():
            set_session_email(email)
            st.session_state.pop("active_portfolio_id", None)
            invalidate_analysis()
            st.rerun()

        user = get_session_user()
        st.caption(f"User id: {user.id}")
