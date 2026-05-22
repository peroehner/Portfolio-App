"""Fibonacci retracement levels and OHLC window helpers."""
import pandas as pd


def normalize_ohlc_hist(hist):
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.copy()
    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    if "High" not in hist.columns:
        hist["High"] = hist["Close"]
        hist["Low"] = hist["Close"]
    return hist


def compute_fibonacci_levels(calc_hist, main_trend=None):
    """Retracements from leg high→low; anchored to main trend (T1) when available."""
    anchor_note = "window high/low (no significant trend)"
    h = l = 0.0

    if calc_hist is not None and not calc_hist.empty:
        if main_trend:
            leg_mask = (calc_hist.index >= pd.to_datetime(main_trend["f_start"])) & (
                calc_hist.index <= pd.to_datetime(main_trend["f_end"])
            )
            leg_hist = calc_hist.loc[leg_mask]
            if not leg_hist.empty:
                h = float(leg_hist["High"].max())
                l = float(leg_hist["Low"].min())
            else:
                h = float(max(main_trend["price_start"], main_trend["price_end"]))
                l = float(min(main_trend["price_start"], main_trend["price_end"]))
            anchor_note = (
                f"{main_trend.get('id', 'T1')} {main_trend['type']}: "
                f"{main_trend['f_start'].strftime('%Y-%m-%d')} → "
                f"{main_trend['f_end'].strftime('%Y-%m-%d')}"
            )
        else:
            h = float(calc_hist["High"].max())
            l = float(calc_hist["Low"].min())

    d = max(h - l, 0.0)
    levels = {
        "0% (High)": h,
        "38.2% Retracement": h - 0.382 * d,
        "50.0% Center Line": h - 0.5 * d,
        "61.8% Golden Pocket": h - 0.618 * d,
        "100% (Low Base)": l,
    }
    return levels, anchor_note


def slice_hist_to_window(hist, window_start, window_end):
    mask = (hist.index >= pd.to_datetime(window_start)) & (
        hist.index <= (pd.to_datetime(window_end) + pd.offsets.MonthEnd(0))
    )
    return hist.loc[mask]
