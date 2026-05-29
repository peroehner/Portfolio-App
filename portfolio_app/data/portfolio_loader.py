"""Portfolio CSV loading: upload, CLI, defaults, and demo mock."""
import os
import re
import sys

import pandas as pd
import streamlit as st

from portfolio_app.config import APP_DIR, PORTFOLIO_FILE_CANDIDATES

PORTFOLIO_CSV_COLUMNS = (
    "Symbol",
    "Shares",
    "AvgCost",
    "PurchaseDate",
    "TargetPrice",
    "Currency",
)

_NUMERIC_CSV_COLUMNS = ("Shares", "AvgCost", "TargetPrice")


def parse_locale_number(value, *, allow_dot_thousands: bool = False) -> float:
    """
    Parse numbers from portfolio CSV (US or European formats).

    When allow_dot_thousands is True (Shares only), 1.500 → 1500.
    Prices (AvgCost, TargetPrice) always treat a single dot as decimal (198.380 → 198.38).
    """
    if value is None:
        return float("nan")
    if isinstance(value, float) and pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return float("nan")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        left, _, right = s.partition(",")
        if (
            allow_dot_thousands
            and right.isdigit()
            and len(right) == 3
            and left.isdigit()
        ):
            s = left + right
        else:
            s = left + "." + right
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 2 and all(part.isdigit() for part in parts):
            s = "".join(parts)
        elif (
            allow_dot_thousands
            and len(parts) == 2
            and parts[0].isdigit()
            and parts[1].isdigit()
            and len(parts[1]) == 3
        ):
            s = parts[0] + parts[1]

    try:
        return float(s)
    except ValueError:
        return float("nan")


def parse_shares_number(value) -> float:
    return parse_locale_number(value, allow_dot_thousands=True)


def parse_price_number(value) -> float:
    return parse_locale_number(value, allow_dot_thousands=False)


def coerce_portfolio_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Shares" in out.columns:
        out["Shares"] = out["Shares"].map(parse_shares_number)
    for col in ("AvgCost", "TargetPrice"):
        if col in out.columns:
            out[col] = out[col].map(parse_price_number)
    return out


def get_cli_filename():
    """Extract filename if passed via '-f <filename>' on the command line."""
    try:
        args = sys.argv
        if "-f" in args:
            idx = args.index("-f")
            if idx + 1 < len(args):
                potential_file = args[idx + 1]
                if os.path.isabs(potential_file) and os.path.exists(potential_file):
                    return potential_file
                for base in (os.getcwd(), APP_DIR):
                    candidate = os.path.join(base, potential_file)
                    if os.path.exists(candidate):
                        return candidate
    except Exception:
        pass
    return None


def _read_portfolio_csv(source) -> pd.DataFrame:
    """Read semicolon CSV without losing European thousands (e.g. 1.500 → 1500)."""
    df = pd.read_csv(
        source,
        sep=";",
        dtype=str,
        keep_default_na=False,
    )
    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV is empty or has no columns")
    return df


def _parse_portfolio_df(df):
    df = df.copy()
    df = coerce_portfolio_numeric_columns(df)
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
    if "Symbol" in df.columns:
        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
        df = df[df["Symbol"] != ""]
    df = merge_duplicate_symbol_rows(df)
    return df


