import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from scipy.signal import argrelextrema
import sys
import os
import time
import html
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "static", "myPeroLogo.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(APP_DIR, "myPeroLogo.png")
PAGE_ICON = (
    os.path.join("static", "myPeroLogo.png")
    if os.path.exists(os.path.join(APP_DIR, "static", "myPeroLogo.png"))
    else "myPeroLogo.png"
)


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


# --- KONFIGURATION & THEME ---
st.set_page_config(
    page_title="Pero Portfolio & Trend Analyzer",
    page_icon=PAGE_ICON,
    layout="wide",
)
inject_desktop_icons()

st.markdown("""
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
    """, unsafe_allow_html=True)


# --- PARSE COMMAND LINE ARGUMENTS ---
BULL_TREND_PATH = os.path.join(APP_DIR, "bull-trend.png")
BEAR_TREND_PATH = os.path.join(APP_DIR, "bear-trend.png")
PORTFOLIO_FILE_CANDIDATES = ("myPortfolio.csv", "Sample-Portfolio.csv")
CHART_HEIGHT = 340


@st.cache_data
def get_trend_icon_html(trend_type):
    """Inline trend icons from bull-trend.png / bear-trend.png."""
    paths = {
        "Bullish": (BULL_TREND_PATH, "Bull", "Bullish"),
        "Bearish": (BEAR_TREND_PATH, "Bear", "Bearish"),
    }
    if trend_type in paths:
        path, alt, title = paths[trend_type]
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return (
                f'<img class="trend-icon" src="data:image/png;base64,{b64}" '
                f'alt="{alt}" title="{title}"/>'
            )
    return '<span class="trend-icon-emoji">?</span>'


def get_cli_filename():
    """Extrahiert den Dateinamen, falls via '-f <filename>' im Terminal übergeben."""
    try:
        args = sys.argv
        if "-f" in args:
            idx = args.index("-f")
            if idx + 1 < len(args):
                potential_file = args[idx + 1]
                if os.path.isabs(potential_file) and os.path.exists(potential_file):
                    return potential_file
                for base in (os.getcwd(), APP_DIR):
                    candidate = os.path.join(base, potential_file)
                    if os.path.exists(candidate):
                        return candidate
    except Exception:
        pass
    return None


def _parse_portfolio_df(df):
    df = df.copy()
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"])
    return df


def load_portfolio_from_path(path):
    df = _parse_portfolio_df(pd.read_csv(path, sep=";"))
    return df, os.path.basename(path)


def get_mock_portfolio_df():
    """Demo portfolio when no CSV is available (AAPL, Google, CRWD, NBIS, MELI)."""
    df = pd.DataFrame([
        {"Symbol": "AAPL", "Name": "Apple Inc.", "Shares": 100, "PurchaseDate": "2024-01-15", "AvgCost": 175.0, "TargetPrice": 220.0, "Currency": "USD"},
        {"Symbol": "GOOGL", "Name": "Alphabet (Google)", "Shares": 50, "PurchaseDate": "2024-03-01", "AvgCost": 140.0, "TargetPrice": 200.0, "Currency": "USD"},
        {"Symbol": "CRWD", "Name": "CrowdStrike", "Shares": 75, "PurchaseDate": "2024-06-01", "AvgCost": 280.0, "TargetPrice": 400.0, "Currency": "USD"},
        {"Symbol": "NBIS", "Name": "Nebius Group", "Shares": 200, "PurchaseDate": "2024-09-01", "AvgCost": 25.0, "TargetPrice": 45.0, "Currency": "USD"},
        {"Symbol": "MELI", "Name": "MercadoLibre", "Shares": 30, "PurchaseDate": "2023-11-01", "AvgCost": 1500.0, "TargetPrice": 2200.0, "Currency": "USD"},
    ])
    return _parse_portfolio_df(df)


# --- KERN-ALGORITHMEN ---

def normalize_dividend_yield(div_yield):
    """Convert fractional yield to percent (0.02 → 2.0)."""
    if div_yield is None or div_yield == 0:
        return 0.0
    div_yield = float(div_yield)
    if div_yield < 1:
        return div_yield * 100
    return div_yield


def extract_dividend_yield(info):
    """Parse dividend yield from Yahoo info (field format varies)."""
    if not info:
        return 0.0
    trailing = info.get("trailingAnnualDividendYield")
    if trailing is not None and trailing > 0:
        return normalize_dividend_yield(trailing)
    div = info.get("dividendYield")
    if div is None or div == 0:
        return 0.0
    div = float(div)
    # Fraction (e.g. 0.0035) vs percent points (e.g. 0.36 = 0.36%)
    if div < 0.2:
        return div * 100
    return div


METADATA_COLS = {"Div Yield", "Est Target", "Upside %"}


def period_return(close_series, price, trading_days):
    """Percent change over `trading_days` trading days."""
    if len(close_series) < trading_days + 1:
        return 0.0
    past = close_series.iloc[-(trading_days + 1)]
    if past == 0 or pd.isna(past):
        return 0.0
    return ((price / past) - 1) * 100


