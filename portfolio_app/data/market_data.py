"""Yahoo Finance price and FX data (cached)."""
import time
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st
import yfinance as yf

from portfolio_app.analysis.returns import extract_dividend_yield, normalize_dividend_yield
from portfolio_app.config import DETAIL_HISTORY_PERIOD, TABLE_HISTORY_PERIOD


def _coerce_float(value, default=0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


@st.cache_data(ttl=300, show_spinner=False)
def get_exchange_rate():
    try:
        fx = yf.Ticker("EURUSD=X")
        return 1 / fx.history(period="1d")["Close"].iloc[-1]
    except Exception:
        return 0.92


def _close_frame_from_bulk(bulk_data, symbols: list[str]) -> pd.DataFrame:
    if bulk_data is None or bulk_data.empty:
        return pd.DataFrame()
    if len(symbols) == 1:
        close = bulk_data["Close"]
        return pd.DataFrame({symbols[0]: close}).dropna()
    if "Close" not in bulk_data.columns:
        return pd.DataFrame()
    return bulk_data["Close"].dropna(how="all")


def _fetch_close_per_symbol(symbols: list[str], period: str) -> pd.DataFrame:
    """Per-symbol history fallback when bulk yf.download fails (common on cloud hosts)."""
    series = {}
    for symbol in symbols:
        try:
            hist = yf.Ticker(symbol).history(period=period)
            if hist is None or hist.empty or "Close" not in hist.columns:
                continue
            close = hist["Close"].dropna()
            if not close.empty:
                series[symbol] = close
        except Exception:
            continue
        time.sleep(0.15)
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).dropna(how="all")


def download_close_prices(
    symbols: list[str], period: str = TABLE_HISTORY_PERIOD
) -> tuple[pd.DataFrame, str | None]:
    """
    Fetch close history for symbols.

    Returns (dataframe, error_or_warning). Tries bulk download first, then per-symbol.
    """
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
    if not symbols:
        return pd.DataFrame(), None

    bulk_error = None
    frame = pd.DataFrame()
    try:
        bulk_data = yf.download(
            symbols, period=period, progress=False, group_by="column", threads=True
        )
        frame = _close_frame_from_bulk(bulk_data, symbols)
    except Exception as exc:
        bulk_error = str(exc)

    missing = [s for s in symbols if frame.empty or s not in frame.columns]
    if not missing:
        return frame, None

    fallback = _fetch_close_per_symbol(missing, period)
    if not fallback.empty:
        if frame.empty:
            frame = fallback
        else:
            for col in fallback.columns:
                frame[col] = fallback[col]
        still_missing = [s for s in symbols if s not in frame.columns]
        if still_missing and not bulk_error:
            return frame, (
                f"Partial Yahoo fetch: no prices for {', '.join(still_missing[:6])}"
                + ("…" if len(still_missing) > 6 else "")
            )
        if still_missing:
            return frame, (
                f"Bulk download failed ({bulk_error}); per-symbol fallback missing "
                f"{len(still_missing)} symbol(s)"
            )
        if bulk_error:
            return frame, f"Bulk download failed ({bulk_error}); used per-symbol fallback"
        return frame, "Used per-symbol fallback (bulk download returned incomplete data)"

    if bulk_error:
        return pd.DataFrame(), f"Yahoo price fetch failed: {bulk_error}"
    return pd.DataFrame(), "Yahoo returned no price data (host may block yfinance bulk download)"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bulk_close(symbols_tuple, period=TABLE_HISTORY_PERIOD):
    """Bulk close prices for all symbols (cached)."""
    frame, _note = download_close_prices(list(symbols_tuple), period)
    return frame


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


def _extract_target_from_targets(targets) -> float:
    if targets is None:
        return 0.0
    # yfinance may return a dict (newer behavior) or a DataFrame (older behavior).
    if isinstance(targets, dict):
        for key in ("mean", "median", "current"):
            val = _coerce_float(targets.get(key), 0.0)
            if val > 0:
                return val
        return 0.0
    if getattr(targets, "empty", True) or "current" not in targets.columns:
        return 0.0
    try:
        if "mean" in targets.index:
            return float(targets.loc["mean", "current"])
        if "median" in targets.index:
            return float(targets.loc["median", "current"])
        if len(targets) > 0:
            return float(targets["current"].iloc[0])
    except Exception:
        return 0.0
    return 0.0


