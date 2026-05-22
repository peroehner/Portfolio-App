"""Streamlit application entry — layout and page flow."""
import streamlit as st

from portfolio_app.config import PAGE_ICON
from portfolio_app.data.portfolio_loader import load_portfolio
from portfolio_app.ui.components import inject_table_click_modifiers
from portfolio_app.ui.detail_panel import render_detail_panel
from portfolio_app.ui.header import render_header
from portfolio_app.ui.portfolio_page import render_portfolio_page
from portfolio_app.ui.theme import inject_app_styles, inject_desktop_icons
from portfolio_app.ui.toolbar import ensure_uploader_key, render_toolbar_row


def run():
    st.set_page_config(
        page_title="Pero Portfolio & Trend Analyzer",
        page_icon=PAGE_ICON,
        layout="wide",
    )
    inject_desktop_icons()
    inject_app_styles()
    inject_table_click_modifiers()

    render_header()
    ensure_uploader_key()
    kpi_col, _, refresh_clicked = render_toolbar_row()

    df_port, portfolio_name = load_portfolio(None)
    if df_port is not None:
        render_portfolio_page(kpi_col, df_port, portfolio_name, refresh_clicked)
        render_detail_panel()
