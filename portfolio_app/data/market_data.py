"""Yahoo Finance price and FX data (cached)."""
import time
from typing import Optional, Tuple

import pandas as pd
import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

from portfolio_app.analysis.returns import extract_dividend_yield
from portfolio_app.config import DETAIL_HISTORY_PERIOD, TABLE_HISTORY_PERIOD


@st.cache_data(ttl=300, show_spinner=False)
def get_exchange_rate():
    try:
        fx = yf.Ticker("EURUSD=X")
        return 1 / fx.history(period="1d")["Close"].iloc[-1]
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


def _guess_currency(symbol: str) -> str:
    try:
        info = yf.Ticker(symbol).info or {}
        cur = str(info.get("currency") or "USD").strip().upper()
        return "EUR" if cur == "EUR" else "USD"
    except Exception:
        return "USD"


@st.cache_data(ttl=86400, show_spinner=False)
def validate_symbol(ticker_symbol: str) -> Tuple[bool, str, Optional[str]]:
    """
    Check that Yahoo Finance has price history for this ticker.

    Returns (valid, normalized_symbol, currency_hint).
    """
    symbol = str(ticker_symbol).strip().upper()
    if not symbol or len(symbol) > 12:
        return False, symbol, None
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return False, symbol, None
        close = hist["Close"].dropna()
        if close.empty or float(close.iloc[-1]) <= 0:
            return False, symbol, None
        return True, symbol, _guess_currency(symbol)
    except Exception:
        return False, symbol, None
