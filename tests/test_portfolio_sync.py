"""Phase 5: snapshot startup and refresh persistence (AT-6)."""
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd

from portfolio_app.domain.models import (
    SYNC_STATUS_NEVER,
    SYNC_STATUS_SUCCESS,
    PortfolioSyncState,
    SymbolFinancialSnapshot,
)
from portfolio_app.services.portfolio_sync import (
    build_portfolio_results_from_snapshots,
    format_last_sync_label,
    run_network_refresh,
    snapshots_by_symbol,
)
from portfolio_app.storage.repository import PortfolioRepository


class PortfolioSyncTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        self.repo = PortfolioRepository()
        self.user = self.repo.get_or_create_user("sync@example.com")
        self.portfolio = self.repo.create_portfolio(self.user.id, "Synced")

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _sample_holdings(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 10,
                    "AvgCost": 150,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 200,
                    "Currency": "USD",
                },
            ]
        )

    def test_at6_format_last_sync_never(self):
        state = PortfolioSyncState(
            portfolio_id=1,
            last_sync_status=SYNC_STATUS_NEVER,
        )
        self.assertEqual("Never synced", format_last_sync_label(state))

    def test_at6_format_last_sync_local(self):
        synced = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
        state = PortfolioSyncState(
            portfolio_id=1,
            last_sync_at=synced,
            last_sync_status=SYNC_STATUS_SUCCESS,
        )
        label = format_last_sync_label(state)
        self.assertIn("2026", label)
        self.assertNotEqual("Never synced", label)

    def test_build_results_from_snapshots_without_network(self):
        holdings = self._sample_holdings()
        synced = datetime(2026, 6, 1, tzinfo=timezone.utc)
        snap = SymbolFinancialSnapshot(
            portfolio_id=self.portfolio.id,
            symbol="AAPL",
            synced_at=synced,
            price=180.0,
            change_pct=1.2,
            div_yield=0.5,
            est_target=210.0,
            returns_5d=2.0,
            returns_1m=5.0,
            returns_6m=10.0,
            returns_12m=20.0,
        )
        snap_map = snapshots_by_symbol([snap])
        results, value, cost, target, div = build_portfolio_results_from_snapshots(
            holdings, snap_map
        )
        self.assertEqual(1, len(results))
        row = results[0]["data"]
        self.assertAlmostEqual(180.0, row["🌐 Price"])
        self.assertAlmostEqual(1.2, row["Change %"])
        self.assertAlmostEqual(2.0, row["5D"])
        self.assertGreater(value, 0)

    @patch("portfolio_app.services.portfolio_sync._apply_session_results")
    @patch("portfolio_app.services.portfolio_sync.fetch_portfolio_valuation_parallel")
    @patch("portfolio_app.services.portfolio_sync.fetch_portfolio_metadata_parallel")
    @patch("portfolio_app.services.portfolio_sync.download_close_prices")
    @patch("portfolio_app.services.portfolio_sync.get_exchange_rate")
    def test_refresh_persists_snapshots(
        self,
        mock_fx,
        mock_prices,
        mock_meta,
        mock_val,
        mock_apply,
    ):
        mock_fx.return_value = None
        mock_prices.return_value = (
            pd.DataFrame(
                {"AAPL": [175.0, 180.0]},
                index=pd.date_range("2026-05-01", periods=2),
            ),
            None,
        )
        mock_meta.return_value = {"AAPL": (200.0, 1.5, 0.6)}
        mock_val.return_value = {
            "AAPL": {
                "Trailing P/E": 28.0,
                "Forward P/E": 25.0,
                "PEG": 1.2,
                "Rev Growth %": 8.0,
                "Op Margin %": 30.0,
                "PEG P-Score": None,
                "Rev P-Score": None,
                "Margin P-Score": None,
                "P-Score": None,
                "Grade": None,
            }
        }

        holdings = self._sample_holdings()
        self.repo.replace_positions(self.portfolio.id, holdings)

        sync_state = run_network_refresh(
            holdings, self.portfolio.id, repo=self.repo
        )

        self.assertEqual(SYNC_STATUS_SUCCESS, sync_state.last_sync_status)
        self.assertIsNotNone(sync_state.last_sync_at)
        snap = self.repo.get_symbol_snapshot(self.portfolio.id, "AAPL")
        self.assertIsNotNone(snap)
        self.assertAlmostEqual(180.0, snap.price)
        self.assertAlmostEqual(200.0, snap.est_target)
        mock_apply.assert_called_once()


if __name__ == "__main__":
    unittest.main()