def _estimate_dividend_yield_from_history(ticker, last_price: float) -> float:
    """Fallback dividend yield from trailing 12M cash dividends / latest price."""
    if last_price <= 0:
        return 0.0
    try:
        div = ticker.dividends
        if div is None or len(div) == 0:
            return 0.0
        div = div.copy()
        cutoff = pd.Timestamp.now(tz=div.index.tz) - pd.Timedelta(days=365)
        trailing_sum = float(div[div.index >= cutoff].sum())
        if trailing_sum <= 0:
            return 0.0
        return (trailing_sum / last_price) * 100
    except Exception:
        return 0.0


def _fetch_ticker_metadata_primary(ticker_symbol):
    """
    Preferred metadata fetch path without `.info`.

    Uses fast_info + analyst targets to avoid the fragile info endpoint
    that often degrades on hosted deploy IP ranges.
    """
    est_target = 0.0
    pct_change = 0.0
    div_yield = 0.0

    ticker = yf.Ticker(ticker_symbol)
    try:
        fi = ticker.fast_info or {}
    except Exception:
        fi = {}

    # Daily change % from fast_info where available.
    last_price = _coerce_float(fi.get("lastPrice", fi.get("last_price")), 0.0)
    prev_close = _coerce_float(fi.get("previousClose", fi.get("previous_close")), 0.0)
    if last_price > 0 and prev_close > 0:
        pct_change = ((last_price / prev_close) - 1) * 100

    # Dividend yield from fast_info fields when present.
    fast_div = fi.get("dividendYield", fi.get("yearly_dividend_yield"))
    if fast_div is not None:
        div_yield = normalize_dividend_yield(fast_div)
    if div_yield <= 0 and last_price > 0:
        div_yield = _estimate_dividend_yield_from_history(ticker, last_price)

    # Analyst target estimate from dedicated endpoint.
    try:
        targets = ticker.get_analyst_price_targets()
        est_target = _extract_target_from_targets(targets)
    except Exception:
        est_target = 0.0

    return float(est_target), float(pct_change), float(div_yield)


def _fetch_ticker_metadata_raw(ticker_symbol):
    """Legacy `.info` fallback for symbols missing primary metadata."""
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
            est_target = _extract_target_from_targets(targets)
        except Exception:
            pass

    return float(est_target or 0), float(pct_change or 0), float(div_yield or 0)


@st.cache_data(ttl=3600, show_spinner=False)
def get_symbol_metadata(ticker_symbol):
    """Cached metadata for one symbol; avoid `.info` as primary source."""
    symbol = str(ticker_symbol).strip().upper()
    est_target, pct_change, div_yield = _fetch_ticker_metadata_primary(symbol)

    # Fill only missing fields from fallback (.info), keep primary pct_change.
    if not est_target or not div_yield:
        fallback = (0.0, 0.0, 0.0)
        for attempt in range(2):
            fallback = _fetch_ticker_metadata_raw(symbol)
            if fallback[0] or fallback[2]:
                break
            time.sleep(0.4 * (attempt + 1))
        if not est_target and fallback[0]:
            est_target = fallback[0]
        if not div_yield and fallback[2]:
            div_yield = fallback[2]

    return float(est_target or 0), float(pct_change or 0), float(div_yield or 0)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_portfolio_metadata_parallel(symbols_tuple):
    """Fetch analyst metadata in parallel via the `.info`-free primary path."""
    symbols = list(symbols_tuple)
    if not symbols:
        return {}
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
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
            time.sleep(0.12)
    return results


def _guess_currency(symbol: str) -> str:
    symbol = str(symbol).strip().upper()
    try:
        fi = yf.Ticker(symbol).fast_info or {}
        cur = str(fi.get("currency") or "").strip().upper()
        if cur:
            return "EUR" if cur == "EUR" else "USD"
    except Exception:
        pass
    try:
        info = yf.Ticker(symbol).info or {}
        cur = str(info.get("currency") or "").strip().upper()
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
