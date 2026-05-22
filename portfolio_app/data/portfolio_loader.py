"""Portfolio CSV loading: upload, CLI, defaults, and demo mock."""
import os
import sys

import pandas as pd
import streamlit as st

from portfolio_app.config import APP_DIR, PORTFOLIO_FILE_CANDIDATES


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


def _parse_portfolio_df(df):
    df = df.copy()
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"])
    return df


def load_portfolio_from_path(path):
    df = _parse_portfolio_df(pd.read_csv(path, sep=";"))
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


def _read_uploaded_portfolio(uploaded_file):
    """Read uploaded CSV; Streamlit files must be rewound on each rerun."""
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=";")
    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV is empty or has no columns")
    return _parse_portfolio_df(df)


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
