import unittest
from strategies.strategy_hammer_candles import StrategyHammerCandles, HammerCandle
from models import Signal

class TestStrategyHammerCandles(unittest.TestCase):
    def setUp(self):
        self.strategy = StrategyHammerCandles()

    def test_bullish_hammer(self):
        candle = [0, "100", "111", "80", "110"]  # open, high, low, close
        dummy = [1, "0", "0", "0", "0"]
        result = self.strategy.generate_signal([candle, dummy])
        self.assertIsInstance(result, Signal)
        self.assertEqual(result.type, "Long")
        self.assertEqual(result.entry, 110.0)
        self.assertEqual(result.sl, 90.0)
        self.assertEqual(result.tp, 130.0)

    def test_bearish_hammer(self):
        candle = [0, "100", "120", "89", "90"]
        dummy = [1, "0", "0", "0", "0"]
        result = self.strategy.generate_signal([candle, dummy])
        self.assertIsInstance(result, Signal)
        self.assertEqual(result.type, "Short")
        self.assertEqual(result.entry, 90.0)
        self.assertEqual(result.sl, 110)
        self.assertEqual(result.tp, 70)

    def test_non_hammer_green(self):
        candle = [0, "100", "101", "99", "102"]
        dummy = [1, "0", "0", "0", "0"]
        result = self.strategy.generate_signal([candle, dummy])
        self.assertIsNone(result)

    def test_non_hammer_red(self):
        candle = [0, "102", "103", "101", "100"]
        dummy = [1, "0", "0", "0", "0"]
        result = self.strategy.generate_signal([candle, dummy])
        self.assertIsNone(result)

    def test_zero_body_size(self):
        candle = [0, "100", "105", "95", "100"]
        dummy = [1, "0", "0", "0", "0"]
        result = self.strategy.generate_signal([candle, dummy])
        self.assertIsNone(result)

    def test_insufficient_candles(self):
        result = self.strategy.generate_signal([])  # 0 candles
        self.assertIsNone(result)
        result = self.strategy.generate_signal([[0, "100", "105", "90", "104"]])  # 1 candle
        self.assertIsNone(result)

    def test_candle_hammer_type_direct(self):
        self.assertEqual(
            self.strategy._candle_hammer_type(100, 102, 90, 105),
            HammerCandle.BULLISH_HAMMER
        )
        self.assertEqual(
            self.strategy._candle_hammer_type(105, 120, 104, 100),
            HammerCandle.BEARISH_HAMMER
        )
        self.assertEqual(
            self.strategy._candle_hammer_type(100, 101, 99, 102),
            HammerCandle.NON_HAMMER
        )
