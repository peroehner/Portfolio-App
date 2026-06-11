"""App header with logo and title."""
import base64
import mimetypes
import os

import streamlit as st

from portfolio_app.config import LOGO_PATH

_HEADER_SUBTITLE = (
    "Pick and define portfolio · Select symbol(s) · "
    "Analyse chart · Export findings"
)


def _logo_data_uri() -> str | None:
    if not os.path.exists(LOGO_PATH):
        return None
    mime, _ = mimetypes.guess_type(LOGO_PATH)
    mime = mime or "image/png"
    with open(LOGO_PATH, "rb") as img:
        encoded = base64.b64encode(img.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _header_html() -> str:
    logo_uri = _logo_data_uri()
    if logo_uri:
        logo_markup = f'<img class="app-header-logo" src="{logo_uri}" alt="" />'
    else:
        logo_markup = '<div class="app-header-logo-fallback">Compass</div>'

    return f"""
<div class="app-header-shell">
  <div class="app-header-brand">
    {logo_markup}
    <div class="app-header-text">
      <h1 class="app-header-title">Portfolio Compass</h1>
      <p class="app-header-subtitle">{_HEADER_SUBTITLE}</p>
    </div>
  </div>
</div>
<style>
  .app-header-shell {{
    margin: 0 0 0.15rem 0;
  }}
  .app-header-brand {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    min-height: 72px;
  }}
  .app-header-logo {{
    height: 72px;
    width: auto;
    border-radius: 8px;
    flex-shrink: 0;
    display: block;
  }}
  .app-header-logo-fallback {{
    height: 72px;
    width: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    color: #64748b;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    flex-shrink: 0;
  }}
  .app-header-text {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.2rem;
    min-width: 0;
  }}
  .app-header-title {{
    margin: 0;
    padding: 0;
    font-family: inherit;
    font-size: 2.35rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.03em;
    color: #0f172a;
  }}
  .app-header-subtitle {{
    margin: 0;
    padding: 0;
    font-family: inherit;
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.35;
    color: #64748b;
  }}
</style>
"""


def render_header():
    st.markdown('<div class="app-header-row"></div>', unsafe_allow_html=True)
    st.html(_header_html(), unsafe_allow_javascript=False)
