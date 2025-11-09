from dataclasses import dataclass
from typing import Optional
import unittest
from strategies.strategy_hammer_candles import StrategyHammerCandles, HammerCandle, Candle
from models import Signal

@dataclass
class Expected:
    type:   str
    entry:  float
    tp:     float
    sl:     float

class TestStrategyHammerCandles(unittest.TestCase):
    def setUp(self):
        self.strategy = StrategyHammerCandles()

    def _assert_signal(self, result, expected: Optional[Expected]):
        if expected is None:
            self.assertIsNone(result)
            return
        self.assertIsNotNone(result)
        self.assertEqual(result.type, expected.type)
        self.assertEqual(result.entry, expected.entry)
        self.assertEqual(result.tp, expected.tp)
        self.assertEqual(result.sl, expected.sl)

    def test_hammer_scenarios(self):
        dummy_candle = Candle(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        scenarios = [
            { "candles": [Candle(0, 100, 111, 80, 110, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": Expected(type="Short", entry=110.0, tp=90.0, sl=130.0) },
            { "candles": [Candle(0, 100, 120, 89, 90, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": Expected(type="Long", entry=90.0, tp=110.0, sl=70.0) },
            { "candles": [Candle(0, 100, 101, 99, 102, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 102, 103, 101, 100, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 100, 105, 95, 100, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 100, 105, 95, 100, 0, 0, 0, 0, 0, 0)], "expected": None }, # insufficient_candles: 1 candle 
            { "candles": [], "expected": None },  # insufficient_candles: 0 candle
        ]
        
        for scenario in scenarios:
            result = self.strategy.generate_signal(scenario["candles"])
            self._assert_signal(result, scenario["expected"])

    def test_insufficient_candles(self):
        # 0 candles
        self.assertIsNone(self.strategy.generate_signal([]))
        # 1 candle
        single = Candle(0, 100, 105, 95, 150, 0, 0, 0, 0, 0, 0)
        self.assertIsNone(self.strategy.generate_signal([single]))

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
