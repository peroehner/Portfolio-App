"""Streamlit application entry — layout and page flow."""
import streamlit as st

from portfolio_app.config import PAGE_ICON
from portfolio_app.services.session_context import (
    consume_pending_portfolio_activation,
    load_active_portfolio,
)
from portfolio_app.ui.detail_panel import render_detail_panel
from portfolio_app.ui.header import render_header
from portfolio_app.ui.holdings import get_editable_holdings_df
from portfolio_app.ui.portfolio_page import render_portfolio_page
from portfolio_app.ui.sections import render_section_header
from portfolio_app.ui.theme import inject_app_styles, inject_desktop_icons
from portfolio_app.ui.toolbar import ensure_uploader_key, render_toolbar_row


def run():
    st.set_page_config(
        page_title="Portfolio Compass",
        page_icon=PAGE_ICON,
        layout="wide",
    )
    inject_desktop_icons()
    inject_app_styles()

    consume_pending_portfolio_activation()

    render_header()

    with st.container(border=True):
        render_section_header(
            title="Portfolio Screener",
            subtitle="Compose holdings & targets · Show trends returns & valuations",
            panel_class="section-panel-portfolio",
            account_in_corner=True,
        )
        ensure_uploader_key()
        _, refresh_clicked = render_toolbar_row()
        active = load_active_portfolio()
        render_portfolio_page(get_editable_holdings_df(), active.name, refresh_clicked)

    with st.container(border=True):
        render_section_header(
            title="Technical Analysis",
            subtitle="Time bound, chart, trends & Fibonacci · Analyse selected symbol · Export analytics for multi-selection",
            panel_class="section-panel-ta",
        )
        render_detail_panel()
