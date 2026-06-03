"""Column source registry: user, market, analyst, calculated."""
from enum import Enum


class ColumnSource(str, Enum):
    USER = "user"
    MARKET = "market"
    ANALYST = "analyst"
    CALCULATED = "calculated"


# Display columns in analysis tables → source (for legends / future styling)
COLUMN_SOURCES = {
    "Symbol": ColumnSource.USER,
    "Shares": ColumnSource.USER,
    "PurchaseDate": ColumnSource.USER,
    "Cost/Share": ColumnSource.USER,
    "📈 Target": ColumnSource.USER,
    "Currency": ColumnSource.USER,
    "🌐 Price": ColumnSource.MARKET,
    "Change %": ColumnSource.MARKET,
    "5D": ColumnSource.MARKET,
    "1M": ColumnSource.MARKET,
    "6M": ColumnSource.MARKET,
    "12M": ColumnSource.MARKET,
    "Div Yield": ColumnSource.ANALYST,
    "Est Target": ColumnSource.ANALYST,
    "Upside %": ColumnSource.CALCULATED,
    "📈 Total %": ColumnSource.CALCULATED,
    "Total $": ColumnSource.CALCULATED,
    "Div Income": ColumnSource.CALCULATED,
    "Ø CAGR": ColumnSource.CALCULATED,
    "Target %": ColumnSource.CALCULATED,
    "Target $": ColumnSource.CALCULATED,
    "Value": ColumnSource.CALCULATED,
    "Invest": ColumnSource.CALCULATED,
    "📈 Target Val": ColumnSource.CALCULATED,
    "Est Target Val": ColumnSource.CALCULATED,
    "∆ Act-Target %": ColumnSource.CALCULATED,
    "∆ Act-Est Target %": ColumnSource.CALCULATED,
    "Trailing P/E": ColumnSource.ANALYST,
    "Forward P/E": ColumnSource.ANALYST,
    "PEG": ColumnSource.ANALYST,
    "Rev Growth %": ColumnSource.ANALYST,
    "Op Margin %": ColumnSource.ANALYST,
    "PEG P-Score": ColumnSource.CALCULATED,
    "Rev P-Score": ColumnSource.CALCULATED,
    "Margin P-Score": ColumnSource.CALCULATED,
    "P-Score": ColumnSource.CALCULATED,
    "Grade": ColumnSource.CALCULATED,
}

USER_EDITABLE_COLUMNS = (
    "Symbol",
    "Shares",
    "AvgCost",
    "PurchaseDate",
    "TargetPrice",
    "Currency",
)

SOURCE_LEGEND = {
    ColumnSource.USER: "Your data (editable in Edit portfolio)",
    ColumnSource.MARKET: "Live market data (yfinance)",
    ColumnSource.ANALYST: "Analyst estimates (yfinance)",
    ColumnSource.CALCULATED: "Computed from your inputs + market data",
}
