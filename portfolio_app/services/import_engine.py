"""CSV import: preflight validation, preview, and replace/merge apply (Phase 2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import pandas as pd

from portfolio_app.data.portfolio_loader import (
    PORTFOLIO_CSV_COLUMNS,
    coerce_portfolio_numeric_columns,
    merge_duplicate_symbol_rows,
    parse_price_number,
    parse_shares_number,
)


class ImportMode(str, Enum):
    REPLACE = "replace"
    MERGE = "merge"


@dataclass(frozen=True)
class RowIssue:
    row_number: int
    symbol: str
    reason: str


@dataclass
class ImportPreview:
    mode: ImportMode
    added: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    rejected: List[RowIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    result_symbol_count: int = 0

    @property
    def can_apply(self) -> bool:
        if self.rejected and self.result_symbol_count == 0:
            return False
        return True


@dataclass
class ImportApplyResult:
    mode: ImportMode
    holdings_df: pd.DataFrame
    preview: ImportPreview
    symbols_added: int = 0
    symbols_updated: int = 0
    symbols_removed: int = 0
    symbols_unchanged: int = 0


def _normalize_symbol(value) -> str:
    return str(value or "").strip().upper()


def _validate_raw_row(row: pd.Series, row_number: int) -> Tuple[Optional[dict], Optional[RowIssue]]:
    symbol = _normalize_symbol(row.get("Symbol", ""))
    if not symbol:
        return None, RowIssue(row_number, "", "Missing or empty Symbol")

    shares_raw = row.get("Shares", "")
    shares = parse_shares_number(shares_raw)
    if pd.isna(shares):
        return None, RowIssue(row_number, symbol, f"Invalid Shares: {shares_raw!r}")
    if shares < 0:
        return None, RowIssue(row_number, symbol, "Shares cannot be negative")
    if shares == 0:
        return None, RowIssue(row_number, symbol, "Shares cannot be zero")

    avg_cost = parse_price_number(row.get("AvgCost", ""))
    if pd.isna(avg_cost):
        return None, RowIssue(row_number, symbol, f"Invalid AvgCost: {row.get('AvgCost', '')!r}")
    if avg_cost < 0:
        return None, RowIssue(row_number, symbol, "AvgCost cannot be negative")

    target_price = parse_price_number(row.get("TargetPrice", ""))
    if pd.isna(target_price):
        return None, RowIssue(
            row_number, symbol, f"Invalid TargetPrice: {row.get('TargetPrice', '')!r}"
        )
    if target_price < 0:
        return None, RowIssue(row_number, symbol, "TargetPrice cannot be negative")

    purchase_date = pd.to_datetime(row.get("PurchaseDate", ""), errors="coerce")
    currency = str(row.get("Currency", "") or "USD").strip().upper() or "USD"

    return {
        "Symbol": symbol,
        "Shares": float(shares),
        "AvgCost": float(avg_cost),
        "PurchaseDate": purchase_date,
        "TargetPrice": float(target_price),
        "Currency": currency,
    }, None


def parse_csv_preflight(raw: pd.DataFrame) -> Tuple[pd.DataFrame, List[RowIssue]]:
    """
    Validate CSV rows; skip rejected rows; consolidate N rows per symbol within the file.
    """
    missing = [c for c in PORTFOLIO_CSV_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    if raw.empty:
        empty = pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
        return empty, []

    rejected: List[RowIssue] = []
    valid_dicts = []
    for idx, row in raw.iterrows():
        row_number = int(idx) + 2
        parsed, issue = _validate_raw_row(row, row_number)
        if issue:
            rejected.append(issue)
        else:
            valid_dicts.append(parsed)

    if not valid_dicts:
        empty = pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
        return empty, rejected

    df = pd.DataFrame(valid_dicts)
    df = coerce_portfolio_numeric_columns(df)
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
    df = merge_duplicate_symbol_rows(df)
    return df.reset_index(drop=True), rejected


def _holdings_row_dict(row: pd.Series) -> dict:
    purchase = row.get("PurchaseDate")
    if pd.isna(purchase):
        purchase_out = None
    else:
        purchase_out = pd.to_datetime(purchase).strftime("%Y-%m-%d")
    return {
        "Symbol": _normalize_symbol(row["Symbol"]),
        "Shares": round(float(row["Shares"]), 6),
        "AvgCost": round(float(row["AvgCost"]), 6),
        "PurchaseDate": purchase_out,
        "TargetPrice": round(float(row["TargetPrice"]), 6),
        "Currency": str(row.get("Currency", "USD")).strip().upper(),
    }


def holdings_rows_equal(left: pd.Series, right: pd.Series) -> bool:
    return _holdings_row_dict(left) == _holdings_row_dict(right)


def merge_holdings_dataframes(
    current: pd.DataFrame, csv_consolidated: pd.DataFrame
) -> pd.DataFrame:
    """Merge DB holdings with consolidated CSV rows (§6 per overlapping symbol)."""
    current = current if current is not None and not current.empty else pd.DataFrame(
        columns=list(PORTFOLIO_CSV_COLUMNS)
    )
    csv_consolidated = (
        csv_consolidated
        if csv_consolidated is not None and not csv_consolidated.empty
        else pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
    )

    current_symbols = {
        _normalize_symbol(s) for s in current.get("Symbol", pd.Series(dtype=str))
    }
    csv_symbols = {
        _normalize_symbol(s) for s in csv_consolidated.get("Symbol", pd.Series(dtype=str))
    }
    all_symbols = sorted(current_symbols | csv_symbols)

    rows = []
    for symbol in all_symbols:
        db_rows = current[current["Symbol"].astype(str).str.upper() == symbol]
        csv_rows = csv_consolidated[
            csv_consolidated["Symbol"].astype(str).str.upper() == symbol
        ]
        if not db_rows.empty and csv_rows.empty:
            rows.append(db_rows.iloc[0].to_dict())
        elif db_rows.empty and not csv_rows.empty:
            rows.append(csv_rows.iloc[0].to_dict())
        else:
            combined = pd.concat([db_rows, csv_rows], ignore_index=True)
            merged = merge_duplicate_symbol_rows(combined)
            rows.append(merged.iloc[0].to_dict())

    if not rows:
        return pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
    out = pd.DataFrame(rows)
    out["PurchaseDate"] = pd.to_datetime(out["PurchaseDate"], errors="coerce")
    return out.reset_index(drop=True)


def _currency_warnings(
    current: pd.DataFrame, csv_consolidated: pd.DataFrame, symbols: List[str]
) -> List[str]:
    warnings = []
    if current.empty or csv_consolidated.empty:
        return warnings
    db_currency = current.set_index(current["Symbol"].str.upper())["Currency"]
    csv_currency = csv_consolidated.set_index(csv_consolidated["Symbol"].str.upper())[
        "Currency"
    ]
    for symbol in symbols:
        if symbol not in db_currency.index or symbol not in csv_currency.index:
            continue
        db_cur = str(db_currency[symbol]).upper()
        csv_cur = str(csv_currency[symbol]).upper()
        if db_cur != csv_cur:
            warnings.append(
                f"{symbol}: currency {csv_cur} (CSV) vs {db_cur} (portfolio) — "
                f"merged row will use the largest lot's currency (§6)."
            )
    return warnings


def build_import_preview(
    current: pd.DataFrame,
    csv_consolidated: pd.DataFrame,
    mode: ImportMode,
    rejected: Optional[List[RowIssue]] = None,
) -> ImportPreview:
    """Compute added / updated / removed / unchanged before commit."""
    rejected = rejected or []
    current = current if current is not None else pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
    csv_consolidated = (
        csv_consolidated
        if csv_consolidated is not None
        else pd.DataFrame(columns=list(PORTFOLIO_CSV_COLUMNS))
    )

    current_by_symbol = {
        _normalize_symbol(r["Symbol"]): r for _, r in current.iterrows()
    }
    csv_by_symbol = {
        _normalize_symbol(r["Symbol"]): r for _, r in csv_consolidated.iterrows()
    }
    current_symbols = set(current_by_symbol)
    csv_symbols = set(csv_by_symbol)

    preview = ImportPreview(mode=mode, rejected=list(rejected))

    if mode == ImportMode.REPLACE:
        preview.removed = sorted(current_symbols - csv_symbols)
        preview.added = sorted(csv_symbols - current_symbols)
        for symbol in sorted(current_symbols & csv_symbols):
            if holdings_rows_equal(current_by_symbol[symbol], csv_by_symbol[symbol]):
                preview.unchanged.append(symbol)
            else:
                preview.updated.append(symbol)
        result = csv_consolidated
    else:
        merged = merge_holdings_dataframes(current, csv_consolidated)
        merged_by_symbol = {_normalize_symbol(r["Symbol"]): r for _, r in merged.iterrows()}
        preview.added = sorted(csv_symbols - current_symbols)
        overlap = current_symbols & csv_symbols
        preview.warnings = _currency_warnings(
            current, csv_consolidated, sorted(overlap)
        )
        unchanged_set = set(current_symbols - csv_symbols)
        for symbol in sorted(overlap):
            if holdings_rows_equal(current_by_symbol[symbol], merged_by_symbol[symbol]):
                unchanged_set.add(symbol)
            else:
                preview.updated.append(symbol)
        preview.unchanged = sorted(unchanged_set)
        result = merged

    preview.result_symbol_count = len(result)
    return preview


def apply_import(
    current: pd.DataFrame,
    csv_consolidated: pd.DataFrame,
    mode: ImportMode,
    rejected: Optional[List[RowIssue]] = None,
    *,
    allow_empty_replace: bool = False,
) -> ImportApplyResult:
    """Build final holdings DataFrame and summary for persistence."""
    preview = build_import_preview(current, csv_consolidated, mode, rejected)

    if mode == ImportMode.REPLACE:
        if csv_consolidated.empty and not allow_empty_replace:
            raise ValueError(
                "Replace import has no valid rows. Fix the CSV or confirm clearing all holdings."
            )
        holdings_df = csv_consolidated.copy()
    else:
        if csv_consolidated.empty and (current is None or current.empty):
            raise ValueError("Nothing to import: CSV and portfolio are both empty.")
        holdings_df = merge_holdings_dataframes(current, csv_consolidated)

    return ImportApplyResult(
        mode=mode,
        holdings_df=holdings_df.reset_index(drop=True),
        preview=preview,
        symbols_added=len(preview.added),
        symbols_updated=len(preview.updated),
        symbols_removed=len(preview.removed),
        symbols_unchanged=len(preview.unchanged),
    )
