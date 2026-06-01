"""Holdings edit helpers: draft state, validation, display ↔ DB mapping."""
from datetime import date

import pandas as pd
import streamlit as st

from portfolio_app.data.market_data import get_exchange_rate, validate_symbol
from portfolio_app.services.session_context import (
    get_portfolio_service,
    invalidate_analysis,
    load_active_portfolio,
    set_active_portfolio_id,
)

ROI_EDITABLE_COLUMNS = (
    "Symbol",
    "Shares",
    "PurchaseDate",
    "Cost/Share",
    "📈 Target",
)


def _draft_key(portfolio_id: int) -> str:
    return f"holdings_draft_{portfolio_id}"


def clear_holdings_draft(portfolio_id: int):
    st.session_state.pop(_draft_key(portfolio_id), None)
    st.session_state.pop("portfolio_table", None)
    st.session_state.pop("portfolio_grid", None)
    st.session_state.pop("portfolio_table_roi_editor", None)


def set_holdings_draft(portfolio_id: int, df: pd.DataFrame):
    st.session_state[_draft_key(portfolio_id)] = df.copy()


def get_editable_holdings_df() -> pd.DataFrame:
    """Holdings used for analysis load (draft overrides DB until saved)."""
    active = load_active_portfolio()
    draft = st.session_state.get(_draft_key(active.portfolio_id))
    if draft is not None:
        return draft.copy()
    return active.holdings_df.copy()


