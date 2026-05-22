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
    .app-header-row [data-testid="column"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    .app-header-row [data-testid="stImage"] img {
        max-height: 60px;
        width: auto;
        object-fit: contain;
    }
    .app-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #111;
        margin: 0;
        padding: 0;
        line-height: 1.2;
    }
    .app-title .app-muted {
        font-weight: 500;
        color: #666;
        font-size: 0.9rem;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #e8ecf0;
        margin: 0.35rem 0 0.45rem 0;
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
    .kpi-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem 1rem;
        align-items: center;
        font-size: 0.8rem;
        color: #444;
        margin: 0;
        padding: 0.35rem 0.55rem;
        background: #f6f8fa;
        border-radius: 6px;
        border: 1px solid #e8ecf0;
        min-height: 2.1rem;
    }
    .kpi-strip .kpi-item b { color: #1f77b4; font-weight: 600; }
    .kpi-strip .kpi-val { font-weight: 700; color: #111; font-size: 0.9rem; }
    .kpi-strip .kpi-file {
        max-width: 220px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .trend-line {
        font-size: 0.78rem;
        margin: 0.05rem 0 0.25rem 0;
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
