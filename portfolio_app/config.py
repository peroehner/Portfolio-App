"""Paths, history periods, and table column configuration."""
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "data", "pero.db")

LOGO_PATH = os.path.join(APP_DIR, "static", "myPeroLogo.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(APP_DIR, "myPeroLogo.png")

PAGE_ICON = (
    os.path.join("static", "myPeroLogo.png")
    if os.path.exists(os.path.join(APP_DIR, "static", "myPeroLogo.png"))
    else "myPeroLogo.png"
)

BULL_TREND_PATH = os.path.join(APP_DIR, "bull-trend.png")
BEAR_TREND_PATH = os.path.join(APP_DIR, "bear-trend.png")
PORTFOLIO_FILE_CANDIDATES = ("myPortfolio.csv", "Sample-Portfolio.csv")
CHART_HEIGHT = 340

TABLE_HISTORY_PERIOD = "2y"
DETAIL_HISTORY_PERIOD = "2y"
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
        "Symbol", "🌐 Price", "Change %", "Div Yield", "Est Target", "Upside %",
    ],
    "Trends": [
        "Symbol", "🌐 Price", "Change %", "5D", "1M", "6M", "12M",
    ],
    "ROI": [
        "Symbol", "🌐 Price", "Shares", "PurchaseDate", "Cost/Share", "Currency",
        "📈 Total %", "Total $", "Ø CAGR", "📈 Target", "∆ Act-Target %", "Est Target",
        "∆ Act-Est Target %",
    ],
    "Valuation Growth": [
        "Symbol", "🌐 Price", "Change %",
        "Trailing P/E", "Forward P/E", "PEG",
        "Rev Growth %", "Op Margin %",
        "PEG P-Score", "Rev P-Score", "Margin P-Score",
        "P-Score", "Grade",
    ],
}

TABLE_PERCENT_COLS = [
    "📈 Total %", "Change %", "Upside %", "Ø CAGR", "Target %", "∆ Act-Target %",
    "∆ Act-Est Target %",
    "5D", "1M", "6M", "12M",
    "Rev Growth %", "Op Margin %",
]
TABLE_CURRENCY_COLS = [
    "📈 Target", "Target $", "Total $", "Est Target", "Cost/Share", "🌐 Price",
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
