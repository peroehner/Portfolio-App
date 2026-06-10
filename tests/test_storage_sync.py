"""Phase 1: portfolio sync state and symbol snapshot persistence."""
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from portfolio_app.domain.models import (
    SYNC_STATUS_PARTIAL,
    SYNC_STATUS_SUCCESS,
    SymbolFinancialSnapshot,
)
from portfolio_app.storage.database import SCHEMA_USER_VERSION, get_connection, init_database
from portfolio_app.storage.repository import PortfolioRepository


class StorageSyncTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        self.repo = PortfolioRepository()

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_schema_migration_version(self):
        with get_connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertEqual(SCHEMA_USER_VERSION, version)
        self.assertIn("portfolio_sync_state", tables)
        self.assertIn("symbol_financial_snapshot", tables)
        self.assertIn("symbol_ta_woi", tables)

    def test_create_portfolio_has_sync_state(self):
        user = self.repo.get_or_create_user("phase1@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Test")
        state = self.repo.get_sync_state(portfolio.id)
        self.assertEqual(portfolio.id, state.portfolio_id)
        self.assertIsNone(state.last_sync_at)
        self.assertEqual("never", state.last_sync_status)

    def test_upsert_and_list_snapshots(self):
        user = self.repo.get_or_create_user("snap@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Snap")
        synced = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        snapshots = [
            SymbolFinancialSnapshot(
                portfolio_id=portfolio.id,
                symbol="aapl",
                synced_at=synced,
                price=190.5,
                change_pct=1.2,
                est_target=220.0,
            ),
            SymbolFinancialSnapshot(
                portfolio_id=portfolio.id,
                symbol="MSFT",
                synced_at=synced,
                price=420.0,
                div_yield=0.8,
            ),
        ]
        count = self.repo.upsert_symbol_snapshots(portfolio.id, snapshots)
        self.assertEqual(2, count)
        loaded = self.repo.list_symbol_snapshots(portfolio.id)
        self.assertEqual({"AAPL", "MSFT"}, {s.symbol for s in loaded})
        aapl = self.repo.get_symbol_snapshot(portfolio.id, "AAPL")
        self.assertIsNotNone(aapl)
        self.assertAlmostEqual(190.5, aapl.price)
        self.assertAlmostEqual(1.2, aapl.change_pct)

    def test_update_sync_state(self):
        user = self.repo.get_or_create_user("sync@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Sync")
        synced = datetime(2026, 6, 2, 10, 30, 0, tzinfo=timezone.utc)
        updated = self.repo.update_sync_state(
            portfolio.id,
            last_sync_at=synced,
            last_sync_status=SYNC_STATUS_SUCCESS,
            symbols_requested=10,
            symbols_succeeded=10,
        )
        self.assertEqual(SYNC_STATUS_SUCCESS, updated.last_sync_status)
        self.assertEqual(10, updated.symbols_requested)
        self.assertEqual(10, updated.symbols_succeeded)
        self.assertIsNotNone(updated.last_sync_at)

    def test_replace_positions_prunes_snapshots(self):
        user = self.repo.get_or_create_user("prune@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Prune")
        synced = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.repo.upsert_symbol_snapshots(
            portfolio.id,
            [
                SymbolFinancialSnapshot(
                    portfolio_id=portfolio.id,
                    symbol="AAPL",
                    synced_at=synced,
                    price=1.0,
                ),
                SymbolFinancialSnapshot(
                    portfolio_id=portfolio.id,
                    symbol="MSFT",
                    synced_at=synced,
                    price=2.0,
                ),
            ],
        )
        holdings = pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 10,
                    "AvgCost": 100,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 150,
                    "Currency": "USD",
                }
            ]
        )
        self.repo.replace_positions(portfolio.id, holdings)
        remaining = self.repo.list_symbol_snapshots(portfolio.id)
        self.assertEqual(["AAPL"], [s.symbol for s in remaining])

    def test_copy_symbol_snapshots(self):
        user = self.repo.get_or_create_user("copy@example.com")
        source = self.repo.create_portfolio(user.id, "Source")
        dest = self.repo.create_portfolio(user.id, "Dest")
        synced = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.repo.upsert_symbol_snapshots(
            source.id,
            [
                SymbolFinancialSnapshot(
                    portfolio_id=source.id,
                    symbol="GOOGL",
                    synced_at=synced,
                    price=140.0,
                    peg=1.5,
                )
            ],
        )
        copied = self.repo.copy_symbol_snapshots(source.id, dest.id)
        self.assertEqual(1, copied)
        snap = self.repo.get_symbol_snapshot(dest.id, "GOOGL")
        self.assertIsNotNone(snap)
        self.assertAlmostEqual(140.0, snap.price)
        self.assertAlmostEqual(1.5, snap.peg)

    def test_delete_portfolio_cascades_sync_tables(self):
        user = self.repo.get_or_create_user("del@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Gone")
        synced = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.repo.update_sync_state(
            portfolio.id,
            last_sync_at=synced,
            last_sync_status=SYNC_STATUS_PARTIAL,
        )
        self.repo.upsert_symbol_snapshots(
            portfolio.id,
            [
                SymbolFinancialSnapshot(
                    portfolio_id=portfolio.id,
                    symbol="X",
                    synced_at=synced,
                    price=1.0,
                )
            ],
        )
        self.repo.delete_portfolio(user.id, portfolio.id)
        with get_connection() as conn:
            sync_row = conn.execute(
                "SELECT 1 FROM portfolio_sync_state WHERE portfolio_id = ?",
                (portfolio.id,),
            ).fetchone()
            snap_row = conn.execute(
                "SELECT 1 FROM symbol_financial_snapshot WHERE portfolio_id = ?",
                (portfolio.id,),
            ).fetchone()
        self.assertIsNone(sync_row)
        self.assertIsNone(snap_row)


class LegacyDatabaseMigrationTestCase(unittest.TestCase):
    """Simulate pre-v1 DB and verify migration adds sync tables."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        with get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    last_portfolio_id INTEGER
                );
                CREATE TABLE portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO users (email) VALUES ('legacy@example.com');
                INSERT INTO portfolios (user_id, name) VALUES (1, 'Legacy');
                """
            )

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_legacy_db_migrates_on_init(self):
        init_database()
        repo = PortfolioRepository()
        state = repo.get_sync_state(1)
        self.assertEqual(1, state.portfolio_id)
        self.assertEqual("never", state.last_sync_status)


if __name__ == "__main__":
    unittest.main()
