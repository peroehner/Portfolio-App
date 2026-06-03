"""Phase 3: holdings editor validation and save consolidation."""
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from portfolio_app.data.portfolio_loader import merge_duplicate_symbol_rows
from portfolio_app.services.portfolio_service import PortfolioService
from portfolio_app.storage.repository import PortfolioRepository
from portfolio_app.ui.holdings import (
    parse_holdings_editor_df,
    prepare_holdings_editor_df,
    validate_holdings_editor_df,
)


class HoldingsEditorLogicTestCase(unittest.TestCase):
    def test_validate_zero_shares(self):
        df = pd.DataFrame(
            [
                {
                    "Symbol": "QBTS",
                    "Shares": 0.0,
                    "AvgCost": 10.0,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 20.0,
                    "Currency": "USD",
                }
            ]
        )
        errors = validate_holdings_editor_df(df)
        self.assertTrue(any("zero" in e.lower() for e in errors))

    def test_validate_allows_missing_cost_until_save(self):
        df = pd.DataFrame(
            [
                {
                    "Symbol": "QBTS",
                    "Shares": 500.0,
                    "AvgCost": float("nan"),
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": float("nan"),
                    "Currency": "USD",
                }
            ]
        )
        self.assertEqual([], validate_holdings_editor_df(df))

    def test_validate_allows_duplicate_symbols(self):
        df = pd.DataFrame(
            [
                {
                    "Symbol": "TSLA",
                    "Shares": 10,
                    "AvgCost": 200,
                    "PurchaseDate": "2023-01-01",
                    "TargetPrice": 300,
                    "Currency": "USD",
                },
                {
                    "Symbol": "TSLA",
                    "Shares": 5,
                    "AvgCost": 250,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 320,
                    "Currency": "USD",
                },
            ]
        )
        errors = validate_holdings_editor_df(df)
        self.assertEqual([], errors)

    def test_parse_and_consolidate_on_save(self):
        editor = prepare_holdings_editor_df(
            pd.DataFrame(
                [
                    {
                        "Symbol": "TSLA",
                        "Shares": 10,
                        "AvgCost": 200,
                        "PurchaseDate": "2023-01-01",
                        "TargetPrice": 300,
                        "Currency": "USD",
                    },
                    {
                        "Symbol": "TSLA",
                        "Shares": 5,
                        "AvgCost": 250,
                        "PurchaseDate": "2024-01-01",
                        "TargetPrice": 320,
                        "Currency": "USD",
                    },
                ]
            )
        )
        parsed = parse_holdings_editor_df(editor)
        self.assertEqual(2, len(parsed))
        consolidated = merge_duplicate_symbol_rows(parsed)
        self.assertEqual(1, len(consolidated))
        self.assertAlmostEqual(15.0, float(consolidated.iloc[0]["Shares"]))
        self.assertAlmostEqual(216.666667, float(consolidated.iloc[0]["AvgCost"]), places=4)


class HoldingsEditorPersistenceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self._tmp.name)
        self._patch.start()
        self.repo = PortfolioRepository()
        self.svc = PortfolioService(self.repo)

    def tearDown(self):
        self._patch.stop()
        import os

        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_save_consolidates_in_db(self):
        user = self.repo.get_or_create_user("editor@example.com")
        portfolio = self.repo.create_portfolio(user.id, "Edit Test")
        lots = pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 100,
                    "AvgCost": 150,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 200,
                    "Currency": "USD",
                },
                {
                    "Symbol": "AAPL",
                    "Shares": 50,
                    "AvgCost": 200,
                    "PurchaseDate": "2025-01-01",
                    "TargetPrice": 250,
                    "Currency": "USD",
                },
            ]
        )
        self.svc.save_holdings(portfolio.id, lots)
        positions = self.repo.list_positions(portfolio.id)
        self.assertEqual(1, len(positions))
        self.assertAlmostEqual(150.0, positions[0].shares)
        self.assertAlmostEqual(166.666667, positions[0].avg_cost, places=4)


if __name__ == "__main__":
    unittest.main()
