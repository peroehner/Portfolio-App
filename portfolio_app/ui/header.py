"""App header with logo and title."""
import os

import streamlit as st

from portfolio_app.config import LOGO_PATH


def render_header():
    st.markdown('<div class="app-header-row"></div>', unsafe_allow_html=True)
    header_logo_col, header_title_col = st.columns([0.42, 5.58], vertical_alignment="center")
    with header_logo_col:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=60)
        else:
            st.caption("Pero")
    with header_title_col:
        st.markdown(
            '<div class="app-headings">'
            '<p class="app-title">Portfolio Compass</p>'
            '<p class="app-subtitle section-subtitle">'
            "Choose portfolio · Select symbol(s) · Analyse chart"
            "</p></div>",
            unsafe_allow_html=True,
        )
