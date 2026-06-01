"""Section layout: headers and panel chrome."""
import streamlit as st

from portfolio_app.ui.user_sidebar import render_account_in_header


def _section_header_html(*, title: str, subtitle: str) -> str:
    return (
        f'<div class="section-header">'
        f'<div class="section-headings">'
        f'<p class="section-title">{title}</p>'
        f'<p class="section-subtitle">{subtitle}</p>'
        f'</div></div>'
    )


def _render_panel_account_corner() -> None:
    st.markdown('<div class="panel-account-anchor"></div>', unsafe_allow_html=True)
    ac_label, ac_sel = st.columns([0.48, 1.52], gap="small", vertical_alignment="center")
    with ac_label:
        st.markdown('<p class="panel-account-label">Account</p>', unsafe_allow_html=True)
    with ac_sel:
        render_account_in_header()


def render_section_header(
    *,
    title: str,
    subtitle: str,
    panel_class: str,
    account_in_corner: bool = False,
) -> None:
    """Section title block; pair with matching panel_class on the bordered container."""
    st.markdown(f'<div class="section-panel {panel_class}"></div>', unsafe_allow_html=True)

    if account_in_corner:
        st.markdown('<div class="section-header-row-anchor"></div>', unsafe_allow_html=True)
        title_col, account_col = st.columns([4.55, 1.45], gap="small", vertical_alignment="center")
        with title_col:
            st.markdown(_section_header_html(title=title, subtitle=subtitle), unsafe_allow_html=True)
        with account_col:
            _render_panel_account_corner()
        return

    st.markdown(_section_header_html(title=title, subtitle=subtitle), unsafe_allow_html=True)
