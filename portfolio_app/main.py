"""Streamlit application entry — layout and page flow."""
import streamlit as st

from portfolio_app.config import PAGE_ICON
from portfolio_app.services.session_context import load_active_portfolio
from portfolio_app.ui.components import inject_table_click_modifiers
from portfolio_app.ui.detail_panel import render_detail_panel
from portfolio_app.ui.header import render_header
from portfolio_app.ui.portfolio_page import render_portfolio_page
from portfolio_app.ui.theme import inject_app_styles, inject_desktop_icons
from portfolio_app.ui.toolbar import ensure_uploader_key, render_toolbar_row
from portfolio_app.ui.user_sidebar import render_user_sidebar


def run():
    st.set_page_config(
        page_title="Pero Portfolio & Trend Analyzer",
        page_icon=PAGE_ICON,
        layout="wide",
    )
    inject_desktop_icons()
    inject_app_styles()
    inject_table_click_modifiers()

    render_user_sidebar()
    render_header()
    ensure_uploader_key()
    kpi_col, refresh_clicked = render_toolbar_row()

    active = load_active_portfolio()
    render_portfolio_page(kpi_col, active.holdings_df, active.name, refresh_clicked)
    render_detail_panel()
