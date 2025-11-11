import unittest
from unittest.mock import MagicMock
from models import Signal, Position
from charts.chart_interface import Candle, Timeframe, TrendMetrics

class TestModels(unittest.TestCase):
    def _sample_candle(self, timestamp=1630000000000, open_p=100.0, close_p=102.0):
        return Candle(
            timestamp=timestamp,
            open=open_p,
            high=105.0,
            low=95.0,
            close=close_p,
            volume=1500.0,
            close_time=timestamp + 5000,
            quote_volume=153000.0,
            trade_count=120,
            taker_buy_base_volume=700.0,
            taker_buy_quote_volume=71500.0,
        )

    def test_candle_equality_uses_key_attributes(self):
        a = self._sample_candle(timestamp=1, open_p=10.0, close_p=11.0)
        # same timestamp/open/close but different other fields
        b = Candle(
            timestamp=1,
            open=10.0,
            high=999.0,
            low=-999.0,
            close=11.0,
            volume=0.0,
            close_time=2,
            quote_volume=0.0,
            trade_count=1,
            taker_buy_base_volume=0.0,
            taker_buy_quote_volume=0.0,
        )
        self.assertEqual(a,b)
        self.assertNotEqual(a, "not a candle")

    def test_candle_inequality_when_key_changes(self):
        base = self._sample_candle(timestamp=42, open_p=5.0, close_p=6.0)
        diff_close = self._sample_candle(timestamp=42, open_p=5.0, close_p=7.0)
        diff_open = self._sample_candle(timestamp=42, open_p=4.0, close_p=6.0)
        diff_timestamp = self._sample_candle(timestamp=43, open_p=5.0, close_p=6.0)
        self.assertNotEqual(base, diff_close)
        self.assertNotEqual(base, diff_open)
        self.assertNotEqual(base, diff_timestamp)

    def test_candle_field_types(self):
        c = self._sample_candle()
        self.assertIsInstance(c.timestamp, int)
        self.assertIsInstance(c.open, float)
        self.assertIsInstance(c.high, float)
        self.assertIsInstance(c.low, float)
        self.assertIsInstance(c.close, float)
        self.assertIsInstance(c.volume, float)
        self.assertIsInstance(c.close_time, int)
        self.assertIsInstance(c.quote_volume, float)
        self.assertIsInstance(c.trade_count, int)
        self.assertIsInstance(c.taker_buy_base_volume, float)
        self.assertIsInstance(c.taker_buy_quote_volume, float)

    def test_generate_position_assigns_all_fields_correctly(self):
        chart = MagicMock()
        chart.symbol = "BTCUSDT"
        chart.timeframe = Timeframe.MINUTE_5

        signal = Signal(entry=100.0, sl=95.0, tp=110.0, type="long")

        position = Position.generate_position(chart, signal)

        self.assertEqual(position.symbol, "BTCUSDT")
        self.assertEqual(position.interval, Timeframe.MINUTE_5)
        self.assertEqual(position.entry, 100.0)
        self.assertEqual(position.initial_sl, 95.0)
        self.assertEqual(position.initial_tp, 110.0)
        self.assertEqual(position.sl, 95.0)
        self.assertEqual(position.tp, 110.0)
        self.assertEqual(position.type, "long")

    def test_generate_position_sets_defaults(self):
        chart = MagicMock()
        chart.symbol = "ETHUSDT"
        chart.timeframe = Timeframe.HOURS_1

        signal = Signal(entry=200.0, sl=190.0, tp=220.0, type="short")

        position = Position.generate_position(chart, signal)

        self.assertEqual(position.status, "")
        self.assertEqual(position.open_timestamp, 0)
        self.assertEqual(position.close_timestamp, 0)
        self.assertEqual(position.duration, 0)
        self.assertEqual(position.exit_price, 0)
        self.assertEqual(position.exit_reason, "")
        self.assertEqual(position.profit, 0)

    def test_generate_position_with_mocked_chart_and_signal(self):
        chart = MagicMock()
        chart.symbol = "XRPUSDT"
        chart.timeframe = Timeframe.MINUTE_15

        signal = Signal(entry=0.5, sl=0.45, tp=0.6, type="long")

        position = Position.generate_position(chart, signal)

        self.assertEqual(position.symbol, "XRPUSDT")
        self.assertEqual(position.interval, Timeframe.MINUTE_15)
        self.assertEqual(position.entry, 0.5)
        self.assertEqual(position.initial_sl, 0.45)
        self.assertEqual(position.initial_tp, 0.6)
        self.assertEqual(position.type, "long")

    def test_signal(self):
        s = Signal(entry=100.0, sl=95.0, tp=110.0, type="long")
        self.assertIsInstance(s.entry, float)
        self.assertIsInstance(s.sl, float)
        self.assertIsInstance(s.tp, float)
        self.assertIsInstance(s.type, str)

    def test_trend_metrics(self):
        tm = TrendMetrics(atr=1.23, adx=20.0, plus_di=25.0, minus_di=10.0)
        self.assertIsInstance(tm.atr, float)
        self.assertIsInstance(tm.adx, float)
        self.assertIsInstance(tm.plus_di, float)
        self.assertIsInstance(tm.minus_di, float)
