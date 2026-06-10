"""Page chrome, CSS, and desktop icon injection."""
import streamlit as st

APP_CSS = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');
    /* Page canvas — soft grey so bordered panels read as white cards */
    .stApp,
    [data-testid="stAppViewContainer"],
    section[data-testid="stMain"] {
        background-color: #f1f3f4 !important;
    }
    [data-testid="stMainBlockContainer"] {
        background-color: transparent !important;
    }
    /* Compact page chrome — more table visible above the fold */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.75rem !important;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    div:has(> .app-header-row) + div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        margin-bottom: 0.15rem !important;
    }
    div:has(> .app-header-row) + div[data-testid="stHorizontalBlock"] [data-testid="column"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    div:has(> .app-header-row) + div[data-testid="stHorizontalBlock"] [data-testid="stImage"] img {
        max-height: 72px;
        width: auto;
        object-fit: contain;
        border-radius: 6px;
    }
    .app-headings {
        min-width: 0;
    }
    .app-title {
        font-size: 1.65rem;
        font-weight: 1000;
        color: #111827;
        margin: 0;
        padding: 0;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }
    .app-subtitle {
        margin: 0.16rem 0 0 0;
        font-size: 1.02rem;
    }
    .panel-account-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #666;
        margin: 0;
        padding-right: 0.25rem;
        line-height: 1.2;
        letter-spacing: 0.02em;
        white-space: nowrap;
        text-align: right;
    }
    div:has(> .section-header-row-anchor) + div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        margin-top: 0 !important;
        margin-bottom: 0.2rem !important;
        padding-top: 0 !important;
    }
    div:has(> .section-header-row-anchor) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div:has(> .section-header-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:last-child {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
    }
    div:has(> .panel-account-anchor) + div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 0.45rem !important;
        width: 100% !important;
    }
    div:has(> .panel-account-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        flex: 1 1 8rem !important;
        min-width: 7rem !important;
        max-width: 11rem !important;
    }
    div:has(> .panel-account-anchor) + div[data-testid="stHorizontalBlock"] .stSelectbox {
        width: 100% !important;
        margin: 0 !important;
    }
    div:has(> .panel-account-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] > div {
        min-height: 2rem !important;
        height: 2rem !important;
    }
    div:has(> .panel-account-label) [data-testid="stTextInput"] input {
        font-size: 0.85rem;
        padding: 0.25rem 0.5rem;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #e8ecf0;
        margin: 0.35rem 0 0.45rem 0;
    }
    /* Section cards in Streamlit 1.57: border containers are stVerticalBlock nodes. */
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) {
        background-color: #f8f9fa !important;
        border: 1px solid #dadce0 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(60, 64, 67, 0.12);
        padding: 10px 12px 14px 12px !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) > div,
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) > div,
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stHorizontalBlock"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stHorizontalBlock"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="element-container"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="element-container"] {
        background-color: #f8f9fa !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) {
        border-left: 4px solid #2563eb !important;
        margin-bottom: 0.35rem;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) {
        border-left: 4px solid #0d9488 !important;
        margin-top: 0.45rem;
    }
    .section-panel {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) {
        padding-top: 0 !important;
        padding-bottom: 0.65rem !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) > div,
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        gap: 0.15rem !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stVerticalBlock"] {
        gap: 0.15rem !important;
        padding-top: 0 !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stMarkdown"]:has(.section-header),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stMarkdown"]:has(.section-header),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stMarkdownContainer"]:has(.section-header),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stMarkdownContainer"]:has(.section-header) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="stVerticalBlock"] > div:first-child,
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="stVerticalBlock"] > div:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-portfolio) [data-testid="element-container"],
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .section-panel-ta) [data-testid="element-container"] {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    .section-header {
        margin: 0 0 0.25rem 0;
        padding: 0;
    }
    .section-headings {
        min-width: 0;
    }
    .section-title {
        margin: 0;
        font-size: 1rem;
        font-weight: 800;
        color: #111827;
        line-height: 1.2;
    }
    .section-subtitle {
        margin: 0.05rem 0 0 0;
        font-size: 0.78rem;
        font-weight: 500;
        color: #6b7280;
        line-height: 1.35;
    }
    /* Technical Analysis symbol bar row (list frame + export) */
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
        margin-bottom: 0.15rem !important;
        gap: 0.45rem !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child {
        background: linear-gradient(180deg, #ecfdf5 0%, #f8fffe 100%) !important;
        border: 1px solid #99f6e4 !important;
        border-left: 4px solid #14b8a6 !important;
        border-radius: 8px !important;
        padding: 0.35rem 0.5rem !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 0.3rem !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child .stButton > button {
        background: #ffffff !important;
        border: 1px solid #14b8a6 !important;
        color: #0f766e !important;
        min-height: 2rem !important;
        height: 2rem !important;
        padding: 0.12rem 0.55rem !important;
        border-radius: 999px !important;
        box-shadow: 0 1px 2px rgba(15, 118, 110, 0.12) !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child .stButton > button p {
        color: #0f766e !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        line-height: 1.2 !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child .stButton > button:hover {
        background: #f0fdfa !important;
        border-color: #0d9488 !important;
        color: #115e59 !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:first-child .stButton > button:hover p {
        color: #115e59 !important;
    }
    .ta-sym-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 2rem;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        color: #0f766e;
        background: #ffffff;
        border: 1px solid #14b8a6;
        box-shadow: 0 1px 2px rgba(15, 118, 110, 0.12);
        white-space: nowrap;
    }
    .ta-sym-chip-active {
        font-size: 0.92rem;
        font-weight: 900;
        border-width: 2px;
        letter-spacing: 0.02em;
        box-shadow: 0 1px 3px rgba(15, 118, 110, 0.18);
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:last-child {
        display: flex !important;
        align-items: center !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:last-child [data-testid="stDownloadButton"] button {
        background: #ecfdf5 !important;
        border: 1px solid #99f6e4 !important;
        color: #0f766e !important;
        font-weight: 700 !important;
        min-height: 2rem !important;
        border-radius: 8px !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:last-child [data-testid="stDownloadButton"] button:hover:not(:disabled) {
        background: #d1fae5 !important;
        border-color: #14b8a6 !important;
    }
    div:has(> .ta-symbol-nav-row-anchor) + div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"]:last-child [data-testid="stDownloadButton"] button:disabled {
        opacity: 0.5 !important;
    }
    .ta-chart-heading {
        display: flex;
        align-items: baseline;
        gap: 0.55rem;
        margin: 0 0 0.35rem 0;
        padding: 0.15rem 0.1rem 0.25rem;
        border-bottom: 1px solid #e2e8f0;
    }
    .ta-chart-symbol {
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: 0.03em;
        color: #0f766e;
    }
    .ta-chart-meta {
        font-size: 0.72rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .ta-sym-ellipsis {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        color: #94a3b8;
        font-size: 1rem;
        font-weight: 700;
        user-select: none;
    }
    .section-empty-state {
        margin: 0.35rem 0 0.5rem 0;
        padding: 1rem 0.85rem;
        border-radius: 8px;
        border: 1px dashed #cbd5e1;
        background: rgba(255, 255, 255, 0.72);
        text-align: center;
    }
    .section-empty-title {
        margin: 0;
        font-size: 0.92rem;
        font-weight: 700;
        color: #334155;
    }
    .section-empty-body {
        margin: 0.35rem 0 0 0;
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.45;
    }
    .tech-header {
        font-size: 0.95rem;
        font-weight: 700;
        color: #111;
        margin: 0.15rem 0 0.3rem 0;
        line-height: 1.25;
    }
    [data-testid="stTabs"] {
        margin-bottom: 0.15rem;
    }
    [data-testid="stPlotlyChart"] {
        margin-bottom: 0.15rem;
    }
    hr[data-testid="stDivider"] {
        margin: 0.35rem 0 !important;
    }
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.35rem;
    }
    [data-testid="stProgress"] {
        margin-bottom: 0.2rem;
    }
    [data-testid="stProgress"] label {
        font-size: 0.8rem;
    }
    /* Toolbar row: portfolio picker, KPIs, and action buttons — one shared height */
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] {
        --portfolio-toolbar-h: 2.25rem;
        align-items: center !important;
        gap: 0.35rem !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        align-self: center !important;
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div {
        width: 100%;
        margin: 0 !important;
        padding: 0 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="element-container"] {
        margin: 0 !important;
        padding: 0 !important;
        min-height: 0 !important;
        height: var(--portfolio-toolbar-h) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: stretch !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        width: 100%;
        height: var(--portfolio-toolbar-h) !important;
        min-height: var(--portfolio-toolbar-h) !important;
        justify-content: center !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stHtml"] {
        width: 100%;
        margin: 0 !important;
        padding: 0 !important;
        height: var(--portfolio-toolbar-h) !important;
        min-height: var(--portfolio-toolbar-h) !important;
        display: flex !important;
        align-items: center !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stHtml"] > div {
        width: 100%;
        margin: 0 !important;
        padding: 0 !important;
        height: var(--portfolio-toolbar-h) !important;
        display: flex !important;
        align-items: center !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.kpi-toolbar-slot) {
        height: auto !important;
        min-height: var(--portfolio-toolbar-h) !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.kpi-toolbar-slot) [data-testid="element-container"],
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.kpi-toolbar-slot) [data-testid="stHtml"],
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.kpi-toolbar-slot) [data-testid="stHtml"] > div {
        height: auto !important;
        min-height: var(--portfolio-toolbar-h) !important;
        max-height: none !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .kpi-toolbar-slot {
        width: 100%;
        min-height: var(--portfolio-toolbar-h);
        height: auto;
        max-height: none;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        justify-content: center;
        gap: 0.08rem;
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    .kpi-sync-footnote {
        font-size: 0.58rem;
        font-weight: 500;
        color: #6e7781;
        text-align: right;
        line-height: 1.1;
        padding: 0 0.45rem 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex-shrink: 0;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"],
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] label[data-testid="stWidgetLabel"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stSelectbox,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stSelectbox"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100%;
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stSelectbox > div,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stSelectbox"] > div {
        gap: 0 !important;
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] {
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] > div {
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] span {
        line-height: 1.2 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stButton,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton {
        margin: 0 !important;
        width: 100%;
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
    }
    /* Toolbar icon buttons (↑ + ↺ 📁 🔄) */
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
        max-height: var(--portfolio-toolbar-h) !important;
        width: 100% !important;
        padding: 0 !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        color: #24292f !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
        font-size: 1.28rem !important;
        line-height: 1 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button:hover,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton > button:hover {
        border-color: #b8c5d0 !important;
        background: #f6f8fa !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button p,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton > button p {
        font-size: 1.28rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100%;
        text-align: center;
        white-space: nowrap;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Second toolbar row: Portfolio (DB) + File (CSV) when ⋮ expanded */
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] {
        --portfolio-toolbar-h: 2.25rem;
        align-items: center !important;
        gap: 0.35rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.15rem !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
    }
    /* Shrink side columns; spacer column absorbs remaining width */
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child,
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
        max-width: none !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        width: auto !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
        justify-content: flex-start !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        justify-content: flex-end !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
        gap: 0.25rem !important;
        width: fit-content !important;
        max-width: 100% !important;
        flex: 0 0 auto !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.stButton),
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.stDownloadButton) {
        flex: 0 0 var(--portfolio-toolbar-h) !important;
        min-width: var(--portfolio-toolbar-h) !important;
        max-width: var(--portfolio-toolbar-h) !important;
        width: var(--portfolio-toolbar-h) !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    /* Portfolio: icon sub-row only as wide as its buttons */
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child > div > [data-testid="stHorizontalBlock"] {
        width: fit-content !important;
        max-width: 100% !important;
        flex: 0 0 auto !important;
        justify-content: flex-start !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        display: flex !important;
        justify-content: flex-end !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child > div {
        width: 100% !important;
        display: flex !important;
        justify-content: flex-end !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child > div > [data-testid="stHorizontalBlock"] {
        width: fit-content !important;
        flex: 0 0 auto !important;
        margin-left: auto !important;
        justify-content: flex-end !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button,
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton > button {
        min-height: var(--portfolio-toolbar-h) !important;
        height: var(--portfolio-toolbar-h) !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] .portfolio-toolbar-group-label {
        display: block;
        font-size: 0.62rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: #57606a;
        line-height: 1;
        white-space: nowrap;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .portfolio-toolbar-group-label {
        color: #0969da;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .portfolio-toolbar-group-label {
        color: #8250df;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton > button,
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stDownloadButton > button {
        border-color: #54aeff66 !important;
        background: #f6f8fa !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button,
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stDownloadButton > button {
        border-style: dashed !important;
        border-color: #8250df88 !important;
        background: #fbefff !important;
        color: #6639ba !important;
    }
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button:hover,
    div:has(> .portfolio-toolbar-actions-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stDownloadButton > button:hover {
        border-color: #8250df !important;
        background: #f3d9ff !important;
    }
    /* View tabs row — Gmail-style (icon + label, blue active underline) */
    .portfolio-view-tabs-anchor {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stMarkdown"]:has(.portfolio-view-tabs-anchor) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) {
        align-items: flex-end !important;
        margin-bottom: 0.35rem !important;
        gap: 0.35rem !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:first-child {
        border-bottom: 1px solid #dadce0;
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
        align-self: stretch !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:first-child [data-testid="element-container"],
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:first-child [data-testid="stVerticalBlock"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100%;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100%;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
        display: none !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-end !important;
        flex-wrap: nowrap !important;
        gap: 0 !important;
        width: 100%;
        border: none !important;
        background: transparent !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] {
        flex: 0 0 auto !important;
        display: inline-flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 0.45rem !important;
        margin: 0 1.5rem 0 0 !important;
        padding: 0.72rem 0.1rem 0.58rem 0.1rem !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: #5f6368 !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        cursor: pointer !important;
        min-height: unset !important;
        transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:hover {
        color: #202124 !important;
        background: rgba(60, 64, 67, 0.06) !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        color: #1a73e8 !important;
        border-bottom-color: #1a73e8 !important;
        margin-bottom: -1px !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked):hover {
        color: #1a73e8 !important;
        background: transparent !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] input[type="radio"] {
        position: absolute !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        pointer-events: none !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] p {
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap;
    }
    /* Tab icons (Material Symbols) — order: Standard, ROI, Trends, Valuation */
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:nth-of-type(1)::before {
        content: "table_rows";
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:nth-of-type(2)::before {
        content: "payments";
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:nth-of-type(3)::before {
        content: "trending_up";
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:nth-of-type(4)::before {
        content: "monitoring";
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]::before {
        font-family: "Material Symbols Outlined";
        font-size: 1.125rem;
        font-weight: normal;
        font-style: normal;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:last-child {
        align-self: center !important;
        padding-bottom: 0.35rem !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:last-child .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 2.1rem !important;
        height: 2.1rem !important;
        width: 100% !important;
        padding: 0 !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
        font-size: 1.28rem !important;
        line-height: 1 !important;
    }
    div:has(.portfolio-view-tabs-anchor) [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) > div[data-testid="column"]:last-child .stButton > button:hover {
        border-color: #b8c5d0 !important;
        background: #f6f8fa !important;
    }
    /* Add symbol / save row */
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 2.1rem !important;
        height: 2.1rem !important;
        width: 100% !important;
        padding: 0 0.75rem !important;
        border-radius: 6px !important;
        font-size: 0.82rem !important;
        line-height: 1.2 !important;
    }
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton > button {
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
    }
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button p {
        font-size: 0.82rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        white-space: nowrap;
    }
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="input"] > div,
    div:has(> .portfolio-edit-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] > div {
        min-height: 2.1rem !important;
        height: 2.1rem !important;
    }
    /* Technical analysis: single controls row */
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] {
        --tech-controls-row-h: 2.15rem;
        align-items: center !important;
        flex-wrap: nowrap !important;
        gap: 0.3rem !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        min-width: 0 !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stMarkdown"] p {
        margin: 0 !important;
        line-height: 1.35 !important;
        overflow: hidden;
    }
    .tech-trend-slot {
        margin: 0;
        max-width: 100%;
    }
    .ta-trend-card {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        width: 100%;
        max-width: 100%;
        min-height: var(--tech-controls-row-h, 2.15rem);
        padding: 0.3rem 0.55rem;
        border-radius: 8px;
        border: 1px solid #d0d7de;
        background: #f6f8fa;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.05);
        box-sizing: border-box;
        overflow: hidden;
    }
    .ta-trend-card.bull {
        border-color: #b7dfc8;
        background: linear-gradient(180deg, #f3fbf6 0%, #eaf7ef 100%);
    }
    .ta-trend-card.bear {
        border-color: #f5c2c0;
        background: linear-gradient(180deg, #fff7f6 0%, #fdecea 100%);
    }
    .ta-trend-card.empty {
        border-style: dashed;
        border-color: #d0d7de;
        background: #fafbfc;
        color: #6e7781;
        font-size: 0.72rem;
        font-style: italic;
        justify-content: center;
    }
    .ta-trend-leading {
        display: flex;
        align-items: center;
        flex-shrink: 0;
    }
    .ta-trend-leading .trend-icon {
        height: 1.75rem !important;
        width: auto;
        margin: 0 !important;
        object-fit: contain;
        border-radius: 5px;
        box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08);
    }
    .ta-trend-body {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 0.08rem;
        min-width: 0;
        flex: 1 1 auto;
    }
    .ta-trend-top {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        min-width: 0;
    }
    .ta-trend-badge {
        font-size: 0.74rem !important;
        font-weight: 700;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .ta-trend-card.bull .ta-trend-badge { color: #137333; }
    .ta-trend-card.bear .ta-trend-badge { color: #c5221f; }
    .ta-trend-id {
        font-size: 0.62rem !important;
        font-weight: 700;
        color: #57606a;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 999px;
        padding: 0.05rem 0.35rem;
        white-space: nowrap;
    }
    .ta-trend-foot {
        min-width: 0;
    }
    .ta-trend-range {
        font-size: 0.66rem !important;
        color: #57606a;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .ta-trend-stats {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        justify-content: center;
        gap: 0.08rem;
        flex-shrink: 0;
        margin-left: 0.15rem;
    }
    .ta-trend-pct {
        font-size: 0.82rem !important;
        font-weight: 800;
        line-height: 1.1;
        white-space: nowrap;
    }
    .ta-trend-card.bull .ta-trend-pct { color: #137333; }
    .ta-trend-card.bear .ta-trend-pct { color: #c5221f; }
    .ta-trend-count {
        font-size: 0.62rem !important;
        font-weight: 600;
        color: #6e7781;
        white-space: nowrap;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-baseweb="select"] > div,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) [data-baseweb="select"] > div {
        min-height: var(--tech-controls-row-h) !important;
        height: var(--tech-controls-row-h) !important;
        font-size: 0.78rem !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-baseweb="select"] span,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) [data-baseweb="select"] span {
        font-size: 0.78rem !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        justify-content: flex-end !important;
        margin-left: auto;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child label {
        font-size: 0.78rem !important;
        white-space: nowrap;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child [data-testid="stWidgetLabel"] {
        margin-bottom: 0 !important;
    }
    /* Technical analysis: narrow month-step icons */
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) .stButton > button,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: var(--tech-controls-row-h) !important;
        height: var(--tech-controls-row-h) !important;
        width: 100% !important;
        padding: 0 !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        font-size: 1.05rem !important;
        line-height: 1 !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) .stButton > button p,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) .stButton > button p {
        font-size: 1.2rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    /* Technical analysis: Re-Analyse */
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: var(--tech-controls-row-h) !important;
        height: var(--tech-controls-row-h) !important;
        width: 100% !important;
        padding: 0 0.45rem !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        font-size: 0.78rem !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) .stButton > button:disabled {
        opacity: 0.5;
        background: #f6f8fa !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) .stButton > button p {
        font-size: 0.78rem !important;
        line-height: 1.35 !important;
        margin: 0 !important;
        white-space: nowrap;
    }
    /* Technical analysis sidebar: export */
    div:has(.tech-sidebar-anchor) .stDownloadButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 2.1rem !important;
        height: 2.1rem !important;
        width: 100% !important;
        padding: 0 0.55rem !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        font-size: 0.8rem !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
    }
    div:has(.tech-sidebar-anchor) .stDownloadButton > button p {
        font-size: 0.8rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        white-space: nowrap;
    }
    .kpi-strip {
        display: flex;
        flex-wrap: nowrap;
        gap: 0.5rem;
        align-items: center;
        justify-content: space-between;
        font-size: 0.82rem;
        color: #444;
        margin: 0;
        padding: 0 0.75rem;
        background: #f6f8fa;
        border-radius: 6px;
        border: 1px solid #d0d7de;
        box-sizing: border-box;
        width: 100%;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06);
        align-self: center;
    }
    .kpi-strip-toolbar {
        margin: 0 !important;
        height: var(--portfolio-toolbar-h, 2.25rem) !important;
        min-height: var(--portfolio-toolbar-h, 2.25rem) !important;
        max-height: var(--portfolio-toolbar-h, 2.25rem) !important;
        flex: 1 1 auto;
    }
    .kpi-strip .kpi-item {
        display: inline-flex;
        flex: 1 1 0;
        min-width: 0;
        align-items: center;
        justify-content: center;
        gap: 0.3rem;
        white-space: nowrap;
        line-height: 1.2;
    }
    .kpi-strip .kpi-item:first-child {
        justify-content: flex-start;
    }
    .kpi-strip-toolbar .kpi-item:last-child {
        justify-content: flex-end;
    }
    .kpi-strip .kpi-lbl,
    .kpi-strip .kpi-item b {
        color: #1f77b4;
        font-weight: 600;
        flex-shrink: 0;
    }
    .kpi-strip .kpi-nums {
        display: inline-flex;
        align-items: baseline;
        gap: 0.15rem;
        min-width: 0;
        white-space: nowrap;
    }
    .kpi-strip .kpi-val {
        font-weight: 700;
        color: #111;
        font-size: 0.9rem;
    }
    .kpi-strip .kpi-pct {
        font-weight: 600;
        font-size: 0.78rem;
        flex-shrink: 0;
    }
    .kpi-strip .kpi-pct-up {
        color: #0d7a3d;
    }
    .kpi-strip .kpi-pct-down {
        color: #c0392b;
    }
    [data-testid="stHorizontalBlock"] button p {
        white-space: nowrap;
    }
    .kpi-inline {
        font-size: 0.78rem;
        color: #444;
        white-space: nowrap;
    }
    .kpi-inline b {
        color: #1f77b4;
        font-weight: 600;
        margin-right: 0.15rem;
    }
    .kpi-strip .kpi-file {
        max-width: 220px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .trend-line {
        font-size: 0.78rem;
        margin: 0;
        padding: 0;
        line-height: 1.3;
    }
    .trend-bull { color: #137333; }
    .trend-bear { color: #c5221f; }
    .trend-line .trend-icon {
        height: 1.55rem;
        width: auto;
        vertical-align: middle;
        margin-right: 0.35rem;
        border-radius: 4px;
        object-fit: cover;
        box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
    }
    .trend-icon-emoji {
        font-size: 1.15rem;
        vertical-align: middle;
        margin-right: 0.3rem;
    }
    .ta-side-panel {
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
        margin-top: 0.15rem;
    }
    .ta-side-section {
        background: #f6f8fa;
        border: 1px solid #d0d7de;
        border-radius: 8px;
        padding: 0.55rem 0.6rem 0.6rem;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.05);
    }
    .ta-side-heading {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #57606a;
        margin: 0 0 0.45rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid #d8dee4;
    }
    .ta-metric-stack {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .ta-price-pill {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.35rem;
        padding: 0.35rem 0.5rem;
        border-radius: 6px;
        background: #fff;
        border: 1px solid #d0d7de;
        font-size: 0.72rem;
        color: #57606a;
    }
    .ta-price-pill strong {
        color: #111;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .ta-metric-card {
        border-radius: 6px;
        padding: 0.42rem 0.5rem;
        border: 1px solid transparent;
        background: #fff;
    }
    .ta-metric-card.up {
        border-color: #b7dfc8;
        background: linear-gradient(180deg, #f3fbf6 0%, #eaf7ef 100%);
    }
    .ta-metric-card.down {
        border-color: #f5c2c0;
        background: linear-gradient(180deg, #fff7f6 0%, #fdecea 100%);
    }
    .ta-metric-card.flat {
        border-color: #d0d7de;
        background: #fff;
    }
    .ta-metric-card.div {
        border-color: #c6dafc;
        background: linear-gradient(180deg, #f5f9ff 0%, #e8f0fe 100%);
    }
    .ta-metric-top {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.25rem;
        margin-bottom: 0.2rem;
    }
    .ta-metric-label {
        font-size: 0.68rem;
        font-weight: 600;
        color: #57606a;
        line-height: 1.2;
    }
    .ta-metric-value {
        font-size: 0.8rem;
        font-weight: 700;
        color: #111;
        white-space: nowrap;
    }
    .ta-metric-card.up .ta-metric-value { color: #137333; }
    .ta-metric-card.down .ta-metric-value { color: #c5221f; }
    .ta-metric-card.div .ta-metric-value { color: #1a73e8; }
    .ta-metric-foot {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.25rem;
        font-size: 0.68rem;
        line-height: 1.2;
    }
    .ta-metric-delta {
        font-weight: 700;
    }
    .ta-metric-card.up .ta-metric-delta { color: #137333; }
    .ta-metric-card.down .ta-metric-delta { color: #c5221f; }
    .ta-metric-ref {
        color: #6e7781;
        white-space: nowrap;
    }
    .ta-metric-empty,
    .ta-fib-empty {
        font-size: 0.72rem;
        color: #6e7781;
        padding: 0.35rem 0.1rem;
        font-style: italic;
    }
    .ta-fib-window {
        margin-bottom: 0.3rem;
    }
    .ta-fib-range {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        color: #1f77b4;
        background: #fff;
        border: 1px solid #c6dafc;
        border-radius: 999px;
        padding: 0.15rem 0.45rem;
        white-space: nowrap;
    }
    .ta-fib-sticky-badge {
        display: inline-block;
        margin-left: 0.35rem;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #7c3aed;
        background: #f3e8ff;
        border: 1px solid #d8b4fe;
        border-radius: 999px;
        padding: 0.12rem 0.4rem;
        vertical-align: middle;
    }
    .ta-pin-woi-inline {
        display: inline-block;
        margin-left: 0.1rem;
        font-size: 0.78rem;
        line-height: 1.35;
        color: #5b21b6;
        white-space: nowrap;
    }
    .ta-fib-anchor {
        font-size: 0.68rem;
        color: #57606a;
        line-height: 1.35;
        margin: 0 0 0.4rem 0;
        word-break: break-word;
    }
    .ta-fib-list {
        display: flex;
        flex-direction: column;
        gap: 0.28rem;
    }
    .ta-fib-row {
        display: grid;
        grid-template-columns: 1fr auto auto;
        align-items: center;
        gap: 0.2rem 0.35rem;
        padding: 0.3rem 0.4rem;
        border-radius: 5px;
        background: #fff;
        border: 1px solid #e1e4e8;
        font-size: 0.68rem;
        line-height: 1.2;
    }
    .ta-fib-row.closest {
        border-color: #c6dafc;
        background: #f5f9ff;
    }
    .ta-fib-row.near {
        border-color: #f9ab00;
        background: #fffbf0;
        box-shadow: 0 0 0 1px rgba(249, 171, 0, 0.15);
    }
    .ta-fib-lbl {
        color: #444;
        font-weight: 500;
        min-width: 0;
    }
    .ta-fib-val {
        font-weight: 700;
        color: #111;
        white-space: nowrap;
    }
    .ta-fib-prox {
        font-size: 0.62rem;
        font-weight: 700;
        color: #b06000;
        background: #fff3cd;
        border-radius: 999px;
        padding: 0.1rem 0.3rem;
        white-space: nowrap;
    }
    .ta-fib-row.near .ta-fib-prox {
        color: #7a4e00;
        background: #ffe08a;
    }
    [data-testid="stDataFrame"] td { color: black !important; }
    /* ROI editor: hide misleading auto-sum row (wrong % / $ totals) */
    div:has(> .roi-table-anchor) + div [data-testid="stDataEditor"] [class*="summary"],
    div:has(> .roi-table-anchor) + div [data-testid="stDataEditor"] .dvn-summary-row,
    div:has(> .roi-table-anchor) + div [data-testid="stDataEditor"] [class*="gdg-summary"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
        padding-top: 0;
    }
    </style>
    """


def inject_desktop_icons():
    """Favicon, Apple touch icon, and web manifest at real /static/ URLs."""
    st.markdown(
        """
        <script>
        (function () {
            var origin = window.location.origin;
            var icon = origin + "/static/compass-icon.png";
            function addLink(rel, href, sizes) {
                var sel = 'link[rel="' + rel + '"]';
                if (document.querySelector(sel)) return;
                var el = document.createElement("link");
                el.rel = rel;
                el.href = href;
                if (sizes) el.sizes = sizes;
                document.head.appendChild(el);
            }
            addLink("icon", icon);
            addLink("shortcut icon", icon);
            addLink("apple-touch-icon", icon, "180x180");
            addLink("manifest", origin + "/static/manifest.webmanifest");
            var theme = document.querySelector('meta[name="theme-color"]');
            if (!theme) {
                theme = document.createElement("meta");
                theme.name = "theme-color";
                theme.content = "#1f77b4";
                document.head.appendChild(theme);
            }
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def inject_app_styles():
    st.markdown(APP_CSS, unsafe_allow_html=True)
