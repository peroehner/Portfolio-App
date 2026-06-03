"""AT-7: Save as new portfolio — holdings + snapshots + sync state."""
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from portfolio_app.domain.models import SYNC_STATUS_SUCCESS, SymbolFinancialSnapshot
from portfolio_app.services.portfolio_service import PortfolioService
from portfolio_app.storage.repository import PortfolioRepository


class SaveAsPortfolioTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        self.repo = PortfolioRepository()
        self.svc = PortfolioService(self.repo)
        self.user = self.repo.get_or_create_user("saveas@example.com")

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_at7_save_as_copies_holdings_snapshots_and_sync(self):
        source = self.repo.create_portfolio(self.user.id, "BigThing")
        holdings = pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 10,
                    "AvgCost": 150,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 200,
                    "Currency": "USD",
                },
                {
                    "Symbol": "MSFT",
                    "Shares": 5,
                    "AvgCost": 300,
                    "PurchaseDate": "2024-06-01",
                    "TargetPrice": 400,
                    "Currency": "USD",
                },
            ]
        )
        self.repo.replace_positions(source.id, holdings)
        synced = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
        self.repo.upsert_symbol_snapshots(
            source.id,
            [
                SymbolFinancialSnapshot(
                    portfolio_id=source.id,
                    symbol="AAPL",
                    synced_at=synced,
                    price=180.0,
                ),
                SymbolFinancialSnapshot(
                    portfolio_id=source.id,
                    symbol="MSFT",
                    synced_at=synced,
                    price=320.0,
                ),
            ],
        )
        self.repo.update_sync_state(
            source.id,
            last_sync_at=synced,
            last_sync_status=SYNC_STATUS_SUCCESS,
            symbols_requested=2,
            symbols_succeeded=2,
        )

        new_active = self.svc.save_as_portfolio(
            self.user.id,
            source.id,
            "BigThing 2026",
            holdings,
        )

        self.assertNotEqual(source.id, new_active.portfolio_id)
        self.assertEqual("BigThing 2026", new_active.name)
        self.assertEqual(2, len(new_active.holdings_df))
        self.assertEqual(
            ["AAPL", "MSFT"],
            sorted(new_active.holdings_df["Symbol"].astype(str).str.upper().tolist()),
        )

        aapl_snap = self.repo.get_symbol_snapshot(new_active.portfolio_id, "AAPL")
        self.assertIsNotNone(aapl_snap)
        self.assertAlmostEqual(180.0, aapl_snap.price)

        dest_sync = self.repo.get_sync_state(new_active.portfolio_id)
        self.assertEqual(SYNC_STATUS_SUCCESS, dest_sync.last_sync_status)
        self.assertEqual(synced, dest_sync.last_sync_at)
        self.assertEqual(2, dest_sync.symbols_succeeded)

        user = self.repo.get_user(self.user.id)
        self.assertEqual(new_active.portfolio_id, user.last_portfolio_id)

    def test_save_as_rejects_duplicate_name(self):
        self.repo.create_portfolio(self.user.id, "Taken")
        source = self.repo.create_portfolio(self.user.id, "Source")
        holdings = pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 1,
                    "AvgCost": 100,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 120,
                    "Currency": "USD",
                }
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            self.svc.save_as_portfolio(self.user.id, source.id, "Taken", holdings)
        self.assertIn("already exists", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
