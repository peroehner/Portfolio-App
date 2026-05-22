"""Swing-based trend leg detection."""
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


def find_multiple_trends(df, max_trends=4, strong_threshold=0.05, order=10):
    """Find significant trends via local swing highs and lows."""
    trends = []
    if df is None or df.empty or "Close" not in df.columns:
        return trends

    prices = df["Close"].values
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
        idx_end = all_extrema[i + 1]

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
                "type": "Bullish" if p_start < p_end else "Bearish",
            })

    sorted_legs = sorted(raw_legs, key=lambda x: x["move_pct"], reverse=True)

    for idx, leg in enumerate(sorted_legs[:max_trends]):
        leg["id"] = f"T{idx + 1}"
        trends.append(leg)

    return trends
