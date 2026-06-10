"""Portfolio persistence (SQLite)."""
from datetime import datetime, timezone
from typing import Iterable, List, Optional

import pandas as pd

from portfolio_app.data.portfolio_loader import (
    coerce_portfolio_numeric_columns,
    merge_duplicate_symbol_rows,
)
from portfolio_app.domain.models import (
    Portfolio,
    PortfolioSyncState,
    Position,
    SymbolFinancialSnapshot,
    SYNC_STATUS_NEVER,
    User,
)
from portfolio_app.domain.user_identity import (
    ACCOUNT_SELECTABLE_STATUSES,
    display_name_from_email,
    normalize_email,
)
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


def _format_sync_dt(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def _optional_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


class PortfolioRepository:
    def __init__(self):
        init_database()

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

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Lookup by canonical email without creating a row or touching last_login."""
        email = normalize_email(email)
        if not email:
            return None
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()
        if not row:
            return None
        return self._user_from_row(row)

    def update_user_status(self, user_id: int, status: str) -> User:
        status = (status or "").strip().lower()
        if not status:
            raise ValueError("Status is required.")
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status, user_id),
            )
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found.")
        return user

    def get_or_create_user(self, email: str) -> User:
        email = normalize_email(email)
        if not email:
            raise ValueError("Email is required.")
        display_name = display_name_from_email(email)
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

    def list_users(
        self,
        *,
        statuses: Optional[Iterable[str]] = None,
    ) -> List[User]:
        allowed = tuple(statuses) if statuses is not None else ACCOUNT_SELECTABLE_STATUSES
        if not allowed:
            return []
        placeholders = ",".join("?" for _ in allowed)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, email, display_name, status, last_portfolio_id, created_at, last_login_at
                FROM users
                WHERE COALESCE(status, 'active') IN ({placeholders})
                ORDER BY email ASC
                """,
                allowed,
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
            portfolio_id = int(cur.lastrowid)
            self._ensure_sync_state_conn(conn, portfolio_id)
            return Portfolio(
                id=portfolio_id,
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
        keep_symbols = {_normalize_symbol(s) for s in cleaned["Symbol"].tolist()}
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
            self._prune_symbol_snapshots_conn(conn, portfolio_id, keep_symbols)

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

    @staticmethod
    def _sync_state_from_row(row) -> PortfolioSyncState:
        return PortfolioSyncState(
            portfolio_id=int(row["portfolio_id"]),
            last_sync_at=_parse_dt(row["last_sync_at"]),
            last_sync_status=row["last_sync_status"] or SYNC_STATUS_NEVER,
            last_sync_error=row["last_sync_error"],
            symbols_requested=row["symbols_requested"],
            symbols_succeeded=row["symbols_succeeded"],
        )

    @staticmethod
    def _snapshot_from_row(row) -> SymbolFinancialSnapshot:
        return SymbolFinancialSnapshot(
            portfolio_id=int(row["portfolio_id"]),
            symbol=_normalize_symbol(row["symbol"]),
            synced_at=_parse_dt(row["synced_at"]),
            price=_optional_float(row["price"]),
            change_pct=_optional_float(row["change_pct"]),
            div_yield=_optional_float(row["div_yield"]),
            est_target=_optional_float(row["est_target"]),
            trailing_pe=_optional_float(row["trailing_pe"]),
            forward_pe=_optional_float(row["forward_pe"]),
            peg=_optional_float(row["peg"]),
            rev_growth_pct=_optional_float(row["rev_growth_pct"]),
            op_margin_pct=_optional_float(row["op_margin_pct"]),
            returns_5d=_optional_float(row["returns_5d"]),
            returns_1m=_optional_float(row["returns_1m"]),
            returns_6m=_optional_float(row["returns_6m"]),
            returns_12m=_optional_float(row["returns_12m"]),
            payload_json=row["payload_json"],
        )

    @staticmethod
    def _ensure_sync_state_conn(conn, portfolio_id: int) -> PortfolioSyncState:
        conn.execute(
            """
            INSERT OR IGNORE INTO portfolio_sync_state (portfolio_id, last_sync_status)
            VALUES (?, ?)
            """,
            (portfolio_id, SYNC_STATUS_NEVER),
        )
        row = conn.execute(
            """
            SELECT portfolio_id, last_sync_at, last_sync_status, last_sync_error,
                   symbols_requested, symbols_succeeded
            FROM portfolio_sync_state
            WHERE portfolio_id = ?
            """,
            (portfolio_id,),
        ).fetchone()
        return PortfolioRepository._sync_state_from_row(row)

    def ensure_sync_state(self, portfolio_id: int) -> PortfolioSyncState:
        with get_connection() as conn:
            return self._ensure_sync_state_conn(conn, portfolio_id)

    def get_sync_state(self, portfolio_id: int) -> PortfolioSyncState:
        return self.ensure_sync_state(portfolio_id)

    def update_sync_state(
        self,
        portfolio_id: int,
        *,
        last_sync_at: Optional[datetime] = None,
        last_sync_status: Optional[str] = None,
        last_sync_error: Optional[str] = None,
        symbols_requested: Optional[int] = None,
        symbols_succeeded: Optional[int] = None,
    ) -> PortfolioSyncState:
        self.ensure_sync_state(portfolio_id)
        fields = []
        values = []
        if last_sync_at is not None:
            fields.append("last_sync_at = ?")
            values.append(_format_sync_dt(last_sync_at))
        if last_sync_status is not None:
            fields.append("last_sync_status = ?")
            values.append(last_sync_status)
        if last_sync_error is not None:
            fields.append("last_sync_error = ?")
            values.append(last_sync_error)
        if symbols_requested is not None:
            fields.append("symbols_requested = ?")
            values.append(symbols_requested)
        if symbols_succeeded is not None:
            fields.append("symbols_succeeded = ?")
            values.append(symbols_succeeded)
        if not fields:
            return self.get_sync_state(portfolio_id)
        values.append(portfolio_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE portfolio_sync_state SET {', '.join(fields)} WHERE portfolio_id = ?",
                values,
            )
        return self.get_sync_state(portfolio_id)

    def list_symbol_snapshots(self, portfolio_id: int) -> List[SymbolFinancialSnapshot]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT portfolio_id, symbol, synced_at, price, change_pct, div_yield,
                       est_target, trailing_pe, forward_pe, peg, rev_growth_pct, op_margin_pct,
                       returns_5d, returns_1m, returns_6m, returns_12m, payload_json
                FROM symbol_financial_snapshot
                WHERE portfolio_id = ?
                ORDER BY symbol
                """,
                (portfolio_id,),
            ).fetchall()
        return [self._snapshot_from_row(r) for r in rows]

    def get_symbol_snapshot(
        self, portfolio_id: int, symbol: str
    ) -> Optional[SymbolFinancialSnapshot]:
        symbol = _normalize_symbol(symbol)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT portfolio_id, symbol, synced_at, price, change_pct, div_yield,
                       est_target, trailing_pe, forward_pe, peg, rev_growth_pct, op_margin_pct,
                       returns_5d, returns_1m, returns_6m, returns_12m, payload_json
                FROM symbol_financial_snapshot
                WHERE portfolio_id = ? AND symbol = ?
                """,
                (portfolio_id, symbol),
            ).fetchone()
        if not row:
            return None
        return self._snapshot_from_row(row)

    def upsert_symbol_snapshots(
        self, portfolio_id: int, snapshots: Iterable[SymbolFinancialSnapshot]
    ) -> int:
        rows = list(snapshots)
        if not rows:
            return 0
        with get_connection() as conn:
            for snap in rows:
                conn.execute(
                    """
                    INSERT INTO symbol_financial_snapshot (
                        portfolio_id, symbol, synced_at, price, change_pct, div_yield,
                        est_target, trailing_pe, forward_pe, peg, rev_growth_pct, op_margin_pct,
                        returns_5d, returns_1m, returns_6m, returns_12m, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                        synced_at = excluded.synced_at,
                        price = excluded.price,
                        change_pct = excluded.change_pct,
                        div_yield = excluded.div_yield,
                        est_target = excluded.est_target,
                        trailing_pe = excluded.trailing_pe,
                        forward_pe = excluded.forward_pe,
                        peg = excluded.peg,
                        rev_growth_pct = excluded.rev_growth_pct,
                        op_margin_pct = excluded.op_margin_pct,
                        returns_5d = excluded.returns_5d,
                        returns_1m = excluded.returns_1m,
                        returns_6m = excluded.returns_6m,
                        returns_12m = excluded.returns_12m,
                        payload_json = excluded.payload_json
                    """,
                    (
                        portfolio_id,
                        _normalize_symbol(snap.symbol),
                        _format_sync_dt(snap.synced_at),
                        snap.price,
                        snap.change_pct,
                        snap.div_yield,
                        snap.est_target,
                        snap.trailing_pe,
                        snap.forward_pe,
                        snap.peg,
                        snap.rev_growth_pct,
                        snap.op_margin_pct,
                        snap.returns_5d,
                        snap.returns_1m,
                        snap.returns_6m,
                        snap.returns_12m,
                        snap.payload_json,
                    ),
                )
        return len(rows)

    def delete_symbol_snapshots(self, portfolio_id: int, symbols: Iterable[str]) -> int:
        symbol_list = [_normalize_symbol(s) for s in symbols]
        if not symbol_list:
            return 0
        placeholders = ",".join("?" for _ in symbol_list)
        with get_connection() as conn:
            cur = conn.execute(
                f"""
                DELETE FROM symbol_financial_snapshot
                WHERE portfolio_id = ? AND symbol IN ({placeholders})
                """,
                (portfolio_id, *symbol_list),
            )
        return int(cur.rowcount)

    @staticmethod
    def _prune_symbol_snapshots_conn(conn, portfolio_id: int, keep_symbols: set[str]) -> int:
        if not keep_symbols:
            cur = conn.execute(
                "DELETE FROM symbol_financial_snapshot WHERE portfolio_id = ?",
                (portfolio_id,),
            )
            return int(cur.rowcount)
        placeholders = ",".join("?" for _ in keep_symbols)
        cur = conn.execute(
            f"""
            DELETE FROM symbol_financial_snapshot
            WHERE portfolio_id = ? AND symbol NOT IN ({placeholders})
            """,
            (portfolio_id, *sorted(keep_symbols)),
        )
        return int(cur.rowcount)

    def prune_symbol_snapshots(self, portfolio_id: int, keep_symbols: Iterable[str]) -> int:
        keep = {_normalize_symbol(s) for s in keep_symbols}
        with get_connection() as conn:
            return self._prune_symbol_snapshots_conn(conn, portfolio_id, keep)

    def copy_symbol_snapshots(self, source_portfolio_id: int, dest_portfolio_id: int) -> int:
        snapshots = self.list_symbol_snapshots(source_portfolio_id)
        if not snapshots:
            return 0
        cloned = [
            SymbolFinancialSnapshot(
                portfolio_id=dest_portfolio_id,
                symbol=snap.symbol,
                synced_at=snap.synced_at,
                price=snap.price,
                change_pct=snap.change_pct,
                div_yield=snap.div_yield,
                est_target=snap.est_target,
                trailing_pe=snap.trailing_pe,
                forward_pe=snap.forward_pe,
                peg=snap.peg,
                rev_growth_pct=snap.rev_growth_pct,
                op_margin_pct=snap.op_margin_pct,
                returns_5d=snap.returns_5d,
                returns_1m=snap.returns_1m,
                returns_6m=snap.returns_6m,
                returns_12m=snap.returns_12m,
                payload_json=snap.payload_json,
            )
            for snap in snapshots
        ]
        return self.upsert_symbol_snapshots(dest_portfolio_id, cloned)

    def get_symbol_ta_woi_map(self, portfolio_id: int) -> dict[str, dict[str, str]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT symbol, window_start, window_end
                FROM symbol_ta_woi
                WHERE portfolio_id = ?
                """,
                (portfolio_id,),
            ).fetchall()
        return {
            _normalize_symbol(row["symbol"]): {
                "start": row["window_start"],
                "end": row["window_end"],
            }
            for row in rows
        }

    def set_symbol_ta_woi(
        self,
        portfolio_id: int,
        symbol: str,
        window_start: str,
        window_end: str,
    ) -> None:
        symbol = _normalize_symbol(symbol)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO symbol_ta_woi (
                    portfolio_id, symbol, window_start, window_end, updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                    window_start = excluded.window_start,
                    window_end = excluded.window_end,
                    updated_at = datetime('now')
                """,
                (portfolio_id, symbol, window_start, window_end),
            )

    def clear_symbol_ta_woi(self, portfolio_id: int, symbol: str) -> None:
        symbol = _normalize_symbol(symbol)
        with get_connection() as conn:
            conn.execute(
                """
                DELETE FROM symbol_ta_woi
                WHERE portfolio_id = ? AND symbol = ?
                """,
                (portfolio_id, symbol),
            )

    def copy_symbol_ta_woi(self, source_portfolio_id: int, dest_portfolio_id: int) -> int:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT symbol, window_start, window_end
                FROM symbol_ta_woi
                WHERE portfolio_id = ?
                """,
                (source_portfolio_id,),
            ).fetchall()
            count = 0
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO symbol_ta_woi (
                        portfolio_id, symbol, window_start, window_end, updated_at
                    )
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                        window_start = excluded.window_start,
                        window_end = excluded.window_end,
                        updated_at = datetime('now')
                    """,
                    (
                        dest_portfolio_id,
                        row["symbol"],
                        row["window_start"],
                        row["window_end"],
                    ),
                )
                count += 1
            return count
