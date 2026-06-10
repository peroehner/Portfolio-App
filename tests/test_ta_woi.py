import os
import tempfile
import unittest
from unittest.mock import patch

from portfolio_app.storage.repository import PortfolioRepository
from portfolio_app.ui.export import build_multi_export_datasets


class TestTaWoi(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        self.repo = PortfolioRepository()
        self.user = self.repo.get_or_create_user("woi@test.local")
        self.portfolio = self.repo.create_portfolio(self.user.id, "WOI Test")

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_symbol_ta_woi_roundtrip(self):
        self.repo.set_symbol_ta_woi(self.portfolio.id, "AAPL", "2024-01", "2024-06")
        mapping = self.repo.get_symbol_ta_woi_map(self.portfolio.id)
        self.assertEqual(mapping["AAPL"]["start"], "2024-01")
        self.assertEqual(mapping["AAPL"]["end"], "2024-06")
        self.repo.clear_symbol_ta_woi(self.portfolio.id, "AAPL")
        self.assertNotIn("AAPL", self.repo.get_symbol_ta_woi_map(self.portfolio.id))

    def test_export_uses_sticky_override(self):
        text = build_multi_export_datasets(
            ["AAPL", "MSFT"],
            "2025-01",
            "2025-06",
            all_results=[],
            symbol_windows={
                "AAPL": {"start": "2024-03", "end": "2024-09", "is_sticky": True},
                "MSFT": {"start": "2025-01", "end": "2025-06", "is_sticky": False},
            },
        )
        self.assertIn("Default time window: 2025-01 → 2025-06", text)
        self.assertIn("Pinned WoI overrides: AAPL", text)
        self.assertEqual(text.count("[PORTFOLIO EXPORT"), 1)


if __name__ == "__main__":
    unittest.main()
