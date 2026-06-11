import os
import tempfile
import unittest
from unittest.mock import patch

from portfolio_app.services.ta_woi_service import (
    STICKY_WOI_CHECKBOX_KEY,
    on_window_controls_change,
)
from portfolio_app.storage.repository import PortfolioRepository
from portfolio_app.ui.detail_panel import _sidebar_panel_html
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

    @patch("portfolio_app.services.ta_woi_service.st")
    def test_window_controls_do_not_commit_calc_until_reanalyse(self, st_mock):
        class SessionState(dict):
            def __getattr__(self, name):
                return self[name]

            def __setattr__(self, name, value):
                self[name] = value

        session = SessionState(
            ta_chart_symbol="GILD",
            sel_start_ui="2024-12",
            sel_end_ui="2026-06",
            calc_fib_start="2024-11",
            calc_fib_end="2026-06",
            **{STICKY_WOI_CHECKBOX_KEY: True},
        )
        st_mock.session_state = session
        on_window_controls_change()
        self.assertEqual("2024-11", session["calc_fib_start"])
        self.assertEqual("2024-12", session["sel_start_ui"])
        self.assertEqual("GILD", session["ta_chart_symbol"])

    def test_sidebar_panel_html_renders_fib_rows(self):
        html = _sidebar_panel_html(
            ['<div class="ta-price-pill"><span>Current</span><strong>$10.00</strong></div>'],
            "2024-06",
            "2026-06",
            "",
            "T1 Bullish: 2024-06-01 → 2025-03-07",
            '<div class="ta-fib-list"><div class="ta-fib-row">'
            '<span class="ta-fib-lbl">0% (High)</span>'
            '<span class="ta-fib-val">$100.00</span></div></div>',
        )
        self.assertIn("ta-fib-list", html)
        self.assertIn("T1 Bullish", html)
        self.assertNotIn("\n        <div class=\"ta-fib-anchor\">", html)


if __name__ == "__main__":
    unittest.main()
