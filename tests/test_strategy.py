import unittest
from strategy import StrategyAllCandles, StrategyHammerCandles

class TestStrategyAllCandles(unittest.TestCase):
    def test_generate_buy_signal(self):
        strategy = StrategyAllCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos.type, "Buy")
        self.assertEqual(pos.entry, 105.0)
        self.assertEqual(pos.sl, 90.0)
        self.assertEqual(pos.tp, 120.0)

    def test_generate_sell_signal(self):
        strategy = StrategyAllCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "105", "110", "90", "100"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos.type, "Sell")
        self.assertEqual(pos.entry, 100.0)
        self.assertEqual(pos.sl, 110.0)
        self.assertEqual(pos.tp, 90.0)

    def test_buy_signal_with_multiple_rr(self):
        strategy = StrategyAllCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0, 2.0])
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].tp, 120.0)
        self.assertEqual(positions[1].tp, 135.0)

    def test_sell_signal_with_multiple_rr(self):
        strategy = StrategyAllCandles("BTCUSDT", "1h", reward_to_risk_ratios=[0.5, 1.5])
        candles = [[0, "105", "110", "90", "100"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].tp, 95.0)
        self.assertEqual(positions[1].tp, 85.0)

    def test_no_signal_on_same_candle(self):
        strategy = StrategyAllCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]
        strategy.generate_signal(candles)
        positions = strategy.generate_signal(candles)
        self.assertEqual(positions, [])

class TestStrategyHammerCandles(unittest.TestCase):
    def test_generate_buy_signal(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "100", "106", "90", "105"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos.type, "Buy")
        self.assertEqual(pos.entry, 106.0)
        self.assertEqual(pos.sl, 90.0)
        self.assertEqual(pos.tp, 122.0)

    def test_generate_sell_signal(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "105", "115", "114", "100"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos.type, "Sell")
        self.assertEqual(pos.entry, 114.0)
        self.assertEqual(pos.sl, 115.0)
        self.assertEqual(pos.tp, 113.0)

    def test_buy_signal_with_multiple_rr(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0, 2.0])
        candles = [[0, "100", "106", "90", "105"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].tp, 122.0)
        self.assertEqual(positions[1].tp, 138.0)

    def test_sell_signal_with_multiple_rr(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[0.5, 1.5])
        candles = [[0, "105", "115", "114", "100"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].tp, 113.5)
        self.assertEqual(positions[1].tp, 112.5)

    def test_no_signal_on_same_candle(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "100", "106", "90", "105"], [1, "0", "0", "0", "0"]]
        strategy.generate_signal(candles)
        positions = strategy.generate_signal(candles)
        self.assertEqual(positions, [])

    def test_no_signal_on_non_hammer(self):
        strategy = StrategyHammerCandles("BTCUSDT", "1h", reward_to_risk_ratios=[1.0])
        candles = [[0, "100", "102", "98", "101"], [1, "0", "0", "0", "0"]]
        positions = strategy.generate_signal(candles)
        self.assertEqual(positions, [])