def compute_trend_returns(price, close_series):
    """Rolling returns for 5D, 1M (~21d), 6M (~126d), 12M (~252d)."""
    return {
        "5D": period_return(close_series, price, 5),
        "1M": period_return(close_series, price, 21),
        "6M": period_return(close_series, price, 126),
        "12M": period_return(close_series, price, 252),
    }


def daily_change_pct(close_series):
    """Approximate daily change from last two closes (no Yahoo info call)."""
    if len(close_series) < 2:
        return 0.0
    prev = close_series.iloc[-2]
    if prev == 0 or pd.isna(prev):
        return 0.0
    return ((close_series.iloc[-1] / prev) - 1) * 100


def find_multiple_trends(df, max_trends=4, strong_threshold=0.05, order=10):
    """Findet signifikante Trends über lokale Swing Highs und Lows."""
    trends = []
    if df is None or df.empty or 'Close' not in df.columns:
        return trends
        
    prices = df['Close'].values
    dates = pd.to_datetime(df.index)
    if getattr(dates, "tz", None) is not None:
        dates = dates.tz_localize(None)
    
    total_len = len(prices)
    if total_len < 15:
        return trends

    if total_len < 40:
        order = 3
    elif total_len < 100:
        order = 5

    local_max_idx = argrelextrema(prices, np.greater, order=order)[0]
    local_min_idx = argrelextrema(prices, np.less, order=order)[0]
    
    all_extrema = sorted(list(local_max_idx) + list(local_min_idx))
    
    if len(all_extrema) < 2:
        all_extrema = [0, total_len - 1]
    else:
        if all_extrema[0] != 0:
            all_extrema.insert(0, 0)
        if all_extrema[-1] != total_len - 1:
            all_extrema.append(total_len - 1)

    raw_legs = []
    for i in range(len(all_extrema) - 1):
        idx_start = all_extrema[i]
        idx_end = all_extrema[i+1]
        
        if idx_end - idx_start < 2:
            continue
            
        p_start = prices[idx_start]
        p_end = prices[idx_end]
        
        if p_start == 0:
            continue
            
        move_pct = abs(p_end - p_start) / p_start
        
        if move_pct >= strong_threshold:
            raw_legs.append({
                "f_start": dates[idx_start],
                "f_end": dates[idx_end],
                "price_start": p_start,
                "price_end": p_end,
                "move_pct": move_pct,
                "type": "Bullish" if p_start < p_end else "Bearish"
            })
            
    sorted_legs = sorted(raw_legs, key=lambda x: x["move_pct"], reverse=True)
    
    for idx, leg in enumerate(sorted_legs[:max_trends]):
        leg["id"] = f"T{idx+1}"
        trends.append(leg)
        
    return trends


# --- DATENBESCHAFFUNG ---

TABLE_HISTORY_PERIOD = "2y"   # 12M trend needs ~253 trading days; 1y is often too short
DETAIL_HISTORY_PERIOD = "2y"  # Fibonacci / technical chart (lazy per ticker)
METADATA_BATCH_SIZE = 2       # symbols per background tick (Yahoo rate limits)
METADATA_POLL_SECONDS = 1.5   # fragment refresh interval while loading
ANALYST_LOADED_NOTICE_SEC = 3

# Table detail tabs — edit column lists per view as needed
TABLE_VIEW_COLUMNS = {
    "Standard": [
        "Symbol", "🌐 Price", "Change %", "Div Yield", "Est Target", "Upside %",
    ],
    "Trends": [
        "Symbol", "🌐 Price", "Change %", "5D", "1M", "6M", "12M",
    ],
    "ROI": [
        "Symbol", "🌐 Price", "Shares", "PurchaseDate", "Cost/Share",
        "📈 Total %", "Total $", "Ø CAGR", "📈 Target", "Est Target",
    ],
}

TABLE_PERCENT_COLS = [
    "📈 Total %", "Change %", "Upside %", "Ø CAGR", "Target %", "5D", "1M", "6M", "12M",
]
TABLE_CURRENCY_COLS = ["📈 Target", "Target $", "Total $", "Est Target", "Cost/Share", "🌐 Price"]
TABLE_PNL_COLS = ["Total $"]
TABLE_GRADIENT_EXCLUDE = {"Div Yield"}

# Signed cell colors: zero = white, positive = green, negative = red
_COLOR_POSITIVE = (19, 115, 51)
_COLOR_NEGATIVE = (197, 34, 31)


def _signed_cell_color(intensity, rgb_end):
    intensity = max(0.0, min(1.0, intensity))
    r = int(255 - (255 - rgb_end[0]) * intensity)
    g = int(255 - (255 - rgb_end[1]) * intensity)
    b = int(255 - (255 - rgb_end[2]) * intensity)
    return f"background-color: rgb({r},{g},{b}); color: black"


