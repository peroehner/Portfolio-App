"""Build portfolio table rows from pre-fetched price history."""
import pandas as pd

from portfolio_app.analysis.returns import (
    compute_position_cagr,
    compute_trend_returns,
    daily_change_pct,
    holding_days_since_purchase,
)
from portfolio_app.analysis.valuation_scores import VALUATION_ALL_COLUMNS


def build_hist_by_symbol(bulk_close, symbols):
    """Pre-index close history per symbol — no network in the row loop."""
    hist_by_symbol = {}
    for symbol in symbols:
        if bulk_close.empty or symbol not in bulk_close.columns:
            continue
        close = bulk_close[symbol].dropna()
        if not close.empty:
            hist_by_symbol[symbol] = pd.DataFrame({"Close": close})
    return hist_by_symbol


def build_portfolio_results(df_port, hist_by_symbol, eur_rate=None, metadata_map=None):
    """Build depot rows from pre-fetched prices only (no per-row API calls)."""
    results_temp = []
    total_depot_value = 0.0
    total_depot_cost = 0.0
    total_depot_target = 0.0

    for _, row in df_port.iterrows():
        symbol = row["Symbol"]
        hist = hist_by_symbol.get(symbol, pd.DataFrame())
        has_price = not hist.empty

        if has_price:
            price = float(hist["Close"].iloc[-1])
            if metadata_map and symbol in metadata_map:
                est_target, pct_change, div_yield = metadata_map[symbol]
                upside_pct = ((est_target / price) - 1) * 100 if est_target else 0.0
            else:
                est_target, div_yield, upside_pct = None, None, None
                pct_change = daily_change_pct(hist["Close"])
        else:
            price = None
            est_target, pct_change, div_yield, upside_pct = None, None, None, None

        cost_per_share = row["AvgCost"]
        target = row["TargetPrice"]
        if row["Currency"] == "EUR" and eur_rate:
            cost_per_share /= eur_rate
            target /= eur_rate

        purchase_date = row["PurchaseDate"]
        if pd.isna(purchase_date) or isinstance(purchase_date, str):
            try:
                purchase_date = pd.to_datetime(purchase_date)
            except Exception:
                purchase_date = None

        days_held = holding_days_since_purchase(purchase_date)

        current_shares = row["Shares"]
        current_cost = row["Shares"] * cost_per_share
        current_target = row["Shares"] * target
        total_depot_cost += current_cost
        total_depot_target += current_target

        if has_price and price:
            current_val = row["Shares"] * price
            total_depot_value += current_val
            diff_target_abs = abs(target - price)
            diff_target_pct = abs(target - price) / price if price != 0 else 0
            act_target_delta_pct = ((price - target) / price * 100) if price != 0 else 0.0
            if est_target is not None and est_target:
                act_est_target_delta_pct = ((price - est_target) / price * 100)
            else:
                act_est_target_delta_pct = None
            total_pct = ((current_val / current_cost) - 1) * 100 if current_cost else None
            total_dollar = current_val - current_cost
            cagr = compute_position_cagr(current_val, current_cost, days_held)
            trends = compute_trend_returns(price, hist["Close"])
        else:
            diff_target_abs = None
            diff_target_pct = None
            act_target_delta_pct = None
            act_est_target_delta_pct = None
            total_pct = None
            total_dollar = None
            cagr = None
            trends = {"5D": None, "1M": None, "6M": None, "12M": None}

        res = {
            "Symbol": symbol,
            "🌐 Price": price,
            "Change %": pct_change,
            "Div Yield": div_yield,
            "Est Target": est_target,
            "Upside %": upside_pct,
            "Shares": current_shares,
            "Cost/Share": cost_per_share,
            "PurchaseDate": purchase_date.strftime("%Y-%m-%d")
            if purchase_date is not None and not pd.isna(purchase_date)
            else "Unknown",
            "📈 Target": target,
            "∆ Act-Target %": act_target_delta_pct,
            "∆ Act-Est Target %": act_est_target_delta_pct,
            "Target %": (diff_target_pct * 100) if diff_target_pct is not None else None,
            "Target $": diff_target_abs,
            "📈 Total %": total_pct,
            "Total $": total_dollar,
            "Ø CAGR": cagr,
        }
        res.update(trends)
        for col in VALUATION_ALL_COLUMNS:
            res[col] = None
        results_temp.append({"data": res, "hist": hist})

    return results_temp, total_depot_value, total_depot_cost, total_depot_target
