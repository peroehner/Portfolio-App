"""ROI Value / Invest calculated columns."""
import unittest

import pandas as pd

from portfolio_app.ui.table import enrich_roi_calculated_columns, _roi_pinned_bottom_row


class RoiCalculatedColumnsTestCase(unittest.TestCase):
    def test_value_invest_and_target_vals(self):
        df = pd.DataFrame(
            [
                {
                    "Symbol": "AAPL",
                    "Shares": 10,
                    "🌐 Price": 150.0,
                    "Cost/Share": 100.0,
                    "📈 Target": 200.0,
                    "Est Target": 180.0,
                },
            ]
        )
        out = enrich_roi_calculated_columns(df)
        row = out.iloc[0]
        self.assertEqual(1500.0, row["Value"])
        self.assertEqual(1000.0, row["Invest"])
        self.assertEqual(2000.0, row["📈 Target Val"])
        self.assertEqual(1800.0, row["Est Target Val"])

    def test_pinned_bottom_row_sums(self):
        df = enrich_roi_calculated_columns(
            pd.DataFrame(
                [
                    {
                        "Symbol": "AAPL",
                        "Shares": 10,
                        "🌐 Price": 100.0,
                        "Cost/Share": 80.0,
                        "📈 Target": 120.0,
                        "Est Target": 110.0,
                        "Div Income": 50.0,
                    },
                    {
                        "Symbol": "MSFT",
                        "Shares": 5,
                        "🌐 Price": 200.0,
                        "Cost/Share": 150.0,
                        "📈 Target": 250.0,
                        "Est Target": 220.0,
                        "Div Income": 25.0,
                    },
                ]
            )
        )
        footer = _roi_pinned_bottom_row(df)
        self.assertEqual("Sum", footer["Symbol"])
        self.assertEqual(75.0, footer["Div Income"])
        self.assertEqual(1550.0, footer["Invest"])
        self.assertEqual(2000.0, footer["Value"])
        self.assertEqual(2450.0, footer["📈 Target Val"])
        self.assertEqual(2200.0, footer["Est Target Val"])


if __name__ == "__main__":
    unittest.main()
