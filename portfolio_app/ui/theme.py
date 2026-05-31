"""Page chrome, CSS, and desktop icon injection."""
import streamlit as st

APP_CSS = """
    <style>
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
        max-height: 60px;
        width: auto;
        object-fit: contain;
    }
    .app-headings {
        min-width: 0;
    }
    .app-title {
        font-size: 1.35rem;
        font-weight: 1000;
        color: #111827;
        margin: 0;
        padding: 0;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }
    .app-subtitle {
        margin: 0.2rem 0 0 0;
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
        margin-bottom: 0.35rem !important;
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
    /* Section panels (bordered containers) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-portfolio) {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
        border-left: 4px solid #2563eb !important;
        margin-bottom: 0.35rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-ta) {
        background: linear-gradient(180deg, #f0fdfa 0%, #ffffff 100%);
        border-left: 4px solid #0d9488 !important;
        margin-top: 0.45rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-portfolio),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-ta) {
        padding-top: 0.15rem;
    }
    .section-header {
        display: flex;
        align-items: flex-start;
        gap: 0.65rem;
        margin: 0.1rem 0 0.45rem 0;
    }
    .section-number {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.55rem;
        height: 1.55rem;
        border-radius: 999px;
        background: #111827;
        color: #fff;
        font-size: 0.78rem;
        font-weight: 800;
        line-height: 1;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-portfolio) .section-number {
        background: #2563eb;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-panel-ta) .section-number {
        background: #0d9488;
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
        margin: 0.12rem 0 0 0;
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
    /* Toolbar row: portfolio picker, KPIs, and action buttons on one baseline */
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start;
        align-self: stretch !important;
        min-height: 2.1rem !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.kpi-strip-toolbar) {
        align-items: stretch !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"],
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] > div {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stSelectbox {
        margin-bottom: 0 !important;
        width: 100%;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-baseweb="select"] > div {
        min-height: 2.1rem !important;
        height: 2.1rem !important;
    }
    /* Toolbar icon buttons (↑ + ↺ 📁 🔄 ⋮) */
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stButton > button,
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] .stDownloadButton > button {
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
        align-items: center !important;
        flex-wrap: nowrap !important;
        gap: 0.25rem !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        min-width: 0 !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stMarkdown"] p {
        margin: 0 !important;
        line-height: 1.2 !important;
        overflow: hidden;
    }
    .tech-trend-slot {
        display: inline-flex;
        align-items: center;
        gap: 0.2rem;
        font-size: 0.86rem !important;
        line-height: 1.2;
        white-space: nowrap;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        margin: 0;
        vertical-align: middle;
    }
    .tech-trend-slot,
    .tech-trend-slot * {
        font-size: 0.86rem !important;
        line-height: 1.2 !important;
    }
    .tech-trend-slot.tech-trend-line {
        font-size: 0.86rem !important;
        line-height: 1.2 !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] .tech-trend-slot.tech-trend-line,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] .tech-trend-slot.tech-trend-line * {
        font-size: 0.86rem !important;
        line-height: 1.2 !important;
    }
    .tech-trend-slot b {
        font-size: inherit;
        font-weight: 600;
        line-height: inherit;
    }
    .tech-trend-slot.tech-trend-empty {
        color: #6e7781;
        font-style: italic;
    }
    .tech-trend-slot .trend-icon {
        height: 1.35rem !important;
        width: auto;
        margin-right: 0.2rem !important;
        flex-shrink: 0;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-baseweb="select"] > div,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) [data-baseweb="select"] > div {
        min-height: 1.85rem !important;
        height: 1.85rem !important;
        font-size: 0.76rem !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-baseweb="select"] span,
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) [data-baseweb="select"] span {
        font-size: 0.76rem !important;
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
        min-height: 1.85rem !important;
        height: 1.85rem !important;
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
        min-height: 1.85rem !important;
        height: 1.85rem !important;
        width: 100% !important;
        padding: 0 0.45rem !important;
        border-radius: 6px !important;
        border: 1px solid #d0d7de !important;
        background: #fff !important;
        font-size: 0.76rem !important;
        box-shadow: 0 1px 2px rgba(27, 31, 36, 0.06) !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) .stButton > button:disabled {
        opacity: 0.5;
        background: #f6f8fa !important;
    }
    div:has(> .tech-controls-anchor) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) .stButton > button p {
        font-size: 0.82rem !important;
        line-height: 1.2 !important;
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
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stMarkdownContainer"]:has(.kpi-strip-toolbar),
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stMarkdown"]:has(.kpi-strip-toolbar) {
        width: 100%;
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: stretch !important;
        min-height: 2.1rem !important;
        height: 2.1rem !important;
    }
    div:has(> .portfolio-toolbar-anchor) + div[data-testid="stHorizontalBlock"] [data-testid="stMarkdown"]:has(.kpi-strip-toolbar) p {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
        width: 100%;
        display: flex !important;
        align-items: stretch !important;
        min-height: 2.1rem !important;
        height: 100% !important;
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
    }
    .kpi-strip-toolbar {
        margin: 0;
        height: 2.1rem !important;
        min-height: 2.1rem !important;
        max-height: 2.1rem !important;
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
    .kpi-strip .kpi-item:last-child {
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
    .metric-chip {
        background-color: #e6f4ea;
        color: #137333;
        padding: 6px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 11px;
        margin-top: 4px;
    }
    .metric-chip.down {
        background-color: #fce8e6;
        color: #c5221f;
    }
    .metric-chip.div {
        background-color: #e8f0fe;
        color: #1a73e8;
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
            var icon = origin + "/static/myPeroLogo.png";
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
