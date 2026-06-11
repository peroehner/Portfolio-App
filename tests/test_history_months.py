import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from portfolio_app.config import (
    HISTORY_MONTHS_DEFAULT,
    HISTORY_MONTHS_MAX,
    HISTORY_MONTHS_PERSIST_KEY,
    HISTORY_MONTHS_WIDGET_KEY,
    SYNCED_HISTORY_MONTHS_KEY,
)
from portfolio_app.data.market_data import (
    clamp_history_months,
    download_close_prices,
    get_ticker_ohlc_history,
)
from portfolio_app.ui.history_controls import (
    history_months,
    month_options_from_hist,
    on_history_months_change,
    portfolio_ohlc_from_pick,
    set_history_months,
    _sync_slider_from_persisted,
)


class TestHistoryMonths(unittest.TestCase):
    def test_clamp_history_months(self):
        self.assertEqual(1, clamp_history_months(0))
        self.assertEqual(HISTORY_MONTHS_MAX, clamp_history_months(99))
        self.assertEqual(6, clamp_history_months(6))
        self.assertEqual(HISTORY_MONTHS_MAX, clamp_history_months(None))

    @patch("portfolio_app.ui.history_controls.st.session_state", new_callable=dict)
    def test_history_months_defaults_to_twelve(self, session):
        st_mock = MagicMock()
        st_mock.session_state = session
        with patch("portfolio_app.ui.history_controls.st", st_mock):
            self.assertEqual(HISTORY_MONTHS_DEFAULT, 12)
            self.assertEqual(HISTORY_MONTHS_DEFAULT, history_months())

    @patch("portfolio_app.ui.history_controls.st.session_state", new_callable=dict)
    def test_persisted_months_survive_widget_unmount(self, session):
        session[HISTORY_MONTHS_PERSIST_KEY] = 18
        st_mock = MagicMock()
        st_mock.session_state = session
        with patch("portfolio_app.ui.history_controls.st", st_mock):
            self.assertEqual(18, history_months())
            synced = _sync_slider_from_persisted()
            self.assertEqual(18, synced)
            self.assertEqual(18, session[HISTORY_MONTHS_WIDGET_KEY])

    @patch("portfolio_app.ui.history_controls.st.session_state", new_callable=dict)
    def test_set_history_months_updates_persist_only(self, session):
        st_mock = MagicMock()
        st_mock.session_state = session
        with patch("portfolio_app.ui.history_controls.st", st_mock):
            self.assertEqual(9, set_history_months(9))
            self.assertEqual(9, session[HISTORY_MONTHS_PERSIST_KEY])

    @patch("portfolio_app.ui.history_controls.st.session_state", new_callable=dict)
    def test_history_change_triggers_resync_when_synced_differs(self, session):
        session[HISTORY_MONTHS_PERSIST_KEY] = 12
        session[SYNCED_HISTORY_MONTHS_KEY] = 12
        session[HISTORY_MONTHS_WIDGET_KEY] = 6
        st_mock = MagicMock()
        st_mock.session_state = session
        with patch("portfolio_app.ui.history_controls.st", st_mock):
            with patch("portfolio_app.ui.history_controls._request_resync_for_history_change") as mock_resync:
                on_history_months_change()
                self.assertEqual(6, session[HISTORY_MONTHS_PERSIST_KEY])
                mock_resync.assert_called_once()

    def test_month_options_from_hist_uses_actual_index(self):
        index = pd.date_range("2024-06-01", periods=120, freq="B")
        hist = pd.DataFrame({"Close": range(len(index))}, index=index)
        options = month_options_from_hist(hist)
        self.assertEqual(options[0], "2024-06")
        self.assertTrue(options[-1].startswith("2024-") or options[-1].startswith("2025-"))
        self.assertGreater(len(options), 1)

    def test_month_options_from_hist_empty_for_snapshot_stub(self):
        hist = pd.DataFrame({"Close": [180.0]})
        self.assertEqual([], month_options_from_hist(hist))

    def test_portfolio_ohlc_from_pick_uses_synced_close(self):
        index = pd.date_range("2025-01-01", periods=3, freq="D")
        pick = {"hist": pd.DataFrame({"Close": [1.0, 2.0, 3.0]}, index=index)}
        frame = portfolio_ohlc_from_pick(pick)
        self.assertFalse(frame.empty)
        self.assertIn("High", frame.columns)
        self.assertIn("Low", frame.columns)

    @patch("portfolio_app.data.market_data.yf")
    def test_get_ticker_ohlc_history_uses_start_when_months_set(self, yf_mock):
        ticker = MagicMock()
        yf_mock.Ticker.return_value = ticker
        index = pd.date_range("2025-01-01", periods=3, freq="D")
        ticker.history.return_value = pd.DataFrame(
            {"Close": [1.0, 2.0, 3.0], "High": [1.0, 2.0, 3.0], "Low": [1.0, 2.0, 3.0]},
            index=index,
        )
        get_ticker_ohlc_history.clear()
        frame = get_ticker_ohlc_history("AAPL", history_months=3)
        self.assertFalse(frame.empty)
        ticker.history.assert_called_once()
        kwargs = ticker.history.call_args.kwargs
        self.assertIn("start", kwargs)
        self.assertTrue(kwargs.get("auto_adjust"))

    @patch("portfolio_app.data.market_data.yf")
    def test_download_close_prices_uses_months_window(self, yf_mock):
        index = pd.date_range("2025-01-01", periods=3, freq="D")
        yf_mock.download.return_value = pd.DataFrame(
            {"Close": [1.0, 2.0, 3.0], "Open": [1.0, 2.0, 3.0]},
            index=index,
        )
        frame, _note = download_close_prices(["AAPL"], history_months=6)
        self.assertFalse(frame.empty)
        kwargs = yf_mock.download.call_args.kwargs
        self.assertIn("start", kwargs)


if __name__ == "__main__":
    unittest.main()