def style_signed_column(series):
    """Green for gains, red for losses; intensity scales with magnitude."""
    numeric = pd.to_numeric(series, errors="coerce")
    positives = numeric[numeric > 0]
    negatives = numeric[numeric < 0]
    max_pos = positives.max() if not positives.empty else 0
    max_neg = negatives.abs().max() if not negatives.empty else 0

    styles = []
    for val in numeric:
        if pd.isna(val) or val == 0:
            styles.append("background-color: white; color: black")
        elif val > 0:
            intensity = val / max_pos if max_pos else 0
            styles.append(_signed_cell_color(intensity, _COLOR_POSITIVE))
        else:
            intensity = abs(val) / max_neg if max_neg else 0
            styles.append(_signed_cell_color(intensity, _COLOR_NEGATIVE))
    return styles


def _read_uploaded_portfolio(uploaded_file):
    """Read uploaded CSV; Streamlit files must be rewound on each rerun."""
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=";")
    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV is empty or has no columns")
    return _parse_portfolio_df(df)


def load_portfolio(uploaded_file):
    """Lädt Portfolio: Upload > -f CLI > myPortfolio.csv > Sample-Portfolio.csv > Demo-Mock."""
    try:
        if uploaded_file is not None:
            cache_key = (
                f"{st.session_state.get('uploader_key', 0)}:"
                f"{uploaded_file.name}:"
                f"{getattr(uploaded_file, 'size', 0)}"
            )
            if st.session_state.get("uploaded_portfolio_cache_key") == cache_key:
                return (
                    st.session_state.uploaded_portfolio_df.copy(),
                    uploaded_file.name,
                )
            df = _read_uploaded_portfolio(uploaded_file)
            st.session_state.uploaded_portfolio_cache_key = cache_key
            st.session_state.uploaded_portfolio_df = df
            return df, uploaded_file.name

        cli_file = get_cli_filename()
        if cli_file is not None:
            return load_portfolio_from_path(cli_file)

        for filename in PORTFOLIO_FILE_CANDIDATES:
            path = os.path.join(APP_DIR, filename)
            if os.path.exists(path):
                return load_portfolio_from_path(path)

        return get_mock_portfolio_df(), "Demo Portfolio (mock)"
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
        return None, "Load error"


