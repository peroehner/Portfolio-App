"""App header with logo and title."""
import os

import streamlit as st

from portfolio_app.config import LOGO_PATH


def render_header():
    header_logo_col, header_title_col = st.columns(
        [0.4, 5.6], vertical_alignment="center"
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
