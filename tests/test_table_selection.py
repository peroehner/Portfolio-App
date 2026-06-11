"""Table selection must follow display order and grid widget symbols."""
import unittest
from unittest.mock import patch

import pandas as pd

from portfolio_app.ui.detail_panel import _analysis_symbols
from portfolio_app.ui.table import prepare_table_selection_before_render, rows_to_symbols
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

    @patch("portfolio_app.ui.table.st")
    def test_grid_sync_keeps_ta_chip_focus(self, st_mock):
        class SessionState(dict):
            def __getattr__(self, name):
                return self[name]

            def __setattr__(self, name, value):
                self[name] = value

        session = SessionState(
            selected_symbols=["CRWV", "OTEX", "SAP"],
            selected_symbol="OTEX",
            ta_chart_symbol="OTEX",
            ta_nav_index=1,
            table_sel_rows=[2],
            portfolio_grid_0={
                "symbols": ["CRWV", "OTEX", "SAP"],
                "rows": [0, 1, 2],
            },
        )
        st_mock.session_state = session
        display_df = self._sample_df()

        from portfolio_app.ui.table import sync_selection_from_grid_widget

        sync_selection_from_grid_widget("portfolio_grid_0", display_df)

        self.assertEqual("OTEX", session["selected_symbol"])
        self.assertEqual(1, session["ta_nav_index"])

    def test_apply_grid_selection_keeps_ta_chip_focus(self):
        from portfolio_app.ui.table import apply_grid_selection

        display_df = self._sample_df()
        with patch("portfolio_app.ui.table.st") as st_mock:
            class SessionState(dict):
                def __getattr__(self, name):
                    return self[name]

                def __setattr__(self, name, value):
                    self[name] = value

            session = SessionState(
                selected_symbols=["CRWV", "OTEX", "SAP"],
                selected_symbol="OTEX",
                ta_chart_symbol="OTEX",
                table_sel_rows=[0, 1, 2],
            )
            st_mock.session_state = session
            result = {"symbols": ["CRWV", "OTEX", "SAP"], "rows": [0, 1, 2]}
            apply_grid_selection(result, display_df)
        self.assertEqual("OTEX", session["selected_symbol"])
        self.assertEqual("OTEX", session["ta_chart_symbol"])

    @patch("portfolio_app.ui.table.st")
    def test_technical_controls_preserve_ta_chip_focus(self, st_mock):
        class SessionState(dict):
            def __getattr__(self, name):
                return self[name]

            def __setattr__(self, name, value):
                self[name] = value

        session = SessionState(
            selected_symbols=["GILD", "SAP"],
            selected_symbol="GILD",
            ta_chart_symbol="GILD",
            ta_nav_index=0,
            table_sel_rows=[0, 1],
            sel_start_ui="2024-12",
            sel_end_ui="2026-06",
            calc_fib_start="2024-11",
            calc_fib_end="2026-06",
            fibo_trend_inspect=True,
            sticky_woi_enabled=False,
            _last_tech_controls_state={
                "sel_start_ui": "2024-11",
                "sel_end_ui": "2026-06",
                "calc_fib_start": "2024-11",
                "calc_fib_end": "2026-06",
                "fibo_trend_inspect": True,
                "sticky_woi_enabled": False,
            },
        )
        st_mock.session_state = session
        display_df = pd.DataFrame(
            [
                {"Symbol": "GILD", "📈 Total %": 5.0},
                {"Symbol": "SAP", "📈 Total %": 10.0},
            ]
        )

        prepare_table_selection_before_render(display_df)

        self.assertEqual("GILD", session["selected_symbol"])
        self.assertEqual("GILD", session["ta_chart_symbol"])


if __name__ == "__main__":
    unittest.main()
