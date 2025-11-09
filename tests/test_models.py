import unittest
from models import Signal, Position
from charts.chart_interface import Candle, TrendMetrics

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

    def test_position(self):
        position = Position(
            symbol="BTCUSDT",
            interval="1h",
            candle_time=1633036800,
            open_time="2021-10-01T00:00:00Z",
            entry=43000.0,
            initial_sl=42500.0,
            initial_tp=44000.0,
            sl=42500.0,
            tp=44000.0,
            status="open",
            type="long",
            start_timestamp=1633036800.0
        )
        self.assertEqual(position.symbol, "BTCUSDT")
        self.assertEqual(position.interval, "1h")
        self.assertEqual(position.status, "open")
        self.assertEqual(position.type, "long")
        self.assertEqual(position.exit_price, 0.0)
        self.assertEqual(position.profit, -1.0)

        self.assertIsInstance(position.symbol, str)
        self.assertIsInstance(position.interval, str)
        self.assertIsInstance(position.candle_time, int)
        self.assertIsInstance(position.entry, float)
        self.assertIsInstance(position.initial_sl, float)
        self.assertIsInstance(position.initial_tp, float)
        self.assertIsInstance(position.sl, float)
        self.assertIsInstance(position.tp, float)
        self.assertIsInstance(position.status, str)
        self.assertIsInstance(position.start_timestamp, float)
        self.assertIsInstance(position.close_time, str)
        self.assertIsInstance(position.duration, str)
        self.assertIsInstance(position.exit_price, float)
        self.assertIsInstance(position.exit_reason, str)
        self.assertIsInstance(position.rr_ratio, float)
        self.assertIsInstance(position.profit, float)

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