@st.cache_data(ttl=300, show_spinner=False)
def get_exchange_rate():
    try:
        fx = yf.Ticker("EURUSD=X")
        return 1 / fx.history(period="1d")['Close'].iloc[-1]
    except Exception:
        return 0.92


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bulk_close(symbols_tuple, period=TABLE_HISTORY_PERIOD):
    """Bulk close prices for all symbols (cached)."""
    symbols = list(symbols_tuple)
    if not symbols:
        return pd.DataFrame()
    try:
        bulk_data = yf.download(symbols, period=period, progress=False, group_by="column")
        if bulk_data is None or bulk_data.empty:
            return pd.DataFrame()
        if len(symbols) == 1:
            close = bulk_data["Close"]
            return pd.DataFrame({symbols[0]: close}).dropna()
        return bulk_data["Close"].dropna(how="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_ticker_ohlc_history(ticker_symbol, period=DETAIL_HISTORY_PERIOD):
    """Full OHLC for Fibonacci/detail view — loaded only when needed."""
    try:
        hist = yf.Ticker(ticker_symbol).history(period=period)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.copy()
        if getattr(hist.index, "tz", None) is not None:
            hist.index = hist.index.tz_localize(None)
        return hist
    except Exception:
        return pd.DataFrame()


def _fetch_ticker_metadata_raw(ticker_symbol):
    """Single Yahoo metadata request with fallbacks."""
    est_target = 0.0
    pct_change = 0.0
    div_yield = 0.0
    ticker = yf.Ticker(ticker_symbol)
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    if info:
        pct_change = info.get("regularMarketChangePercent") or 0.0
        est_target = (
            info.get("targetMeanPrice")
            or info.get("targetMedianPrice")
            or 0.0
        )
        div_yield = extract_dividend_yield(info)

    if not est_target:
        try:
            targets = ticker.get_analyst_price_targets()
            if targets is not None and not targets.empty and "current" in targets.columns:
                if "mean" in targets.index:
                    est_target = float(targets.loc["mean", "current"])
                elif len(targets) > 0:
                    est_target = float(targets["current"].iloc[0])
        except Exception:
            pass

    return float(est_target or 0), float(pct_change or 0), float(div_yield or 0)


@st.cache_data(ttl=3600, show_spinner=False)
def get_symbol_metadata(ticker_symbol):
    """Cached metadata for one symbol (used on row/detail focus)."""
    for attempt in range(2):
        result = _fetch_ticker_metadata_raw(ticker_symbol)
        if result[0] or result[2]:
            return result
        time.sleep(0.4 * (attempt + 1))
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_portfolio_metadata_parallel(symbols_tuple):
    """Fetch analyst metadata in parallel (optional bulk load)."""
    symbols = list(symbols_tuple)
    if not symbols:
        return {}
    workers = min(4, max(1, len(symbols)))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(get_symbol_metadata, s): s for s in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception:
                results[symbol] = (0.0, 0.0, 0.0)
            time.sleep(0.15)
    return results


def apply_metadata_to_item(item, est_target, pct_change, div_yield):
    """Write analyst fields into one portfolio row."""
    price = item["data"]["🌐 Price"]
    item["data"]["Change %"] = pct_change
    item["data"]["Div Yield"] = div_yield
    item["data"]["Est Target"] = est_target
    item["data"]["Upside %"] = ((est_target / price) - 1) * 100 if est_target and price else 0.0


def enrich_symbol_metadata(all_results, symbol):
    """Load and merge analyst data for a single symbol into session results."""
    meta = get_symbol_metadata(symbol)
    for item in all_results:
        if item["data"]["Symbol"] == symbol:
            apply_metadata_to_item(item, *meta)
    if "enriched_symbols" not in st.session_state:
        st.session_state.enriched_symbols = set()
    st.session_state.enriched_symbols.add(symbol)


def start_metadata_background_load(symbols):
    """Queue analyst fields to load progressively after prices are shown."""
    symbol_list = list(dict.fromkeys(symbols))
    st.session_state.metadata_queue = symbol_list
    st.session_state.metadata_total = len(symbol_list)
    st.session_state.metadata_bg_active = bool(symbol_list)
    st.session_state.metadata_enriched = False
    st.session_state.enriched_symbols = set()
    st.session_state.pop("analyst_loaded_notice_at", None)


def prioritize_metadata_symbol(symbol):
    """Move symbol to front of background queue (e.g. on row click)."""
    if symbol in st.session_state.get("enriched_symbols", set()):
        return
    queue = list(st.session_state.get("metadata_queue", []))
    if symbol in queue:
        queue.remove(symbol)
        st.session_state.metadata_queue = [symbol] + queue
    elif st.session_state.get("metadata_bg_active"):
        st.session_state.metadata_queue = [symbol] + queue
    else:
        enrich_symbol_metadata(st.session_state.all_results, symbol)


def process_metadata_background_batch():
    """Fetch next batch of analyst data; returns True if more work remains."""
    if not st.session_state.get("metadata_bg_active"):
        return False
    queue = list(st.session_state.get("metadata_queue", []))
    if not queue:
        st.session_state.metadata_bg_active = False
        st.session_state.metadata_enriched = True
        st.session_state.analyst_loaded_notice_at = time.time()
        return False
    batch = queue[:METADATA_BATCH_SIZE]
    st.session_state.metadata_queue = queue[METADATA_BATCH_SIZE:]
    for symbol in batch:
        enrich_symbol_metadata(st.session_state.all_results, symbol)
    return bool(st.session_state.metadata_queue)


@st.fragment(run_every=METADATA_POLL_SECONDS)
def portfolio_table_live():
    """Table + background analyst loader; fragment reruns as rows fill in."""
    if "all_results" not in st.session_state or not st.session_state.all_results:
        return

    process_metadata_background_batch()

    total = st.session_state.get("metadata_total", 0)
    remaining = len(st.session_state.get("metadata_queue", []))
    done = total - remaining

    if st.session_state.get("metadata_bg_active") and total > 0:
        st.progress(min(1.0, done / total), text=f"Loading analyst data: {done}/{total}")
        next_sym = st.session_state.metadata_queue[0] if st.session_state.metadata_queue else "…"
        st.caption(f"Next: **{next_sym}** — table updates automatically.")
    elif st.session_state.get("metadata_enriched"):
        notice_at = st.session_state.get("analyst_loaded_notice_at")
        if notice_at and (time.time() - notice_at) < ANALYST_LOADED_NOTICE_SEC:
            st.caption("✓ Analyst data loaded.")

    summary_df = pd.DataFrame([x["data"] for x in st.session_state.all_results])
    view_options = list(TABLE_VIEW_COLUMNS.keys())
    tab_standard, tab_trends, tab_roi = st.tabs(view_options)
    selection_event = None
    for view_name, tab in zip(view_options, (tab_standard, tab_trends, tab_roi)):
        with tab:
            event = render_portfolio_table(summary_df, view_name)
            if event and event.selection.get("rows"):
                selection_event = event

    if selection_event and selection_event.selection.get("rows"):
        selected_row_idx = selection_event.selection["rows"][0]
        if "ticker_index" not in st.session_state or st.session_state.ticker_index != selected_row_idx:
            st.session_state.ticker_index = selected_row_idx
            st.session_state["fibo_needs_refresh"] = True
            if selected_row_idx < len(st.session_state.ticker_liste):
                prioritize_metadata_symbol(st.session_state.ticker_liste[selected_row_idx])
            st.rerun()


def build_hist_by_symbol(bulk_close, symbols):
    """Pre-index close history per symbol — no network in the row loop."""
    hist_by_symbol = {}
    for symbol in symbols:
        if bulk_close.empty or symbol not in bulk_close.columns:
            continue
        close = bulk_close[symbol].dropna()
        if not close.empty:
            hist_by_symbol[symbol] = pd.DataFrame({"Close": close})
    return hist_by_symbol


def build_portfolio_results(df_port, hist_by_symbol, eur_rate=None, metadata_map=None):
    """Build depot rows from pre-fetched prices only (no per-row API calls)."""
    results_temp = []
    total_depot_value = 0.0
    total_depot_cost = 0.0
    total_depot_target = 0.0

    for _, row in df_port.iterrows():
        symbol = row["Symbol"]
        hist = hist_by_symbol.get(symbol, pd.DataFrame())
        if hist.empty:
            continue

        price = hist["Close"].iloc[-1]
        if metadata_map and symbol in metadata_map:
            est_target, pct_change, div_yield = metadata_map[symbol]
            upside_pct = ((est_target / price) - 1) * 100 if est_target else 0.0
        else:
            est_target, div_yield, upside_pct = None, None, None
            pct_change = daily_change_pct(hist["Close"])

        cost_per_share = row["AvgCost"]
        target = row["TargetPrice"]
        if row["Currency"] == "EUR" and eur_rate:
            cost_per_share /= eur_rate
            target /= eur_rate

        current_shares = row["Shares"]
        current_val = row["Shares"] * price
        current_cost = row["Shares"] * cost_per_share
        current_target = row["Shares"] * target

        total_depot_value += current_val
        total_depot_cost += current_cost
        total_depot_target += current_target

        diff_target_abs = abs(target - price)
        diff_target_pct = abs(target - price) / price if price != 0 else 0

        purchase_date = row["PurchaseDate"]
        if pd.isna(purchase_date) or isinstance(purchase_date, str):
            try:
                purchase_date = pd.to_datetime(purchase_date)
            except Exception:
                purchase_date = None

        if purchase_date is None or pd.isna(purchase_date):
            days_held = 365
        else:
            p_date_naive = purchase_date.to_pydatetime().replace(tzinfo=None)
            days_held = max((datetime.now() - p_date_naive).days, 1)

        years_held = max(days_held / 365.25, 0.01)
        cagr = ((current_val / current_cost) ** (1 / years_held) - 1) * 100
        trends = compute_trend_returns(price, hist["Close"])

        res = {
            "Symbol": symbol,
            "🌐 Price": price,
            "Change %": pct_change,
            "Div Yield": div_yield,
            "Est Target": est_target,
            "Upside %": upside_pct,
            "Shares": current_shares,
            "Cost/Share": cost_per_share,
            "PurchaseDate": purchase_date.strftime("%Y-%m-%d")
            if purchase_date is not None and not pd.isna(purchase_date)
            else "Unknown",
            "📈 Target": target,
            "Target %": diff_target_pct * 100,
            "Target $": diff_target_abs,
            "📈 Total %": ((current_val / current_cost) - 1) * 100,
            "Total $": current_val - current_cost,
            "Ø CAGR": cagr,
        }
        res.update(trends)
        results_temp.append({"data": res, "hist": hist})

    return results_temp, total_depot_value, total_depot_cost, total_depot_target


def enrich_results_with_metadata(all_results, metadata_map):
    """Merge optional analyst fields into an already-built portfolio."""
    for item in all_results:
        symbol = item["data"]["Symbol"]
        if symbol not in metadata_map:
            continue
        apply_metadata_to_item(item, *metadata_map[symbol])
    st.session_state.enriched_symbols = set(metadata_map.keys())


def get_table_format_dict(columns):
    """Column format strings for the styled portfolio table."""
    format_dict = {col: "{:.2f}%" for col in TABLE_PERCENT_COLS if col in columns}
    if "Div Yield" in columns:
        format_dict["Div Yield"] = "{:.1f}%"
    for col in TABLE_CURRENCY_COLS:
        if col in columns:
            format_dict[col] = "{:.2f} $"
    return format_dict


def render_portfolio_table(summary_df, view_name):
    """Render one table detail view; returns the dataframe selection event."""
    cols = [c for c in TABLE_VIEW_COLUMNS[view_name] if c in summary_df.columns]
    if "Symbol" in summary_df.columns and "Symbol" not in cols:
        cols = ["Symbol"] + cols

    display_df = summary_df[cols].copy()
    format_dict = get_table_format_dict(cols)
    actual_format_dict = {k: v for k, v in format_dict.items() if k in display_df.columns}

    fill_cols = [
        c for c in TABLE_PERCENT_COLS + ["Div Yield"]
        if c in display_df.columns and c not in METADATA_COLS
    ]
    if fill_cols:
        display_df[fill_cols] = display_df[fill_cols].fillna(0)

    gradient_cols = [
        c for c in fill_cols
        if c in actual_format_dict and c not in TABLE_GRADIENT_EXCLUDE
    ] + [c for c in TABLE_PNL_COLS if c in display_df.columns]
    styled = display_df.style.format(actual_format_dict, na_rep="-").set_properties(
        **{"background-color": "white", "color": "black"}
    )
    if gradient_cols:
        styled = styled.apply(style_signed_column, subset=gradient_cols, axis=0)

    return st.dataframe(
        styled,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"portfolio_table_{view_name}",
    )


# --- CHARTING ---

def create_chart(ticker, hist, fibs, f_trends, inspect_active):
    fig = go.Figure()
    if hist is None or hist.empty:
        return fig

    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Price", line=dict(color='#1f77b4', width=2)))

    fibo_colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), fibo_colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)

    fig.update_layout(
        template="plotly_white",
        height=CHART_HEIGHT,
        margin=dict(l=12, r=12, t=8, b=8),
    )

    if inspect_active and f_trends:
        trend_colors = {"T1": "#00CC96", "T2": "#AB63FA", "T3": "#FFA15A", "T4": "#19D3F3"}
        for t in f_trends:
            width = 4 if t["id"] == "T1" else 2
            dash = "solid" if t["id"] == "T1" else "dash"

            fig.add_trace(go.Scatter(
                x=[t["f_start"], t["f_end"]],
                y=[t["price_start"], t["price_end"]],
                mode="lines+markers",
                name=f"Trend {t['id']} ({t['type']})",
                line=dict(color=trend_colors.get(t["id"], "#7f7f7f"), width=width, dash=dash),
                marker=dict(size=6, color=trend_colors.get(t["id"], "#7f7f7f")),
                hoverinfo="text",
                hovertext=f"Trend {t['id']}: {t['type']} ({t['move_pct']*100:.1f}%)"
            ))
    return fig


