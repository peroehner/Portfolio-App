"""Portfolio persistence (SQLite)."""
from datetime import datetime
from typing import List, Optional

import pandas as pd

from portfolio_app.data.portfolio_loader import (
    coerce_portfolio_numeric_columns,
    merge_duplicate_symbol_rows,
)
from portfolio_app.domain.models import Portfolio, Position, User
from portfolio_app.storage.database import get_connection, init_database


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None


def _format_dt(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.strftime("%Y-%m-%d")


class PortfolioRepository:
    def __init__(self):
        init_database()

    @staticmethod
    def _display_name_from_email(email: str) -> str:
        prefix = (email or "").split("@")[0].strip()
        return prefix or "User"

    @staticmethod
    def _user_from_row(row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            last_portfolio_id=row["last_portfolio_id"],
            display_name=row["display_name"],
            status=row["status"] or "active",
            created_at=_parse_dt(row["created_at"]),
            last_login_at=_parse_dt(row["last_login_at"]),
        )

    def get_or_create_user(self, email: str) -> User:
        email = email.strip().lower()
        if not email:
            raise ValueError("Email is required.")
        display_name = self._display_name_from_email(email)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE users
                    SET last_login_at = datetime('now'),
                        display_name = COALESCE(NULLIF(display_name, ''), ?),
                        status = COALESCE(NULLIF(status, ''), 'active')
                    WHERE id = ?
                    """,
                    (display_name, row["id"]),
                )
                row = conn.execute(
                    """
                    SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                    FROM users
                    WHERE id = ?
                    """,
                    (row["id"],),
                ).fetchone()
                return self._user_from_row(row)
            cur = conn.execute(
                "INSERT INTO users (email, display_name, status, last_login_at) VALUES (?, ?, 'active', datetime('now'))",
                (email, display_name),
            )
            row = conn.execute(
                """
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
            return self._user_from_row(row)

    def list_users(self) -> List[User]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE COALESCE(status, 'active') = 'active'
                ORDER BY email ASC
                """
            ).fetchall()
        return [self._user_from_row(r) for r in rows]

    def get_user(self, user_id: int) -> Optional[User]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return self._user_from_row(row)

    def set_last_portfolio(self, user_id: int, portfolio_id: int):
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_portfolio_id = ? WHERE id = ?",
                (portfolio_id, user_id),
            )

    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, user_id, name, updated_at FROM portfolios WHERE id = ?",
                (portfolio_id,),
            ).fetchone()
            if not row:
                return None
            return Portfolio(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                updated_at=_parse_dt(row["updated_at"]),
            )

    def get_user_portfolio(self, user_id: int, portfolio_id: Optional[int] = None) -> Optional[Portfolio]:
        with get_connection() as conn:
            if portfolio_id:
                row = conn.execute(
                    "SELECT id, user_id, name, updated_at FROM portfolios WHERE id = ? AND user_id = ?",
                    (portfolio_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, user_id, name, updated_at FROM portfolios
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
            if not row:
                return None
            return Portfolio(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                updated_at=_parse_dt(row["updated_at"]),
            )

    def list_portfolios(self, user_id: int) -> List[Portfolio]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, name, updated_at FROM portfolios
                WHERE user_id = ?
                ORDER BY updated_at DESC, name ASC
                """,
                (user_id,),
            ).fetchall()
        return [
            Portfolio(
                id=r["id"],
                user_id=r["user_id"],
                name=r["name"],
                updated_at=_parse_dt(r["updated_at"]),
            )
            for r in rows
        ]

    def find_portfolio_by_name(self, user_id: int, name: str) -> Optional[Portfolio]:
        name = name.strip()
        if not name:
            return None
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, name, updated_at FROM portfolios
                WHERE user_id = ? AND name = ?
                """,
                (user_id, name),
            ).fetchone()
        if not row:
            return None
        return Portfolio(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            updated_at=_parse_dt(row["updated_at"]),
        )

    def create_portfolio(self, user_id: int, name: str) -> Portfolio:
        name = name.strip()
        if not name:
            raise ValueError("Portfolio name is required.")
        if self.find_portfolio_by_name(user_id, name):
            raise ValueError(f'A portfolio named "{name}" already exists.')
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO portfolios (user_id, name) VALUES (?, ?)",
                (user_id, name),
            )
            return Portfolio(
                id=cur.lastrowid,
                user_id=user_id,
                name=name,
                updated_at=datetime.now(),
            )

    def delete_portfolio(self, user_id: int, portfolio_id: int):
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET last_portfolio_id = NULL
                WHERE id = ? AND last_portfolio_id = ?
                """,
                (user_id, portfolio_id),
            )
            conn.execute(
                "DELETE FROM portfolios WHERE id = ? AND user_id = ?",
                (portfolio_id, user_id),
            )

    def list_positions(self, portfolio_id: int) -> List[Position]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, portfolio_id, symbol, shares, avg_cost, purchase_date,
                       target_price, currency, sort_order
                FROM positions
                WHERE portfolio_id = ?
                ORDER BY sort_order, symbol
                """,
                (portfolio_id,),
            ).fetchall()
        return [
            Position(
                id=r["id"],
                portfolio_id=r["portfolio_id"],
                symbol=str(r["symbol"]).strip().upper(),
                shares=float(r["shares"]),
                avg_cost=float(r["avg_cost"]),
                purchase_date=_parse_dt(r["purchase_date"]),
                target_price=float(r["target_price"]),
                currency=str(r["currency"] or "USD").strip().upper(),
                sort_order=int(r["sort_order"]),
            )
            for r in rows
        ]

    def positions_to_dataframe(self, positions: List[Position]) -> pd.DataFrame:
        if not positions:
            return pd.DataFrame(
                columns=["Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"]
            )
        rows = []
        for p in positions:
            rows.append({
                "Symbol": p.symbol,
                "Shares": p.shares,
                "AvgCost": p.avg_cost,
                "PurchaseDate": p.purchase_date.strftime("%Y-%m-%d")
                if p.purchase_date
                else None,
                "TargetPrice": p.target_price,
                "Currency": p.currency,
            })
        df = pd.DataFrame(rows)
        df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
        return df

    def replace_positions(self, portfolio_id: int, df: pd.DataFrame, *, allow_empty: bool = False):
        cleaned = self._normalize_holdings_df(df, allow_empty=allow_empty)
        with get_connection() as conn:
            conn.execute("DELETE FROM positions WHERE portfolio_id = ?", (portfolio_id,))
            for idx, row in cleaned.iterrows():
                conn.execute(
                    """
                    INSERT INTO positions (
                        portfolio_id, symbol, shares, avg_cost, purchase_date,
                        target_price, currency, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        portfolio_id,
                        row["Symbol"],
                        float(row["Shares"]),
                        float(row["AvgCost"]),
                        _format_dt(row["PurchaseDate"]),
                        float(row["TargetPrice"]),
                        str(row["Currency"]),
                        int(idx),
                    ),
                )
            conn.execute(
                "UPDATE portfolios SET updated_at = datetime('now') WHERE id = ?",
                (portfolio_id,),
            )

    def rename_portfolio(self, user_id: int, portfolio_id: int, name: str):
        name = name.strip()
        if not name:
            raise ValueError("Portfolio name is required.")
        other = self.find_portfolio_by_name(user_id, name)
        if other and other.id != portfolio_id:
            raise ValueError(f'A portfolio named "{name}" already exists.')
        with get_connection() as conn:
            conn.execute(
                "UPDATE portfolios SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (name, portfolio_id),
            )

    @staticmethod
    def _normalize_holdings_df(df: pd.DataFrame, *, allow_empty: bool = False) -> pd.DataFrame:
        required = ["Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        out = df.copy()
        out = out[required]
        out = out.dropna(subset=["Symbol"])
        out["Symbol"] = out["Symbol"].astype(str).str.strip().str.upper()
        out = out[out["Symbol"] != ""]
        out = coerce_portfolio_numeric_columns(out)
        out["Shares"] = pd.to_numeric(out["Shares"], errors="coerce").fillna(0)
        out["AvgCost"] = pd.to_numeric(out["AvgCost"], errors="coerce").fillna(0)
        out["TargetPrice"] = pd.to_numeric(out["TargetPrice"], errors="coerce").fillna(0)
        out["Currency"] = out["Currency"].fillna("USD").astype(str).str.strip().str.upper()
        out["PurchaseDate"] = pd.to_datetime(out["PurchaseDate"], errors="coerce")
        out = merge_duplicate_symbol_rows(out)
        if out.empty and not allow_empty:
            raise ValueError("Portfolio must contain at least one position.")
        return out.reset_index(drop=True)
