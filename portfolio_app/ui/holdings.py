"""Holdings edit helpers: draft state, validation, display ↔ DB mapping."""
from datetime import date

import pandas as pd
import streamlit as st

from portfolio_app.data.market_data import get_exchange_rate, validate_symbol
from portfolio_app.data.portfolio_loader import merge_duplicate_symbol_rows, parse_shares_number
from portfolio_app.domain.columns import USER_EDITABLE_COLUMNS
from portfolio_app.services.session_context import (
    get_portfolio_service,
    invalidate_analysis,
    load_active_portfolio,
    set_active_portfolio_id,
)

HOLDINGS_EDITOR_COLUMNS = USER_EDITABLE_COLUMNS

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
    from portfolio_app.session_keys import clear_portfolio_table_widget
    from portfolio_app.ui.table import clear_edit_portfolio_expander_state

    clear_portfolio_table_widget()
    st.session_state.pop("portfolio_table_roi_editor", None)
    bump_holdings_editor_generation(portfolio_id)
    clear_edit_portfolio_expander_state(portfolio_id)


def _holdings_editor_gen_key(portfolio_id: int) -> str:
    return f"holdings_editor_gen_{portfolio_id}"


def _holdings_save_error_key(portfolio_id: int) -> str:
    return f"portfolio_save_error_{portfolio_id}"


def set_holdings_save_error(portfolio_id: int, message: str):
    st.session_state[_holdings_save_error_key(portfolio_id)] = message


def clear_holdings_save_error(portfolio_id: int):
    st.session_state.pop(_holdings_save_error_key(portfolio_id), None)


def render_holdings_save_error(portfolio_id: int, edited_df: pd.DataFrame) -> None:
    """
    Show a save validation error until the editor content parses successfully.
    Clears automatically when the user fixes fields (e.g. Target) — no extra Save click.
    """
    err_key = _holdings_save_error_key(portfolio_id)
    if not st.session_state.get(err_key):
        return
    try:
        parse_holdings_editor_df(edited_df)
    except ValueError as exc:
        st.session_state[err_key] = str(exc)
        st.error(str(exc))
    else:
        st.session_state.pop(err_key, None)


def holdings_editor_widget_key(portfolio_id: int) -> str:
    """Versioned key so Streamlit drops stale data_editor state after save/add/delete."""
    gen = int(st.session_state.get(_holdings_editor_gen_key(portfolio_id), 0))
    return f"portfolio_holdings_editor_{portfolio_id}_v{gen}"


def bump_holdings_editor_generation(portfolio_id: int):
    st.session_state[_holdings_editor_gen_key(portfolio_id)] = (
        int(st.session_state.get(_holdings_editor_gen_key(portfolio_id), 0)) + 1
    )
    st.session_state.pop(f"portfolio_holdings_editor_{portfolio_id}", None)


def set_holdings_draft(portfolio_id: int, df: pd.DataFrame):
    """Persist draft lots and refresh the editor + screener preview."""
    st.session_state[_draft_key(portfolio_id)] = df.copy()
    bump_holdings_editor_generation(portfolio_id)
    invalidate_analysis(refetch_metadata=False)


def get_editable_holdings_df() -> pd.DataFrame:
    """Raw holdings draft (may include N rows per symbol until Save)."""
    active = load_active_portfolio()
    draft = st.session_state.get(_draft_key(active.portfolio_id))
    if draft is not None:
        return draft.copy()
    return active.holdings_df.copy()


def has_holdings_draft(portfolio_id: int | None = None) -> bool:
    active = load_active_portfolio()
    pid = portfolio_id if portfolio_id is not None else active.portfolio_id
    return _draft_key(pid) in st.session_state


def get_holdings_for_analysis_df() -> pd.DataFrame:
    """
    Holdings for prices/KPIs/table analysis — consolidates duplicate symbols in draft
    without persisting (§6 preview only).
    """
    raw = get_editable_holdings_df()
    if raw.empty or not raw["Symbol"].duplicated().any():
        return raw
    return merge_duplicate_symbol_rows(raw.copy())


