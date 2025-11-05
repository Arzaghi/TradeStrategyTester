import unittest
from unittest.mock import MagicMock, patch
from coin_watcher import CoinWatcher
from models import Signal, Position
from datetime import datetime
import time

class TestCoinWatcher(unittest.TestCase):
    def setUp(self):
        self.symbol = "BTCUSDT"
        self.interval = "15m"
        self.api = MagicMock()
        self.strategy = MagicMock()
        self.strategy.REQUIRED_CANDLES = 2
        self.notifier = MagicMock()
        self.watcher = CoinWatcher(self.symbol, self.interval, self.api, self.strategy, self.notifier)

    def test_first_run_skips_time_check(self):
        self.watcher.last_processed_candle_time = None
        self.assertTrue(self.watcher._is_new_candle_due())

    def test_new_candle_due_logic(self):
        now = int(time.time() * 1000)
        interval_ms = 15 * 60_000
        self.watcher.last_processed_candle_time = now - interval_ms
        self.assertTrue(self.watcher._is_new_candle_due())

    def test_no_new_candle_due(self):
        now = int(time.time() * 1000)
        self.watcher.last_processed_candle_time = now
        self.assertFalse(self.watcher._is_new_candle_due())

    def test_watch_skips_if_no_new_candle_due(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=False)
        result = self.watcher.watch()
        self.api.get_candles.assert_not_called()
        self.assertIsNone(result)

    def test_watch_skips_if_duplicate_candle(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)
        self.api.get_candles.return_value = [[123, "100", "110", "90", "105"], [123, "105", "115", "95", "110"]]
        self.watcher.last_processed_candle_time = 123
        result = self.watcher.watch()
        self.notifier.send_message.assert_not_called()
        self.assertIsNone(result)

    def test_watch_sends_alert_on_signal(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)
        self.api.get_candles.return_value = [[123, "100", "110", "90", "105"], [124, "105", "115", "95", "110"]]
        self.strategy.generate_signal = MagicMock(return_value=Signal(entry=105.0, sl=95.0, tp=115.0, type="Long"))
        self.watcher.watch()
        self.notifier.send_message.assert_called_once()
        args, kwargs = self.notifier.send_message.call_args
        self.assertIn("Entry", args[0])
        self.assertIn("Stop Loss", args[0])
        self.assertEqual(kwargs["parse_mode"], "Markdown")

    def test_watch_no_alert_if_no_signal(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)
        self.api.get_candles.return_value = [[123, "100", "110", "90", "105"], [124, "105", "115", "95", "110"]]
        self.strategy.generate_signal = MagicMock(return_value=None)
        result = self.watcher.watch()
        self.notifier.send_message.assert_not_called()
        self.assertIsNone(result)

    def test_send_alert_does_not_throw_if_notifier_is_none(self):
        watcher = CoinWatcher(symbol="BTCUSDT", interval="15m", api=None, strategy=None, notifier=None)
        signal = Signal(entry=100.0, sl=90.0, tp=110.0, type="Long")
        try:
            watcher.send_alert(signal)
        except Exception as e:
            self.fail(f"send_alert raised an exception when notifier was None: {e}")

    def test_watch_returns_position_on_signal(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)
        self.api.get_candles.return_value = [[1698768000000, "100", "110", "90", "105"], [1698768900000  , "105", "115", "95", "110"]]
        self.strategy.generate_signal = MagicMock(return_value=Signal(entry=105.0, sl=95.0, tp=115.0, type="Long"))

        position = self.watcher.watch()

        self.assertIsInstance(position, Position)
        self.assertEqual(position.symbol, self.symbol)
        self.assertEqual(position.interval, self.interval)
        self.assertEqual(position.candle_time, 1698768900000)
        self.assertEqual(position.entry, 105.0)
        self.assertEqual(position.sl, 95.0)
        self.assertEqual(position.tp, 115.0)
        self.assertEqual(position.status, "open")
        self.assertEqual(position.type, "Long")
        self.assertGreater(position.start_timestamp, 0)
        self.assertGreater(position.start_timestamp, 0)
        self.assertEqual(position.open_time, "2023-10-31 16:15:00")

    def test_watch_returns_none_if_no_signal(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)
        self.api.get_candles.return_value = [[123, "100", "110", "90", "105"], [124, "105", "115", "95", "110"]]
        self.strategy.generate_signal = MagicMock(return_value=None)

        position = self.watcher.watch()

        self.assertIsNone(position)


    def test_5m_interval_exact(self):
        timeframe = "5m"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 2, 20, 5, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_5m_interval_offset(self):
        timeframe = "5m"
        last_candle = datetime(2025, 11, 2, 20, 2, 0)
        expected = datetime(2025, 11, 2, 20, 5, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_15m_interval_exact(self):
        timeframe = "15m"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 2, 20, 15, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_15m_interval_offset(self):
        timeframe = "15m"
        last_candle = datetime(2025, 11, 2, 20, 1, 0)
        expected = datetime(2025, 11, 2, 20, 15, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_30m_interval_exact(self):
        timeframe = "30m"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 2, 20, 30, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_30m_interval_offset(self):
        timeframe = "30m"
        last_candle = datetime(2025, 11, 2, 20, 10, 0)
        expected = datetime(2025, 11, 2, 20, 30, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_1h_interval_exact(self):
        timeframe = "1h"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 2, 21, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_1h_interval_offset(self):
        timeframe = "1h"
        last_candle = datetime(2025, 11, 2, 20, 45, 0)
        expected = datetime(2025, 11, 2, 21, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_2h_interval_exact(self):
        timeframe = "2h"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 2, 22, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_2h_interval_offset(self):
        timeframe = "2h"
        last_candle = datetime(2025, 11, 2, 21, 15, 0)
        expected = datetime(2025, 11, 2, 22, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_4h_interval_exact(self):
        timeframe = "4h"
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        expected = datetime(2025, 11, 3, 0, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_4h_interval_offset(self):
        timeframe = "4h"
        last_candle = datetime(2025, 11, 2, 21, 30, 0)
        expected = datetime(2025, 11, 3, 0, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_1d_interval(self):
        timeframe = "1d"
        last_candle = datetime(2025, 11, 2, 23, 59, 59)
        expected = datetime(2025, 11, 3, 0, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_1w_interval_1(self):
        timeframe = "1w"
        last_candle = datetime(2025, 11, 2, 12, 0, 0)
        expected = datetime(2025, 11, 3, 0, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_1w_interval_2(self):
        timeframe = "1w"
        last_candle = datetime(2025, 11, 3, 0, 0, 0)
        expected = datetime(2025, 11, 10, 0, 0, 0)
        result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
        self.assertEqual(result, expected)

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            timeframe = "1X"
            last_candle = datetime(2025, 11, 2, 12, 0, 0)
            expected = datetime(2025, 11, 9, 0, 0, 0)
            result = CoinWatcher.get_next_candle_time(last_candle.timestamp() * 1000, timeframe)
            self.assertEqual(result, expected)

    def test_multiple_ticks_no_new_candle(self):
        # Set last_processed_candle_time to now
        now = int(time.time() * 1000)
        self.watcher.last_processed_candle_time = now

        # Patch _is_new_candle_due to simulate no new candle
        self.watcher._is_new_candle_due = MagicMock(return_value=False)

        for _ in range(5):
            self.watcher.watch()

        self.api.get_candles.assert_not_called()
        self.notifier.send_message.assert_not_called()

    def test_multiple_ticks_with_new_candle(self):
        # Simulate new candle due
        self.watcher._is_new_candle_due = MagicMock(return_value=True)

        # Simulate candles with increasing timestamps
        base_time = int(time.time() * 1000)
        self.api.get_candles.side_effect = [
            [[base_time, "100", "110", "90", "105"], [base_time + 900_000, "105", "115", "95", "110"]],
            [[base_time + 900_000, "105", "115", "95", "110"], [base_time + 2 * 900_000, "110", "120", "100", "115"]],
        ]

        self.strategy.generate_signal.return_value = None

        # First watch should update last_processed_candle_time
        self.watcher.watch()
        self.assertEqual(self.watcher.last_processed_candle_time, base_time + 900_000)

        # Second watch should also call API
        self.watcher.watch()
        self.assertEqual(self.watcher.last_processed_candle_time, base_time + 2 * 900_000)

        self.assertEqual(self.api.get_candles.call_count, 2)
        self.notifier.send_message.assert_not_called()

    def test_alert_sent_when_signal_generated(self):
        self.watcher._is_new_candle_due = MagicMock(return_value=True)

        candle_time = int(time.time() * 1000)
        self.api.get_candles.return_value = [[candle_time, "100", "110", "90", "105"], [candle_time + 900_000, "105", "115", "95", "110"]]
        self.strategy.generate_signal.return_value = Signal(entry=105.0, sl=95.0, tp=115.0, type="Long")

        self.watcher.watch()

        self.notifier.send_message.assert_called_once()
        args, kwargs = self.notifier.send_message.call_args
        self.assertIn("Entry", args[0])
        self.assertIn("Stop Loss", args[0])
        self.assertIn("Long", args[0])
        self.assertEqual(kwargs["parse_mode"], "Markdown")

    def test_5m_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "5m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 4, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 5, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_5m_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "5m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 2, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 4, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 5, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_15m_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "15m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 14, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 15, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_15m_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "15m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 5, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 14, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 15, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_30m_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "30m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 29, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 30, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_30m_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "30m", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 10, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 29, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 30, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_1h_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "1h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 23, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_1h_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "1h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 22, 5, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 23, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_2h_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "2h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 21, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 22, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_2h_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "2h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 19, 30, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 19, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 20, 0, 0).timestamp()):
            self

    def test_4h_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "4h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 20, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 23, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 3, 0, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_4h_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "4h", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 16, 50, 50)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 19, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 20, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_1d_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "1d", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 0, 0, 0)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 23, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 3, 0, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_1d_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "1d", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 2, 2, 15, 50)
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 2, 23, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 3, 0, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())

    def test_1w_interval_boundary(self):
        watcher = CoinWatcher(self.symbol, "1w", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 3, 0, 0, 0)  # Monday
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 9, 23, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 10, 0, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())
    
    def test_1w_interval_offset(self):
        watcher = CoinWatcher(self.symbol, "1w", self.api, self.strategy, self.notifier)
        last_candle = datetime(2025, 11, 6, 15, 50, 40)  # Thursday
        watcher.last_processed_candle_time = int(last_candle.timestamp() * 1000)

        with patch("time.time", return_value=last_candle.timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 9, 23, 59, 59).timestamp()):
            self.assertFalse(watcher._is_new_candle_due())

        with patch("time.time", return_value=datetime(2025, 11, 10, 0, 0, 0).timestamp()):
            self.assertTrue(watcher._is_new_candle_due())
