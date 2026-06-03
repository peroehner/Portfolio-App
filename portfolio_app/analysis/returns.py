"""Price returns and dividend yield helpers."""
import math
from datetime import datetime

import pandas as pd

from portfolio_app.config import METADATA_COLS  # noqa: F401 — re-export for callers

MIN_DAYS_FOR_CAGR = 30
MAX_CAGR_MAGNITUDE = 9_999.99

__all__ = [
    "METADATA_COLS",
    "MIN_DAYS_FOR_CAGR",
    "compute_annual_div_income",
    "compute_position_cagr",
    "compute_trend_returns",
    "daily_change_pct",
    "extract_dividend_yield",
    "holding_days_since_purchase",
    "normalize_dividend_yield",
    "period_return",
    "value_to_target_gap_pct",
]


def normalize_dividend_yield(div_yield):
    """Convert fractional yield to percent (0.02 → 2.0)."""
    if div_yield is None or div_yield == 0:
        return 0.0
    div_yield = float(div_yield)
    if div_yield < 1:
        return div_yield * 100
    return div_yield


def compute_annual_div_income(shares, price, div_yield_pct) -> float | None:
    """
    Estimated annual dividend income (USD): shares × price × (div yield % / 100).
    """
    if shares is None or price is None or div_yield_pct is None:
        return None
    try:
        s = float(shares)
        p = float(price)
        y = float(div_yield_pct)
    except (TypeError, ValueError):
        return None
    if s <= 0 or p <= 0 or y <= 0:
        return None
    if not all(math.isfinite(v) for v in (s, p, y)):
        return None
    return s * p * (y / 100.0)


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


def holding_days_since_purchase(purchase_date, *, now=None) -> int | None:
    """Calendar days since purchase; None if unknown or purchase date is in the future."""
    if purchase_date is None or (isinstance(purchase_date, float) and pd.isna(purchase_date)):
        return None
    try:
        purchased = pd.to_datetime(purchase_date).to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None
    if now is None:
        now = datetime.now()
    days = (now - purchased).days
    if days < 0:
        return None
    return days


def compute_position_cagr(
    current_val: float,
    current_cost: float,
    days_held: int | None,
) -> float | None:
    """
    Annualized return (CAGR) from cost basis to current value.
    Returns None when the holding period is too short or inputs are invalid
    (avoids absurd values from near-zero years_held).
    """
    if not current_cost or current_cost <= 0 or current_val is None:
        return None
    if days_held is None or days_held < MIN_DAYS_FOR_CAGR:
        return None

    years_held = days_held / 365.25
    ratio = current_val / current_cost
    if ratio <= 0:
        return None

    try:
        cagr = (ratio ** (1 / years_held) - 1) * 100
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(cagr) or abs(cagr) > MAX_CAGR_MAGNITUDE:
        return None
    return round(cagr, 2)


def value_to_target_gap_pct(value, target) -> float | None:
    """
    Gap from current value toward a target price, as % of value.

    Positive when value is below target (still below goal); negative when above.
    """
    if value is None or target is None:
        return None
    try:
        v = float(value)
        t = float(target)
    except (TypeError, ValueError):
        return None
    if v <= 0 or pd.isna(v) or pd.isna(t):
        return None
    return (t - v) / v * 100.0


def daily_change_pct(close_series):
    """Approximate daily change from last two closes (no Yahoo info call)."""
    if len(close_series) < 2:
        return 0.0
    prev = close_series.iloc[-2]
    if prev == 0 or pd.isna(prev):
        return 0.0
    return ((close_series.iloc[-1] / prev) - 1) * 100
