"""Cross-view table sort state."""
import unittest

import pandas as pd

from portfolio_app.ui.table_sort import (
    SORT_ASC,
    SORT_DESC,
    _cycle_sort,
    reorder_by_symbol_order,
    sort_dataframe,
    symbol_order_from_sorted_df,
)


class TableSortTestCase(unittest.TestCase):
    def _sample_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Symbol": "MSFT", "📈 Total %": 10.0},
                {"Symbol": "AAPL", "📈 Total %": 30.0},
                {"Symbol": "GOOGL", "📈 Total %": 20.0},
            ]
        )

    def test_sort_dataframe_desc(self):
        df = self._sample_df()
        sorted_df = sort_dataframe(df, "📈 Total %", SORT_DESC)
        symbols = list(sorted_df["Symbol"])
        self.assertEqual(["AAPL", "GOOGL", "MSFT"], symbols)

    def test_symbol_order_from_sorted(self):
        df = sort_dataframe(self._sample_df(), "📈 Total %", SORT_ASC)
        self.assertEqual(["MSFT", "GOOGL", "AAPL"], symbol_order_from_sorted_df(df))

    def test_cycle_sort_asc_desc_clear(self):
        self.assertEqual(
            {"column": "Shares", "direction": SORT_ASC},
            _cycle_sort(None, "Shares"),
        )
        self.assertEqual(
            {"column": "Shares", "direction": SORT_DESC},
            _cycle_sort({"column": "Shares", "direction": SORT_ASC}, "Shares"),
        )
        self.assertIsNone(
            _cycle_sort({"column": "Shares", "direction": SORT_DESC}, "Shares"),
        )

    def test_reorder_by_symbol_order(self):
        df = pd.DataFrame(
            [
                {"Symbol": "AAPL", "5D": 1.0},
                {"Symbol": "MSFT", "5D": 2.0},
            ]
        )
        reordered = reorder_by_symbol_order(df, ["MSFT", "AAPL"])
        self.assertEqual(["MSFT", "AAPL"], list(reordered["Symbol"]))


if __name__ == "__main__":
    unittest.main()