# --- HAUPTPROGRAMM INTERFACE ---

header_logo_col, header_title_col = st.columns([0.4, 5.6], vertical_alignment="center")
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
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

kpi_col, actions_col = st.columns([6.2, 1.3], vertical_alignment="center")

uploaded_file = None
with actions_col:
    btn_upload, btn_reset, btn_refresh = st.columns(3, gap="small")
    with btn_upload:
        with st.popover("📁", help="Upload portfolio CSV", use_container_width=True):
            uploaded_file = st.file_uploader(
                "Portfolio CSV (semicolon-separated)",
                type=["csv"],
                key=f"portfolio_upload_{st.session_state.uploader_key}",
            )
    with btn_reset:
        show_reset = uploaded_file is not None or get_cli_filename() is not None
        if show_reset and st.button(
            "❌", help="Clear upload & use default portfolio", use_container_width=True
        ):
            st.session_state.uploader_key += 1
            for key in (
                "all_results",
                "uploaded_portfolio_cache_key",
                "uploaded_portfolio_df",
                "metadata_enriched",
                "metadata_bg_active",
                "metadata_queue",
                "metadata_total",
                "enriched_symbols",
                "current_loaded_name",
                "analyst_loaded_notice_at",
            ):
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    with btn_refresh:
        refresh_clicked = st.button(
            "🔄", help="Refresh prices & analyst data", use_container_width=True
        )

