from dataclasses import dataclass
from typing import Optional
import unittest
from unittest.mock import MagicMock
from charts.chart_interface import Candle
from strategies.strategy_hammer_candles import StrategyHammerCandles, HammerCandle

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
            { "candles": [Candle(0, 100, 111, 80, 110, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": Expected(type="Long", entry=110.0, tp=130, sl=90.0) },
            { "candles": [Candle(0, 100, 120, 89, 90, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": Expected(type="Short", entry=90.0, tp=70.0, sl=110.0) },
            { "candles": [Candle(0, 100, 101, 99, 102, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 102, 103, 101, 100, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 100, 105, 95, 100, 0, 0, 0, 0, 0, 0), dummy_candle], "expected": None },
            { "candles": [Candle(0, 100, 105, 95, 100, 0, 0, 0, 0, 0, 0)], "expected": None }, # insufficient_candles: 1 candle 
            { "candles": [], "expected": None },  # insufficient_candles: 0 candle
        ]
        
        for scenario in scenarios:
            test_chart = MagicMock()
            test_chart.get_recent_candles.return_value = scenario["candles"]
            result = self.strategy.generate_signal(test_chart)
            self._assert_signal(result, scenario["expected"])

    def test_candle_hammer_type_direct(self):
        self.assertEqual(
            self.strategy._candle_hammer_type(100, 111, 80, 110),
            HammerCandle.BULLISH_HAMMER
        )
        self.assertEqual(
            self.strategy._candle_hammer_type(100, 120, 89, 90),
            HammerCandle.BEARISH_HAMMER
        )
        self.assertEqual(
            self.strategy._candle_hammer_type(100, 101, 99, 102),
            HammerCandle.NON_HAMMER
        )
