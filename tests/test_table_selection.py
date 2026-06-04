"""Table selection must follow display order and grid widget symbols."""
import unittest
from unittest.mock import patch

import pandas as pd

from portfolio_app.ui.detail_panel import _analysis_symbols
from portfolio_app.ui.table import rows_to_symbols
from portfolio_app.ui.table_sort import sort_dataframe, row_indices_for_symbols


class TableSelectionTestCase(unittest.TestCase):
    def _sample_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Symbol": "CRWV", "📈 Total %": 5.0},
                {"Symbol": "OTEX", "📈 Total %": 15.0},
                {"Symbol": "SAP", "📈 Total %": 10.0},
            ]
        )

    def test_row_index_maps_to_display_order_after_sort(self):
        unsorted = self._sample_df()
        sorted_df = sort_dataframe(unsorted, "📈 Total %", "desc")
        # OTEX is first row in sorted view; same index in unsorted df is CRWV.
        row_idx = 0
        wrong_symbols, _ = rows_to_symbols([row_idx], unsorted)
        right_symbols, _ = rows_to_symbols([row_idx], sorted_df)
        self.assertEqual(["CRWV"], wrong_symbols)
        self.assertEqual(["OTEX"], right_symbols)

    def test_symbols_remap_to_sorted_indices(self):
        sorted_df = sort_dataframe(self._sample_df(), "📈 Total %", "desc")
        indices = row_indices_for_symbols(sorted_df, ["OTEX"])
        self.assertEqual([0], indices)
        self.assertEqual("OTEX", sorted_df.iloc[indices[0]]["Symbol"])

    @patch("portfolio_app.ui.detail_panel.st.session_state", new_callable=dict)
    def test_analysis_symbols_prefers_table_focus_over_full_list(self, session):
        session["selected_symbols"] = []
        session["table_sel_rows"] = [2]
        session["selected_symbol"] = "OTEX"
        session["ticker_liste"] = ["CRWV", "SAP", "OTEX"]
        self.assertEqual(["OTEX"], _analysis_symbols())


if __name__ == "__main__":
    unittest.main()