def prepare_holdings_editor_df(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Holdings-only editor frame (six user columns)."""
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame(columns=list(HOLDINGS_EDITOR_COLUMNS))
    out = holdings_df.copy()
    for col in HOLDINGS_EDITOR_COLUMNS:
        if col not in out.columns:
            out[col] = None
    out = out[list(HOLDINGS_EDITOR_COLUMNS)]
    out["Symbol"] = out["Symbol"].astype(str).str.strip().str.upper()
    out["Shares"] = pd.to_numeric(out["Shares"], errors="coerce")
    out["AvgCost"] = pd.to_numeric(out["AvgCost"], errors="coerce")
    out["TargetPrice"] = pd.to_numeric(out["TargetPrice"], errors="coerce")
    out["Currency"] = out["Currency"].fillna("USD").astype(str).str.strip().str.upper()
    out["PurchaseDate"] = pd.to_datetime(out["PurchaseDate"], errors="coerce")
    return out


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

    return errors


def validate_holdings_editor_df(edited_df: pd.DataFrame) -> list[str]:
    """
    Validate holdings editor while editing.
    Shares are required (and > 0); AvgCost/Target are required only on Save.
    """
    if edited_df is None or edited_df.empty:
        return ["Add at least one row with Symbol and Shares."]

    errors = []
    for idx, row in edited_df.iterrows():
        symbol = str(row.get("Symbol", "")).strip().upper()
        if not symbol or symbol in {"NONE", "NAN"}:
            continue

        shares_val = row.get("Shares")
        if shares_val is None or (isinstance(shares_val, float) and pd.isna(shares_val)):
            errors.append(f"Row {int(idx) + 1} ({symbol}): Shares is required.")
        else:
            try:
                shares = float(shares_val)
            except (TypeError, ValueError):
                errors.append(f"Row {int(idx) + 1} ({symbol}): Shares must be a number.")
            else:
                if shares < 0:
                    errors.append(f"Row {int(idx) + 1} ({symbol}): Shares cannot be negative.")
                elif shares == 0:
                    errors.append(f"Row {int(idx) + 1} ({symbol}): Shares cannot be zero.")

        for col, label in (("AvgCost", "AvgCost"), ("TargetPrice", "Target")):
            val = row.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                continue
            try:
                num = float(val)
            except (TypeError, ValueError):
                errors.append(f"Row {int(idx) + 1} ({symbol}): {label} must be a number.")
                continue
            if num < 0:
                errors.append(f"Row {int(idx) + 1} ({symbol}): {label} cannot be negative.")

        purchase = row.get("PurchaseDate")
        if purchase is not None and not (isinstance(purchase, float) and pd.isna(purchase)):
            try:
                pdt = pd.to_datetime(purchase)
                if pdt > pd.Timestamp.now().normalize() + pd.Timedelta(days=1):
                    errors.append(
                        f"Row {int(idx) + 1} ({symbol}): Purchase date cannot be in the future."
                    )
            except Exception:
                pass

    return errors


def get_holdings_editor_column_config() -> dict:
    """Streamlit column config for the six-column holdings editor."""
    return {
        "Symbol": st.column_config.TextColumn("Symbol", pinned=True, width="small"),
        "Shares": st.column_config.NumberColumn("Shares", format="%.2f", min_value=0.0),
        "AvgCost": st.column_config.NumberColumn("Avg cost", format="%.2f", min_value=0.0),
        "PurchaseDate": st.column_config.DateColumn("Purchase date", format="YYYY-MM-DD"),
        "TargetPrice": st.column_config.NumberColumn("Target", format="%.2f", min_value=0.0),
        "Currency": st.column_config.SelectboxColumn(
            "Currency", options=["USD", "EUR"], required=True
        ),
    }


def holdings_editor_duplicates_hint(edited_df: pd.DataFrame) -> str | None:
    symbols = [
        str(s).strip().upper()
        for s in edited_df.get("Symbol", pd.Series(dtype=str)).tolist()
        if str(s).strip()
    ]
    multi = sorted({s for s in symbols if symbols.count(s) > 1})
    if not multi:
        return None
    return (
        f"Multiple lots for {', '.join(multi)} — will merge into one row per symbol on **Save** "
        "(weighted cost, earliest purchase date)."
    )


def parse_holdings_editor_df(edited_df: pd.DataFrame) -> pd.DataFrame:
    """Map editor rows to DB holdings schema (duplicates consolidated on save in repository)."""
    rows = []
    for _, row in edited_df.iterrows():
        symbol = str(row.get("Symbol", "")).strip().upper()
        if not symbol:
            continue

        shares = _parse_required_float(row.get("Shares"), field_label="Shares", symbol=symbol)
        avg_cost = _parse_required_float(row.get("AvgCost"), field_label="AvgCost", symbol=symbol)
        target = _parse_required_float(
            row.get("TargetPrice"), field_label="Target", symbol=symbol
        )
        if shares == 0:
            raise ValueError(f"{symbol}: Shares cannot be zero.")

        purchase = row.get("PurchaseDate")
        if purchase is None or (isinstance(purchase, float) and pd.isna(purchase)):
            purchase_dt = None
        else:
            purchase_dt = pd.to_datetime(purchase, errors="coerce")
            if pd.isna(purchase_dt):
                purchase_dt = None

        currency = str(row.get("Currency", "USD") or "USD").strip().upper()

        rows.append({
            "Symbol": symbol,
            "Shares": shares,
            "AvgCost": avg_cost,
            "PurchaseDate": purchase_dt,
            "TargetPrice": target,
            "Currency": currency,
        })

    if not rows:
        raise ValueError("Portfolio must contain at least one position.")
    return pd.DataFrame(rows)


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


def append_symbol_to_draft(
    portfolio_id: int,
    holdings_df: pd.DataFrame,
    symbol: str,
    currency: str,
    shares: float,
) -> pd.DataFrame:
    symbol = symbol.strip().upper()
    if shares <= 0:
        raise ValueError("Shares must be greater than zero.")
    new_row = pd.DataFrame([{
        "Symbol": symbol,
        "Shares": float(shares),
        "AvgCost": float("nan"),
        "PurchaseDate": pd.Timestamp(date.today()),
        "TargetPrice": float("nan"),
        "Currency": currency,
    }])
    # Prepend so the new lot appears at the top of the editor (visible without scrolling).
    return pd.concat([new_row, holdings_df], ignore_index=True)


def save_holdings_from_df(portfolio_id: int, holdings_df: pd.DataFrame):
    """Persist holdings; repository consolidates N rows per symbol (§6)."""
    with st.spinner("Validating symbols…"):
        validate_holdings_symbols(holdings_df)
    svc = get_portfolio_service()
    active = svc.save_holdings(portfolio_id, holdings_df)
    clear_holdings_draft(portfolio_id)
    clear_holdings_save_error(portfolio_id)
    set_active_portfolio_id(active.portfolio_id)
    svc.remember_last_portfolio(active.user_id, active.portfolio_id)
    invalidate_analysis(refetch_metadata=False)
