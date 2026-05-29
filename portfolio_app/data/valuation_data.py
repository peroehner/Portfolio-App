"""Yahoo Finance valuation ratios for Valuation Growth view."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import streamlit as st
import yfinance as yf

from portfolio_app.analysis.valuation_scores import (
    METRIC_FORWARD_PE,
    METRIC_OPERATING_MARGIN,
    METRIC_PEG,
    METRIC_REVENUE_GROWTH,
    METRIC_TRAILING_PE,
    raw_metrics_to_display,
)


def _coerce_optional_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _revenue_growth_from_financials(ticker) -> Optional[float]:
    """Year-over-year revenue growth from the two latest annual periods."""
    try:
        fin = ticker.get_financials()
        if fin is None or fin.empty:
            return None
        rev_row = None
        for label in ("Total Revenue", "Revenue", "Operating Revenue"):
            if label in fin.index:
                rev_row = fin.loc[label]
                break
        if rev_row is None:
            return None
        rev = rev_row.dropna().astype(float)
        if len(rev) < 2:
            return None
        rev = rev.sort_index(ascending=False)
        current = float(rev.iloc[0])
        prior = float(rev.iloc[1])
        if prior == 0:
            return None
        return (current - prior) / abs(prior)
    except Exception:
        return None


def _fetch_valuation_raw(symbol: str) -> dict[str, Optional[float]]:
    ticker = yf.Ticker(symbol)
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    trailing_pe = _coerce_optional_float(info.get("trailingPE"))
    forward_pe = _coerce_optional_float(info.get("forwardPE"))
    peg = _coerce_optional_float(info.get("pegRatio"))
    revenue_growth = _coerce_optional_float(info.get("revenueGrowth"))
    operating_margin = _coerce_optional_float(info.get("operatingMargins"))

    if revenue_growth is None:
        revenue_growth = _revenue_growth_from_financials(ticker)

    return {
        METRIC_TRAILING_PE: trailing_pe,
        METRIC_FORWARD_PE: forward_pe,
        METRIC_PEG: peg,
        METRIC_REVENUE_GROWTH: revenue_growth,
        METRIC_OPERATING_MARGIN: operating_margin,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_symbol_valuation(ticker_symbol: str) -> dict:
    """Cached valuation ratios for one symbol (display-ready columns)."""
    symbol = str(ticker_symbol).strip().upper()
    if not symbol:
        return raw_metrics_to_display({})
    raw = _fetch_valuation_raw(symbol)
    return raw_metrics_to_display(raw)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_portfolio_valuation_parallel(symbols_tuple: tuple) -> dict:
    """Fetch valuation metrics for all symbols in parallel."""
    symbols = [str(s).strip().upper() for s in symbols_tuple if str(s).strip()]
    if not symbols:
        return {}
    workers = min(4, max(1, len(symbols)))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(get_symbol_valuation, s): s for s in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception:
                results[symbol] = raw_metrics_to_display({})
            time.sleep(0.12)
    return results
