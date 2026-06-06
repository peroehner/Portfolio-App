"""Technical analysis text export for selected symbols."""
from datetime import datetime

import pandas as pd

from portfolio_app.analysis.fibonacci import (
    compute_fibonacci_levels,
    normalize_ohlc_hist,
    slice_hist_to_window,
)
from portfolio_app.analysis.trends import find_multiple_trends
from portfolio_app.config import DETAIL_HISTORY_PERIOD
from portfolio_app.data.market_data import get_ticker_ohlc_history


def _fmt_num(value, decimals=2, suffix=""):
    try:
        if value is None or pd.isna(value):
            return "-"
        return f"{float(value):.{decimals}f}{suffix}"
    except Exception:
        return "-"


def build_symbol_export_block(symbol, window_start, window_end, all_results):
    pick = next((item for item in all_results if item["data"]["Symbol"] == symbol), None)
    if not pick:
        return ""
    hist_full = normalize_ohlc_hist(get_ticker_ohlc_history(symbol, DETAIL_HISTORY_PERIOD))
    if hist_full.empty:
        hist_full = normalize_ohlc_hist(pick["hist"])
    if hist_full.empty:
        return f"[TECHNICAL ANALYSIS EXPORT: {symbol}]\nNo price history available.\n"

    calc_hist = slice_hist_to_window(hist_full, window_start, window_end)
    fib_trends = find_multiple_trends(calc_hist, max_trends=4, strong_threshold=0.05)
    main_trend = fib_trends[0] if fib_trends else None
    dynamic_fibs, fib_anchor = compute_fibonacci_levels(calc_hist, main_trend)
    curr_p = pick["data"]["🌐 Price"]
    personal_target = pick["data"].get("📈 Target")
    try:
        personal_upside = (
            ((float(personal_target) / float(curr_p)) - 1) * 100
            if personal_target is not None
            and curr_p not in (None, 0)
            and not pd.isna(personal_target)
            and not pd.isna(curr_p)
            else None
        )
    except (TypeError, ValueError):
        personal_upside = None

    if fib_trends:
        detected_trends_str = "".join(
            f"- {t['id']} ({t['type']}): {t['f_start'].strftime('%Y-%m-%d')} to "
            f"{t['f_end'].strftime('%Y-%m-%d')} (Move: {t['move_pct'] * 100:.1f}%)\n"
            for t in fib_trends
        )
    else:
        detected_trends_str = "- No significant trends detected.\n"

    fib_levels_str = "".join(
        f"- {label}: {_fmt_num(val, 2)} $\n" for label, val in dynamic_fibs.items()
    )

    div_income = pick["data"].get("Div Income")
    if div_income is None or (isinstance(div_income, float) and pd.isna(div_income)):
        div_income_line = "Estimate annual dividend income: —"
    else:
        div_income_line = f"Estimate annual dividend income: {float(div_income):,.2f} $"

    trailing_pe = _fmt_num(pick["data"].get("Trailing P/E"), 2)
    forward_pe = _fmt_num(pick["data"].get("Forward P/E"), 2)
    peg = _fmt_num(pick["data"].get("PEG"), 2)
    rev_growth = _fmt_num(pick["data"].get("Rev Growth %"), 1, "%")
    op_margin = _fmt_num(pick["data"].get("Op Margin %"), 1, "%")
    p_score = _fmt_num(pick["data"].get("P-Score"), 1)
    p_grade = pick["data"].get("Grade") or "-"
    shares = pick["data"].get("Shares")
    purchase = pick["data"].get("PurchaseDate") or "-"

    return f"""[TECHNICAL ANALYSIS EXPORT: {symbol}]
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis window: {window_start} to {window_end}
Fibonacci anchor: {fib_anchor}
Current Price: {_fmt_num(curr_p, 2)} $
Personal Target: {_fmt_num(personal_target, 2)} $ (Upside: {_fmt_num(personal_upside, 1, '%')})
1Y Mean Target estimate: {_fmt_num(pick['data'].get('Est Target'), 2)} $ (Upside: {_fmt_num(pick['data'].get('Upside %'), 1, '%')})
Purchased {_fmt_num(shares, 2)} shares on {purchase} @ {_fmt_num(pick['data'].get('Cost/Share'), 2)} $
{div_income_line}

Valuation Growth:
- Trailing P/E: {trailing_pe}
- Forward P/E: {forward_pe}
- PEG: {peg}
- Rev Growth: {rev_growth}
- Op Margin: {op_margin}
- P-Score (private portfolio): {p_score}
- Grade (private portfolio): {p_grade}

Detected Trends:
{detected_trends_str}
Fibonacci Levels:
{fib_levels_str}"""


def build_multi_export_datasets(symbols, window_start, window_end, all_results):
    blocks = [
        build_symbol_export_block(symbol, window_start, window_end, all_results)
        for symbol in symbols
    ]
    blocks = [b for b in blocks if b]
    header = (
        f"[PORTFOLIO EXPORT — {len(blocks)} symbol(s)]\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Time window: {window_start} → {window_end}\n"
        f"Symbols: {', '.join(symbols)}\n"
    )
    return header + ("\n" + ("=" * 72) + "\n\n").join(blocks)