def holdings_to_roi_display_df(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Minimal ROI-shaped frame from raw holdings when analysis rows are not ready yet."""
    if holdings_df.empty:
        return pd.DataFrame()
    needs_eur = (holdings_df["Currency"] == "EUR").any()
    eur_rate = get_exchange_rate() if needs_eur else None
    rows = []
    for _, row in holdings_df.iterrows():
        cost = float(row["AvgCost"])
        target = float(row["TargetPrice"])
        if str(row.get("Currency", "USD")).upper() == "EUR" and eur_rate:
            cost /= eur_rate
            target /= eur_rate
        purchase = row.get("PurchaseDate")
        if pd.isna(purchase):
            purchase_label = "Unknown"
        else:
            purchase_label = pd.to_datetime(purchase).strftime("%Y-%m-%d")
        rows.append({
            "Symbol": row["Symbol"],
            "🌐 Price": None,
            "Shares": row["Shares"],
            "PurchaseDate": purchase_label,
            "Cost/Share": cost,
            "📈 Total %": None,
            "Total $": None,
            "Div Income": None,
            "Ø CAGR": None,
            "📈 Target": target,
            "∆ Act-Target %": None,
            "Est Target": None,
            "∆ Act-Est Target %": None,
        })
    return pd.DataFrame(rows)


def enrich_summary_with_currency(summary_df: pd.DataFrame, holdings_df: pd.DataFrame) -> pd.DataFrame:
    out = summary_df.copy()
    currency_map = (
        holdings_df.set_index("Symbol")["Currency"].astype(str).str.upper().to_dict()
        if not holdings_df.empty
        else {}
    )
    out["Currency"] = out["Symbol"].map(lambda s: currency_map.get(s, "USD"))
    return out


def prepare_roi_editor_df(display_df: pd.DataFrame) -> pd.DataFrame:
    df = display_df.copy()
    if "PurchaseDate" in df.columns:
        df["PurchaseDate"] = df["PurchaseDate"].replace("Unknown", pd.NaT)
        df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
    for col in ("Shares", "Cost/Share", "📈 Target"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _parse_required_float(value, *, field_label: str, symbol: str) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"{symbol}: {field_label} is required — enter a number in the table.")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{symbol}: {field_label} must be a number.") from exc
    if num < 0:
        raise ValueError(f"{symbol}: {field_label} cannot be negative.")
    return num


def validate_roi_editor_df(edited_df: pd.DataFrame) -> list[str]:
    """Validate ROI table rows while editing; returns human-readable issues per symbol."""
    if edited_df is None or edited_df.empty:
        return ["Add at least one symbol row with Symbol, Shares, Cost/Share, and Target."]

    def _normalized_symbol(value) -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        symbol = str(value).strip().upper()
        return "" if symbol in {"", "NONE", "NAN"} else symbol

    errors = []
    for idx, row in edited_df.iterrows():
        symbol = _normalized_symbol(row.get("Symbol"))
        if not symbol:
            # Empty symbol rows are treated as deletions on save.
            continue

        for col, label in (
            ("Shares", "Shares"),
            ("Cost/Share", "Cost/Share"),
            ("📈 Target", "Target"),
        ):
            if col not in edited_df.columns:
                continue
            val = row.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                errors.append(f"{symbol}: {label} is required — enter a number.")
                continue
            try:
                num = float(val)
            except (TypeError, ValueError):
                errors.append(f"{symbol}: {label} must be a number.")
                continue
            if num < 0:
                errors.append(f"{symbol}: {label} cannot be negative.")

        purchase = row.get("PurchaseDate")
        if purchase is not None and not (isinstance(purchase, float) and pd.isna(purchase)):
            try:
                pdt = pd.to_datetime(purchase)
                if pdt > pd.Timestamp.now().normalize() + pd.Timedelta(days=1):
                    errors.append(
                        f"{symbol}: Purchase date cannot be in the future (needed for CAGR)."
                    )
            except Exception:
                pass

    symbols = [_normalized_symbol(s) for s in edited_df["Symbol"].tolist()]
    symbols = [s for s in symbols if s]
    dupes = {s for s in symbols if symbols.count(s) > 1}
    for sym in sorted(dupes):
        errors.append(f"{sym}: duplicate symbol — keep one row per ticker.")

    return errors


def merge_holdings_into_roi_display(
    display_df: pd.DataFrame, holdings_df: pd.DataFrame
) -> pd.DataFrame:
    """Append draft-only symbols (e.g. newly added) so they appear in the ROI editor."""
    if holdings_df is None or holdings_df.empty:
        return display_df
    present = set(display_df["Symbol"].astype(str).str.upper())
    extra_mask = ~holdings_df["Symbol"].astype(str).str.upper().isin(present)
    extra = holdings_df.loc[extra_mask]
    if extra.empty:
        return display_df
    extra_display = prepare_roi_editor_df(holdings_to_roi_display_df(extra))
    for col in display_df.columns:
        if col not in extra_display.columns:
            extra_display[col] = None
    extra_display = extra_display[list(display_df.columns)]
    return pd.concat([display_df, extra_display], ignore_index=True)


def display_df_to_holdings(edited_df: pd.DataFrame) -> pd.DataFrame:
    """Map ROI table columns back to SQLite holdings schema (USD values from ROI view)."""
    rows = []
    for _, row in edited_df.iterrows():
        symbol = str(row["Symbol"]).strip().upper()
        if not symbol:
            continue

        shares = _parse_required_float(row.get("Shares"), field_label="Shares", symbol=symbol)
        avg_cost = _parse_required_float(
            row.get("Cost/Share"), field_label="Cost/Share", symbol=symbol
        )
        target = _parse_required_float(
            row.get("📈 Target"), field_label="Target", symbol=symbol
        )

        purchase = row.get("PurchaseDate")
        if purchase is None or (isinstance(purchase, float) and pd.isna(purchase)):
            purchase_dt = None
        elif purchase == "Unknown":
            purchase_dt = None
        else:
            purchase_dt = pd.to_datetime(purchase, errors="coerce")
            if pd.isna(purchase_dt):
                purchase_dt = None

        rows.append({
            "Symbol": symbol,
            "Shares": shares,
            "AvgCost": avg_cost,
            "PurchaseDate": purchase_dt,
            "TargetPrice": target,
            "Currency": "USD",
        })

    if not rows:
        raise ValueError("Portfolio must contain at least one position.")
    return pd.DataFrame(rows)


def validate_holdings_symbols(df: pd.DataFrame):
    for sym in df["Symbol"].astype(str).str.strip().str.upper().unique():
        if not sym:
            continue
        valid, _, _ = validate_symbol(sym)
        if not valid:
            raise ValueError(
                f'"{sym}" was not found on Yahoo Finance. Remove it or fix the ticker.'
            )


def append_symbol_to_draft(portfolio_id: int, holdings_df: pd.DataFrame, symbol: str, currency: str) -> pd.DataFrame:
    symbol = symbol.strip().upper()
    if symbol in holdings_df["Symbol"].astype(str).str.upper().values:
        raise ValueError(f"{symbol} is already in your portfolio.")
    new_row = pd.DataFrame([{
        "Symbol": symbol,
        "Shares": 0.0,
        "AvgCost": 0.0,
        "PurchaseDate": pd.Timestamp(date.today()),
        "TargetPrice": 0.0,
        "Currency": currency,
    }])
    return pd.concat([holdings_df, new_row], ignore_index=True)


def save_holdings_from_df(portfolio_id: int, holdings_df: pd.DataFrame):
    with st.spinner("Validating symbols…"):
        validate_holdings_symbols(holdings_df)
    svc = get_portfolio_service()
    active = svc.save_holdings(portfolio_id, holdings_df)
    clear_holdings_draft(portfolio_id)
    set_active_portfolio_id(active.portfolio_id)
    svc.remember_last_portfolio(active.user_id, active.portfolio_id)
    invalidate_analysis(refetch_metadata=False)
