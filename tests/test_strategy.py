import unittest
from strategy import Strategy

class TestStrategy(unittest.TestCase):
    def test_generate_buy_signal(self):
        strategy = Strategy("BTCUSDT", "1h", reward_to_risk_ratio=1.0)
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        pos = strategy.generate_signal(candles)
        self.assertEqual(pos.type, "Buy")
        self.assertEqual(pos.entry, 105.0)
        self.assertEqual(pos.sl, 90.0)
        self.assertEqual(pos.tp, 120.0)  # TP = 105 + (105 - 90) * 1.0

    def test_generate_sell_signal(self):
        strategy = Strategy("BTCUSDT", "1h", reward_to_risk_ratio=1.0)
        candles = [[0, "105", "110", "90", "100"], [1, "0", "0", "0", "0"]]
        pos = strategy.generate_signal(candles)
        self.assertEqual(pos.type, "Sell")
        self.assertEqual(pos.entry, 100.0)
        self.assertEqual(pos.sl, 110.0)
        self.assertEqual(pos.tp, 90.0)  # TP = 100 - (110 - 100) * 1.0

    def test_buy_signal_with_custom_rr(self):
        strategy = Strategy("BTCUSDT", "1h", reward_to_risk_ratio=2.0)
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        pos = strategy.generate_signal(candles)
        self.assertEqual(pos.tp, 135.0)  # TP = 105 + (105 - 90) * 2.0

    def test_sell_signal_with_custom_rr(self):
        strategy = Strategy("BTCUSDT", "1h", reward_to_risk_ratio=0.5)
        candles = [[0, "105", "110", "90", "100"], [1, "0", "0", "0", "0"]]
        pos = strategy.generate_signal(candles)
        self.assertEqual(pos.tp, 95.0)  # TP = 100 - (110 - 100) * 0.5

    def test_no_signal_on_same_candle(self):
        strategy = Strategy("BTCUSDT", "1h", reward_to_risk_ratio=1.0)
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        strategy.generate_signal(candles)
        pos = strategy.generate_signal(candles)
        self.assertIsNone(pos)
