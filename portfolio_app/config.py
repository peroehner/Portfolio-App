"""Paths, history periods, and table column configuration."""
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Override with PERO_DB_PATH to use a dedicated DB per host (deploy vs local).
DB_PATH = os.environ.get("PERO_DB_PATH") or os.path.join(APP_DIR, "data", "pero.db")

LOGO_PATH = os.path.join(APP_DIR, "static", "compass-logo.png")

PAGE_ICON = (
    os.path.join("static", "compass-icon.png")
    if os.path.exists(os.path.join(APP_DIR, "static", "compass-icon.png"))
    else os.path.join("static", "compass-logo.png")
)

BULL_TREND_PATH = os.path.join(APP_DIR, "bull-trend.png")
BEAR_TREND_PATH = os.path.join(APP_DIR, "bear-trend.png")
PORTFOLIO_FILE_CANDIDATES = ("myPortfolio.csv", "Sample-Portfolio.csv")
CHART_HEIGHT = 340

TABLE_HISTORY_PERIOD = "2y"  # legacy fallback when history_months is unset
DETAIL_HISTORY_PERIOD = "2y"
# Global price-history window (sync + Trends + TA). Slider max = this many months.
HISTORY_MONTHS_MAX = 24
HISTORY_MONTHS_DEFAULT = 12
HISTORY_MONTHS_MIN = 1
# Persisted fetch preference (survives ⋮ panel close / slider unmount).
HISTORY_MONTHS_PERSIST_KEY = "_history_months_persist"
# Streamlit slider widget key only — never use for Yahoo fetch directly.
HISTORY_MONTHS_WIDGET_KEY = "history_months_slider"
# Months used for the last successful network sync (session).
SYNCED_HISTORY_MONTHS_KEY = "_synced_history_months"
# Backward-compatible aliases
DETAIL_HISTORY_MAX_MONTHS = HISTORY_MONTHS_MAX
TA_HISTORY_MONTHS_DEFAULT = HISTORY_MONTHS_DEFAULT
TA_HISTORY_MONTHS_MIN = HISTORY_MONTHS_MIN
TA_HISTORY_MONTHS_PERSIST_KEY = HISTORY_MONTHS_PERSIST_KEY
TA_HISTORY_MONTHS_WIDGET_KEY = HISTORY_MONTHS_WIDGET_KEY
METADATA_BATCH_SIZE = 2
METADATA_POLL_SECONDS = 1.5
ANALYST_LOADED_NOTICE_SEC = 3

METADATA_COLS = {"Div Yield", "Est Target", "Upside %"}
# Analyst-dependent; keep NaN as "-" until metadata loads (still use signed gradient)
METADATA_LATE_COLS = {"∆ Act-Est Target %"}

VALUATION_COLS = {
    "Trailing P/E", "Forward P/E", "PEG", "Rev Growth %", "Op Margin %",
    "PEG P-Score", "Rev P-Score", "Margin P-Score", "P-Score", "Grade",
}
VALUATION_LATE_COLS = {
    "PEG P-Score", "Rev P-Score", "Margin P-Score", "P-Score", "Grade",
}

TABLE_VIEW_COLUMNS = {
    "Standard": [
        "Symbol", "🌐 Price", "Change %", "Cost/Share",
        "Div Yield", "Est Target", "Upside %", "PurchaseDate",
    ],
    "ROI": [
        "Symbol", "🌐 Price", "Cost/Share", "📈 Target", "Est Target", "Div Income",
        "Shares", "Value", "Ø CAGR", "Invest", "📈 Target Val", "∆ Act-Target %",
        "Est Target Val", "∆ Act-Est Target %",
    ],
    "Trends": [
        "Symbol", "🌐 Price", "Change %", "5D", "1M", "6M", "12M",
    ],
    "Valuation Growth": [
        "Symbol", "🌐 Price", "Change %",
        "Trailing P/E", "Forward P/E", "PEG",
        "Rev Growth %", "Op Margin %",
        "PEG P-Score", "Rev P-Score", "Margin P-Score",
        "P-Score", "Grade",
    ],
}

# ROI pinned footer — sum these $ columns; Δ Tgt% / Δ Est% are derived from totals (see table.py)
ROI_FOOTER_SUM_COLUMNS = (
    "Div Income",
    "Invest",
    "Value",
    "📈 Target Val",
    "Est Target Val",
)

TABLE_PERCENT_COLS = [
    "📈 Total %", "Change %", "Upside %", "Ø CAGR", "Target %", "∆ Act-Target %",
    "∆ Act-Est Target %",
    "5D", "1M", "6M", "12M",
    "Rev Growth %", "Op Margin %",
]
TABLE_CURRENCY_COLS = [
    "📈 Target", "Target $", "Total $", "Est Target", "Cost/Share", "🌐 Price", "Div Income",
    "Value", "Invest", "📈 Target Val", "Est Target Val",
]
TABLE_PNL_COLS = ["Total $"]
TABLE_GRADIENT_EXCLUDE = {"Div Yield"}

# Streamlit NumberColumn printf formats (US: $ prefix, % suffix, dot decimals)
TABLE_NUMBER_COLUMN_FORMAT = {
    "🌐 Price": "$%.2f",
    "Shares": "%.2f",
    "Cost/Share": "$%.2f",
    "📈 Target": "$%.2f",
    "Target $": "$%.2f",
    "Total $": "$%.2f",
    "Est Target": "$%.2f",
    "📈 Total %": "%.2f%%",
    "Change %": "%.2f%%",
    "Upside %": "%.2f%%",
    "Ø CAGR": "%.2f%%",
    "Target %": "%.2f%%",
    "∆ Act-Target %": "%.2f%%",
    "∆ Act-Est Target %": "%.2f%%",
    "Div Yield": "%.1f%%",
    "Div Income": "$%.2f",
    "Value": "$%.2f",
    "Invest": "$%.2f",
    "📈 Target Val": "$%.2f",
    "Est Target Val": "$%.2f",
    "5D": "%.2f%%",
    "1M": "%.2f%%",
    "6M": "%.2f%%",
    "12M": "%.2f%%",
    "Rev Growth %": "%.1f%%",
    "Op Margin %": "%.1f%%",
    "Trailing P/E": "%.2f",
    "Forward P/E": "%.2f",
    "PEG": "%.2f",
    "PEG P-Score": "%.0f",
    "Rev P-Score": "%.0f",
    "Margin P-Score": "%.0f",
    "P-Score": "%.1f",
}

_COLOR_POSITIVE = (19, 115, 51)
_COLOR_NEGATIVE = (197, 34, 31)
