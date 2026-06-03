"""Phase 2: CSV import replace/merge engine (spec AT-1–AT-3)."""
import io
import unittest

import pandas as pd

from portfolio_app.data.portfolio_loader import _read_portfolio_csv
from portfolio_app.services.import_engine import (
    ImportMode,
    apply_import,
    build_import_preview,
    parse_csv_preflight,
)


def _holdings_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
    return df


class ImportEngineTestCase(unittest.TestCase):
    def test_at1_replace_import(self):
        current = _holdings_df(
            [
                {
                    "Symbol": "MSFT",
                    "Shares": 10,
                    "AvgCost": 300,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 400,
                    "Currency": "USD",
                },
                {
                    "Symbol": "AAPL",
                    "Shares": 100,
                    "AvgCost": 150,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 200,
                    "Currency": "USD",
                },
            ]
        )
        raw = pd.read_csv(
            io.StringIO(
                "Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency\n"
                "AAPL;50;200;2025-01-01;250;USD\n"
                "GOOGL;20;140;2024-06-01;200;USD\n"
            ),
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        csv_df, _ = parse_csv_preflight(raw)
        applied = apply_import(current, csv_df, ImportMode.REPLACE)
        symbols = set(applied.holdings_df["Symbol"])
        self.assertEqual({"AAPL", "GOOGL"}, symbols)
        self.assertIn("MSFT", applied.preview.removed)
        self.assertIn("GOOGL", applied.preview.added)

    def test_at2_merge_import_overlap(self):
        current = _holdings_df(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 100,
                    "AvgCost": 150,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 200,
                    "Currency": "USD",
                }
            ]
        )
        raw = pd.read_csv(
            io.StringIO(
                "Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency\n"
                "AAPL;50;200;2025-06-01;250;USD\n"
            ),
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        csv_df, _ = parse_csv_preflight(raw)
        applied = apply_import(current, csv_df, ImportMode.MERGE)
        row = applied.holdings_df.iloc[0]
        self.assertEqual("AAPL", row["Symbol"])
        self.assertAlmostEqual(150.0, float(row["Shares"]))
        self.assertAlmostEqual(166.666667, float(row["AvgCost"]), places=4)
        self.assertEqual("2024-01-01", pd.to_datetime(row["PurchaseDate"]).strftime("%Y-%m-%d"))
        self.assertIn("AAPL", applied.preview.updated)

    def test_at3_csv_n_lots_per_symbol(self):
        raw = _read_portfolio_csv(
            io.StringIO(
                "Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency\n"
                "SAP;1.500;125,50;2024-01-15;200,00;EUR\n"
                "SAP;500;130,00;2025-03-01;210,00;EUR\n"
            )
        )
        csv_df, rejected = parse_csv_preflight(raw)
        self.assertEqual([], rejected)
        self.assertEqual(1, len(csv_df))
        row = csv_df.iloc[0]
        self.assertEqual("SAP", row["Symbol"])
        self.assertAlmostEqual(2000.0, float(row["Shares"]))
        self.assertEqual("2024-01-15", pd.to_datetime(row["PurchaseDate"]).strftime("%Y-%m-%d"))

    def test_merge_keeps_db_only_symbols(self):
        current = _holdings_df(
            [
                {
                    "Symbol": "MSFT",
                    "Shares": 10,
                    "AvgCost": 300,
                    "PurchaseDate": "2024-01-01",
                    "TargetPrice": 400,
                    "Currency": "USD",
                }
            ]
        )
        raw = pd.read_csv(
            io.StringIO(
                "Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency\n"
                "AAPL;5;100;2024-01-01;150;USD\n"
            ),
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        csv_df, _ = parse_csv_preflight(raw)
        preview = build_import_preview(current, csv_df, ImportMode.MERGE)
        self.assertIn("MSFT", preview.unchanged)
        self.assertIn("AAPL", preview.added)
        self.assertEqual([], preview.removed)

    def test_reject_zero_shares(self):
        raw = pd.read_csv(
            io.StringIO(
                "Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency\n"
                "AAPL;0;100;2024-01-01;150;USD\n"
            ),
            sep=";",
            dtype=str,
            keep_default_na=False,
        )
        csv_df, rejected = parse_csv_preflight(raw)
        self.assertTrue(csv_df.empty)
        self.assertEqual(1, len(rejected))
        self.assertIn("zero", rejected[0].reason.lower())


if __name__ == "__main__":
    unittest.main()
