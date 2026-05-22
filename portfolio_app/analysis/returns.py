"""Price returns and dividend yield helpers."""
import pandas as pd

from portfolio_app.config import METADATA_COLS  # noqa: F401 — re-export for callers

__all__ = [
    "METADATA_COLS",
    "compute_trend_returns",
    "daily_change_pct",
    "extract_dividend_yield",
    "normalize_dividend_yield",
    "period_return",
]


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
    if div < 0.2:
        return div * 100
    return div


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