def merge_duplicate_symbol_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge multiple rows for the same Symbol into one holding.

    Shares are summed. AvgCost and TargetPrice use a share-weighted average.
    PurchaseDate is the earliest non-null date. Currency follows the largest lot.
    """
    if df.empty or not df["Symbol"].duplicated().any():
        return df

    merged_rows = []
    for symbol, group in df.groupby("Symbol", sort=False):
        shares = group["Shares"].astype(float)
        total_shares = float(shares.sum())
        if total_shares > 0:
            avg_cost = float((shares * group["AvgCost"]).sum() / total_shares)
            target_price = float((shares * group["TargetPrice"]).sum() / total_shares)
            currency = str(group.loc[shares.idxmax(), "Currency"])
        else:
            avg_cost = float(group["AvgCost"].mean())
            target_price = float(group["TargetPrice"].mean())
            currency = str(group["Currency"].iloc[0])

        valid_dates = group["PurchaseDate"][pd.notna(group["PurchaseDate"])]
        purchase_date = valid_dates.min() if not valid_dates.empty else pd.NaT

        merged_rows.append(
            {
                "Symbol": symbol,
                "Shares": total_shares,
                "AvgCost": avg_cost,
                "PurchaseDate": purchase_date,
                "TargetPrice": target_price,
                "Currency": currency,
            }
        )

    return pd.DataFrame(merged_rows, columns=list(PORTFOLIO_CSV_COLUMNS))


def load_portfolio_from_path(path):
    df = _parse_portfolio_df(_read_portfolio_csv(path))
    return df, os.path.basename(path)


def get_mock_portfolio_df():
    """Demo portfolio when no CSV is available."""
    df = pd.DataFrame([
        {"Symbol": "AAPL", "Name": "Apple Inc.", "Shares": 100, "PurchaseDate": "2024-01-15", "AvgCost": 175.0, "TargetPrice": 220.0, "Currency": "USD"},
        {"Symbol": "GOOGL", "Name": "Alphabet (Google)", "Shares": 50, "PurchaseDate": "2024-03-01", "AvgCost": 140.0, "TargetPrice": 200.0, "Currency": "USD"},
        {"Symbol": "CRWD", "Name": "CrowdStrike", "Shares": 75, "PurchaseDate": "2024-06-01", "AvgCost": 280.0, "TargetPrice": 400.0, "Currency": "USD"},
        {"Symbol": "NBIS", "Name": "Nebius Group", "Shares": 200, "PurchaseDate": "2024-09-01", "AvgCost": 25.0, "TargetPrice": 45.0, "Currency": "USD"},
        {"Symbol": "MELI", "Name": "MercadoLibre", "Shares": 30, "PurchaseDate": "2023-11-01", "AvgCost": 1500.0, "TargetPrice": 2200.0, "Currency": "USD"},
    ])
    return _parse_portfolio_df(df)


def portfolio_export_filename(portfolio_name: str) -> str:
    """Map portfolio name to download filename, e.g. HighGrowth → HighGrowth.csv."""
    stem = (portfolio_name or "portfolio").strip()
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", stem).strip(" .")
    if not stem:
        stem = "portfolio"
    if stem.lower().endswith(".csv"):
        return stem
    return f"{stem}.csv"


def holdings_to_export_csv(df: pd.DataFrame | None) -> str:
    """Semicolon-separated CSV matching the import format."""
    if df is None or df.empty:
        return ";".join(PORTFOLIO_CSV_COLUMNS) + "\n"

    out = df.copy()
    for col in PORTFOLIO_CSV_COLUMNS:
        if col not in out.columns:
            raise ValueError(f"Missing column: {col}")

    out = out[list(PORTFOLIO_CSV_COLUMNS)]
    dates = pd.to_datetime(out["PurchaseDate"], errors="coerce")
    out["PurchaseDate"] = dates.dt.strftime("%Y-%m-%d").where(dates.notna(), "")
    return out.to_csv(sep=";", index=False)


def _read_uploaded_portfolio(uploaded_file):
    """Read uploaded CSV; Streamlit files must be rewound on each rerun."""
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    return _parse_portfolio_df(_read_portfolio_csv(uploaded_file))


def load_portfolio(uploaded_file):
    """Load portfolio: upload > CLI > myPortfolio.csv > Sample-Portfolio.csv > demo mock."""
    try:
        if uploaded_file is not None:
            cache_key = (
                f"{st.session_state.get('uploader_key', 0)}:"
                f"{uploaded_file.name}:"
                f"{getattr(uploaded_file, 'size', 0)}"
            )
            if st.session_state.get("uploaded_portfolio_cache_key") == cache_key:
                return (
                    st.session_state.uploaded_portfolio_df.copy(),
                    uploaded_file.name,
                )
            df = _read_uploaded_portfolio(uploaded_file)
            st.session_state.uploaded_portfolio_cache_key = cache_key
            st.session_state.uploaded_portfolio_df = df
            st.session_state.uploaded_portfolio_name = uploaded_file.name
            return df, uploaded_file.name

        cached_df = st.session_state.get("uploaded_portfolio_df")
        if cached_df is not None:
            return (
                cached_df.copy(),
                st.session_state.get("uploaded_portfolio_name", "Uploaded portfolio"),
            )

        cli_file = get_cli_filename()
        if cli_file is not None:
            return load_portfolio_from_path(cli_file)

        for filename in PORTFOLIO_FILE_CANDIDATES:
            path = os.path.join(APP_DIR, filename)
            if os.path.exists(path):
                return load_portfolio_from_path(path)

        return get_mock_portfolio_df(), "Demo Portfolio (mock)"
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
        return None, "Load error"