df_port, current_portfolio_name = load_portfolio(uploaded_file)

if df_port is not None:
    if 'current_loaded_name' not in st.session_state or st.session_state.current_loaded_name != current_portfolio_name:
        st.session_state.current_loaded_name = current_portfolio_name
        results_temp = []
        total_depot_value = 0.0
        total_depot_cost = 0.0
        total_depot_target = 0.0    

        unique_symbols = tuple(sorted(df_port["Symbol"].unique().tolist()))
        needs_eur = (df_port["Currency"] == "EUR").any()
        eur_rate = get_exchange_rate() if needs_eur else None

        with st.spinner("Loading prices..."):
            bulk_close = fetch_bulk_close(unique_symbols, TABLE_HISTORY_PERIOD)
            hist_by_symbol = build_hist_by_symbol(bulk_close, unique_symbols)

        results_temp, total_depot_value, total_depot_cost, total_depot_target = build_portfolio_results(
            df_port, hist_by_symbol, eur_rate, metadata_map=None
        )

        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_depot_value
        st.session_state.total_depot_cost = total_depot_cost
        st.session_state.total_depot_target = total_depot_target
        st.session_state.ticker_liste = [x["data"]["Symbol"] for x in results_temp]
        st.session_state.portfolio_symbols = unique_symbols
        start_metadata_background_load(unique_symbols)

    all_results = st.session_state.all_results

    safe_filename = html.escape(str(current_portfolio_name))
    with kpi_col:
        st.markdown(
            f'<div class="kpi-strip">'
            f'<span class="kpi-item kpi-file" title="{safe_filename}">'
            f'<b>File</b> <span class="kpi-val">{safe_filename}</span></span>'
            f'<span class="kpi-item"><b>Symbols</b> <span class="kpi-val">{len(df_port):,}</span></span>'
            f'<span class="kpi-item"><b>Value</b> <span class="kpi-val">${st.session_state.total_depot_value:,.0f}</span></span>'
            f'<span class="kpi-item"><b>Cost</b> <span class="kpi-val">${st.session_state.total_depot_cost:,.0f}</span></span>'
            f'<span class="kpi-item"><b>Target</b> <span class="kpi-val">${st.session_state.total_depot_target:,.0f}</span></span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    if refresh_clicked:
        fetch_bulk_close.clear()
        get_ticker_ohlc_history.clear()
        get_exchange_rate.clear()
        get_symbol_metadata.clear()
        fetch_portfolio_metadata_parallel.clear()
        for key in (
            "all_results",
            "current_loaded_name",
            "metadata_enriched",
            "metadata_bg_active",
            "metadata_queue",
            "metadata_total",
            "enriched_symbols",
            "analyst_loaded_notice_at",
        ):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if "all_results" in st.session_state and len(st.session_state.all_results) > 0:
        portfolio_table_live()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    ticker_liste = st.session_state.get('ticker_liste', [])

    if ticker_liste:
        if 'ticker_index' not in st.session_state or st.session_state.ticker_index >= len(ticker_liste):
            st.session_state.ticker_index = 0
            st.session_state["fibo_needs_refresh"] = True

        selected_ticker = ticker_liste[st.session_state.ticker_index]
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == selected_ticker), None) 
        
        if pick:
            if selected_ticker not in st.session_state.get("enriched_symbols", set()):
                prioritize_metadata_symbol(selected_ticker)
                if selected_ticker not in st.session_state.get("enriched_symbols", set()):
                    with st.spinner(f"Loading analyst data for {selected_ticker}..."):
                        enrich_symbol_metadata(st.session_state.all_results, selected_ticker)
                pick = next(
                    (item for item in st.session_state.all_results if item["data"]["Symbol"] == selected_ticker),
                    pick,
                )

            hist_full = get_ticker_ohlc_history(selected_ticker, DETAIL_HISTORY_PERIOD)
            if hist_full.empty:
                hist_full = pick["hist"].copy()
                if getattr(hist_full.index, "tz", None) is not None:
                    hist_full.index = hist_full.index.tz_localize(None)
                if "High" not in hist_full.columns:
                    hist_full["High"] = hist_full["Close"]
                    hist_full["Low"] = hist_full["Close"]

            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]

            def ensure_month_key(key, default):
                if key not in st.session_state or st.session_state[key] not in month_options:
                    st.session_state[key] = default

            ensure_month_key("calc_fib_start", month_options[0])
            ensure_month_key("calc_fib_end", month_options[-1])
            ensure_month_key("sel_start_ui", month_options[0])
            ensure_month_key("sel_end_ui", month_options[-1])

            if st.session_state.get("fibo_needs_refresh", True):
                st.session_state["calc_fib_start"] = month_options[0]
                st.session_state["calc_fib_end"] = month_options[-1]
                st.session_state["sel_start_ui"] = month_options[0]
                st.session_state["sel_end_ui"] = month_options[-1]
                st.session_state["fibo_needs_refresh"] = False

            st.markdown(
                f'<p class="tech-header">{selected_ticker} — Technical Analysis</p>',
                unsafe_allow_html=True,
            )

            idx_start = month_options.index(st.session_state["sel_start_ui"])
            idx_end = month_options.index(st.session_state["sel_end_ui"])

            t_col_start_sel, t_col_start_btn, t_col_end_btn, t_col_end_sel, t_col_action, t_col_toggle = st.columns(
                [1.6, 0.35, 0.35, 1.6, 1.1, 1.0],
                vertical_alignment="bottom",
            )

            with t_col_start_btn:
                if st.button("⏩", help="Move start forward 3 months", use_container_width=True):
                    st.session_state["sel_start_ui"] = month_options[min(idx_start + 3, idx_end)]
                    st.rerun()
            with t_col_end_btn:
                if st.button("⏪", help="Move end back 3 months", use_container_width=True):
                    st.session_state["sel_end_ui"] = month_options[max(idx_end - 3, idx_start)]
                    st.rerun()

            with t_col_start_sel:
                st.selectbox(
                    "From",
                    options=month_options,
                    key="sel_start_ui",
                    label_visibility="collapsed",
                )
            with t_col_end_sel:
                st.selectbox(
                    "To",
                    options=month_options,
                    key="sel_end_ui",
                    label_visibility="collapsed",
                )

            st.session_state["ui_fib_start"] = st.session_state["sel_start_ui"]
            st.session_state["ui_fib_end"] = st.session_state["sel_end_ui"]

            window_changed = (
                st.session_state["sel_start_ui"] != st.session_state["calc_fib_start"]
                or st.session_state["sel_end_ui"] != st.session_state["calc_fib_end"]
            )

            with t_col_action:
                if st.button(
                    "📐 Re-Analyse",
                    disabled=not window_changed,
                    help="Recalculate Fibonacci levels and trends for the selected time window",
                    use_container_width=True,
                ):
                    st.session_state["calc_fib_start"] = st.session_state["sel_start_ui"]
                    st.session_state["calc_fib_end"] = st.session_state["sel_end_ui"]
                    st.rerun()
            with t_col_toggle:
                inspect_active = st.toggle("Trend overlay", value=True, key="fibo_trend_inspect")

            # Calc range (fixed until Re-Analyse); chart view follows UI range
            calc_mask = (hist_full.index >= pd.to_datetime(st.session_state["calc_fib_start"])) & (hist_full.index <= (pd.to_datetime(st.session_state["calc_fib_end"]) + pd.offsets.MonthEnd(0)))
            calc_hist = hist_full.loc[calc_mask]
            fib_trends = find_multiple_trends(calc_hist, max_trends=4, strong_threshold=0.05)

            h = 0 if calc_hist.empty else calc_hist['High'].max()
            l = 0 if calc_hist.empty else calc_hist['Low'].min()
            d = h - l
            
            dynamic_fibs = {
                "0% (High)": h,
                "38.2% Retracement": h - 0.382 * d,
                "50.0% Center Line": h - 0.5 * d,
                "61.8% Golden Pocket": h - 0.618 * d,
                "100% (Low Base)": l
            }

            vis_mask = (hist_full.index >= pd.to_datetime(st.session_state["ui_fib_start"])) & (
                hist_full.index <= (pd.to_datetime(st.session_state["ui_fib_end"]) + pd.offsets.MonthEnd(0))
            )
            vis_hist = hist_full.loc[vis_mask]

            if fib_trends:
                main_trend = fib_trends[0]
                main_trend_type = main_trend["type"]
                trend_cls = "trend-bull" if main_trend_type == "Bullish" else "trend-bear"
                trend_icon = get_trend_icon_html(main_trend_type)
                st.markdown(
                    f'<p class="trend-line {trend_cls}">'
                    f"{trend_icon} <b>{main_trend_type}</b> · "
                    f"{main_trend['f_start'].strftime('%Y-%m-%d')} → {main_trend['f_end'].strftime('%Y-%m-%d')} · "
                    f"{main_trend['move_pct'] * 100:+.1f}% · {len(fib_trends)} trend(s)"
                    f"</p>",
                    unsafe_allow_html=True,
                )

            chart_col, sidebar_col = st.columns([3.2, 0.8])
            with chart_col:
                st.plotly_chart(
                    create_chart(selected_ticker, vis_hist, dynamic_fibs, fib_trends, inspect_active),
                    use_container_width=True,
                )            
            
            with sidebar_col:
                curr_p = pick['data']['🌐 Price']
                
                # --- GENERIERUNG DES DOWNLOADABLE DATA-DUMPS (VARIANTE B) ---
                detected_trends_str = ""
                if fib_trends:
                    for t in fib_trends:
                        detected_trends_str += f"- {t['id']} ({t['type']}): {t['f_start'].strftime('%Y-%m-%d')} to {t['f_end'].strftime('%Y-%m-%d')} (Move: {t['move_pct']*100:.1f}%)\n"
                else:
                    detected_trends_str = "- No significant trends detected.\n"

                fib_levels_str = ""
                for label, val in dynamic_fibs.items():
                    fib_levels_str += f"- {label}: {val:.2f} $\n"

                gemini_data_dump = f"""[TECHNICAL ANALYSIS EXPORT: {selected_ticker}]
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Calculated Analysis Basis: {st.session_state['calc_fib_start']} to {st.session_state['calc_fib_end']}
Current Price: {curr_p:.2f} $
1Y Mean Target estimate: {pick['data'].get('Est Target') or 0:.2f} $ (Upside: {pick['data'].get('Upside %') or 0:.1f}%)
Purchased {pick['data']['Shares']} shares on {pick['data']['PurchaseDate']} @ {pick['data']['Cost/Share']:.2f} $

Detected Trends:
{detected_trends_str}
Fibonacci Levels:
{fib_levels_str}"""

                # Der native, hochkompakte Download-Button, der das UI-Design schont
                st.download_button(
                    label="📸 Export Dataset for Gemini",
                    data=gemini_data_dump,
                    file_name=f"gemini_analysis_{selected_ticker}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Download a compact dataset for Gemini.",
                )

                st.markdown('<p style="font-size:0.82rem;font-weight:700;margin:0.2rem 0 0.15rem 0;">Metrics</p>', unsafe_allow_html=True)
                try:
                    target = pick["data"].get("Est Target")
                    if target is None:
                        est_target, _, _ = get_symbol_metadata(selected_ticker)
                        target = est_target or 0
                        pick["data"]["Est Target"] = target
                        if target and curr_p:
                            pick["data"]["Upside %"] = ((target / curr_p) - 1) * 100
                    if target:
                        up_val = ((target / curr_p) - 1) * 100
                        chip_cls = "metric-chip" if up_val > 0 else "metric-chip down"
                        arrow = "↑" if up_val > 0 else "↓"
                        st.markdown(
                            f'<div class="{chip_cls}">Target {target:.2f} $ · {arrow} {abs(up_val):.1f}% vs {curr_p:.2f} $</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Analyst target not loaded")
                except Exception:
                    st.caption("Analyst target unavailable")

                div_y = pick["data"].get("Div Yield")
                if div_y is not None and div_y > 0:
                    st.markdown(
                        f'<div class="metric-chip div">Div yield {div_y:.1f}%</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<p style="font-size:0.82rem;font-weight:700;margin:0.25rem 0 0.1rem 0;">Fibonacci</p>', unsafe_allow_html=True)
                st.caption(f"{st.session_state['calc_fib_start']} – {st.session_state['calc_fib_end']}")
                fib_lines = []
                for label, val in dynamic_fibs.items():
                    prox = abs(curr_p - val) / val * 100
                    prefix = "🎯" if prox < 1.5 else "·"
                    fib_lines.append(f"{prefix} {label}: {val:.2f}")
                st.markdown(
                    "<span style='font-size:0.78rem;line-height:1.35'>" + "<br>".join(fib_lines) + "</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.error("Selected ticker could not be validated in session.")