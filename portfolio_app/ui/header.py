"""App header with logo, title, and account."""
import os

import streamlit as st

from portfolio_app.config import LOGO_PATH
from portfolio_app.ui.user_sidebar import render_account_in_header


def render_header():
    st.markdown('<div class="app-header-row"></div>', unsafe_allow_html=True)
    header_logo_col, header_title_col, header_account_col = st.columns(
        [0.42, 4.55, 1.53], vertical_alignment="center"
    )
    with header_logo_col:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=60)
        else:
            st.caption("Pero")
    with header_title_col:
        st.markdown(
            '<p class="app-title"><b>Pero Portfolio</b> '
            '<span class="app-muted">· Trend Analyzer</span></p>',
            unsafe_allow_html=True,
        )
    with header_account_col:
        st.markdown('<p class="header-account-label">Account</p>', unsafe_allow_html=True)
        render_account_in_header()
