from dataclasses import dataclass
from typing import Optional
import unittest
from unittest.mock import MagicMock
from charts.chart_interface import Candle, TrendDirection, Timeframe
from strategies.strategy_hammer_candles import StrategyHammerCandles, HammerCandle
from strategies.strategy_fbody_macd import StrategyFullBodyInMacdZones, FullBodyCandle
from strategies.strategy_htf_macd import StrategyHTF_MCD
from structs.signal import Signal

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

class TestStrategyFullBodyInMacdZones(unittest.TestCase):
    def setUp(self):
        self.strategy = StrategyFullBodyInMacdZones()

    def test_full_body_green_detection(self):
        result = self.strategy._candle_full_body_type(open_=80, high=101, low=79, close=100)
        self.assertEqual(result, FullBodyCandle.FULL_BODY_GREEN)

    def test_full_body_red_detection(self):
        result = self.strategy._candle_full_body_type(open_=100, high=101, low=79, close=80)
        self.assertEqual(result, FullBodyCandle.FULL_BODY_RED)

    def test_non_full_body_candle(self):
        result = self.strategy._candle_full_body_type(open_=100, high=105, low=95, close=101)
        self.assertEqual(result, FullBodyCandle.NONE)

    def test_generate_signal_long(self):
        chart = MagicMock()
        chart.get_recent_candles.return_value = [
            MagicMock(open=80, high=101, low=79, close=100),
            MagicMock()  # second candle, unused
        ]
        chart.get_macd_trend.return_value = TrendDirection.UPTREND

        signal = self.strategy.generate_signal(chart)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.type, "Long")
        self.assertEqual(signal.entry, 100)
        self.assertEqual(signal.sl, 80)  # R =1
        self.assertEqual(signal.tp, 160) # RR=3

    def test_generate_signal_short(self):
        chart = MagicMock()
        chart.get_recent_candles.return_value = [
            MagicMock(open=100, high=101, low=79, close=80),
            MagicMock()
        ]
        chart.get_macd_trend.return_value = TrendDirection.DOWNTREND

        signal = self.strategy.generate_signal(chart)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.type, "Short")
        self.assertEqual(signal.entry, 80)
        self.assertEqual(signal.sl, 100)
        self.assertEqual(signal.tp, 20)

    def test_generate_signal_none_due_to_macd(self):
        chart = MagicMock()
        chart.get_recent_candles.return_value = [
            MagicMock(open=80, high=101, low=79, close=100),
            MagicMock()
        ]
        chart.get_macd_trend.return_value = TrendDirection.DOWNTREND  # Green candle in downtrend MACD.

        signal = self.strategy.generate_signal(chart)
        self.assertIsNone(signal)

    def test_generate_signal_none_due_to_candle(self):
        chart = MagicMock()
        chart.get_recent_candles.return_value = [
            MagicMock(open=100, high=101, low=79, close=80),
            MagicMock()
        ]
        chart.get_macd_trend.return_value = TrendDirection.UPTREND # Red candle in downtrend MACD.

        signal = self.strategy.generate_signal(chart)
        self.assertIsNone(signal)

    def test_generate_signal_insufficient_data(self):
        chart = MagicMock()
        chart.get_recent_candles.return_value = [MagicMock()]
        chart.get_macd_trend.return_value = TrendDirection.NEUTRAL

        signal = self.strategy.generate_signal(chart)
        self.assertIsNone(signal)

class TestStrategyHTF_MCD(unittest.TestCase):
    def setUp(self):
        self.strategy = StrategyHTF_MCD()

        self.chart = MagicMock()
        self.chart.symbol = "BTCUSDT"
        self.chart.timeframe = Timeframe.MINUTE_15
        self.chart.get_macd_trend = MagicMock(return_value=TrendDirection.UPTREND)

        def mock_chart(symbol, tf):
            mock = MagicMock()
            mock.symbol = symbol
            mock.timeframe = tf
            mock.get_macd_trend = MagicMock(return_value=TrendDirection.UPTREND)
            return mock

        # Patch type(chart) to return mock_chart
        self.chart_type = MagicMock(side_effect=mock_chart)
        self.strategy._get_higher_timeframes_macd_trend.__globals__["type"] = lambda obj: self.chart_type

    def test_signal_long_full_body_green_uptrend(self):
        # Setup candle with full body green
        candle = MagicMock()
        candle.open = 100
        candle.high = 120
        candle.low = 99
        candle.close = 119

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.UPTREND

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.type, "Long")
        self.assertEqual(signal.entry, 119)
        self.assertEqual(signal.sl, 100)
        self.assertEqual(signal.tp, 119 + (119 - 100) * 3)

    def test_signal_short_full_body_red_downtrend(self):
        self.chart.timeframe = Timeframe.MINUTE_30

        candle = MagicMock()
        candle.open = 100
        candle.high = 101
        candle.low = 79
        candle.close = 80

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.DOWNTREND

        def mock_chart(symbol, tf):
            mock = MagicMock()
            mock.symbol = symbol
            mock.timeframe = tf
            mock.get_macd_trend = MagicMock(return_value=TrendDirection.DOWNTREND)
            return mock

        # Patch type(chart) to return mock_chart
        self.chart_type = MagicMock(side_effect=mock_chart)
        self.strategy._get_higher_timeframes_macd_trend.__globals__["type"] = lambda obj: self.chart_type

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.type, "Short")
        self.assertEqual(signal.entry, 80)
        self.assertEqual(signal.sl, 100)
        self.assertEqual(signal.tp, 80 - 3 * (100 - 80))

    def test_no_signal_if_not_full_body(self):
        candle = MagicMock()
        candle.open = 100
        candle.high = 105
        candle.low = 99
        candle.close = 101  # Small body, large shadows

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.UPTREND

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)

    def test_no_signal_if_macd_neutral(self):
        candle = MagicMock()
        candle.open = 100
        candle.high = 105
        candle.low = 99
        candle.close = 104

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.NEUTRAL

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)

    def test_no_signal_if_higher_timeframes_not_agreed1(self):
        # Setup a full body green candle
        candle = MagicMock()
        candle.open = 100
        candle.high = 120
        candle.low = 99
        candle.close = 119

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.UPTREND

        # Simulate mixed higher timeframe trends: one UPTREND, one DOWNTREND
        def mock_chart(symbol, tf):
            mock = MagicMock()
            mock.symbol = symbol
            mock.timeframe = tf
            mock.get_macd_trend = MagicMock(return_value=TrendDirection.DOWNTREND)
            return mock

        self.chart_type = MagicMock(side_effect=mock_chart)
        self.strategy._get_higher_timeframes_macd_trend.__globals__["type"] = lambda obj: self.chart_type

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)

    def test_no_signal_if_higher_timeframes_not_agreed2(self):
        # Setup a full body red candle
        candle = MagicMock()
        candle.open = 100
        candle.high = 101
        candle.low = 79
        candle.close = 80

        self.chart.get_recent_candles.return_value = [candle, MagicMock()]
        self.chart.get_macd_trend.return_value = TrendDirection.DOWNTREND

        def mock_chart(symbol, tf):
            mock = MagicMock()
            mock.symbol = symbol
            mock.timeframe = tf
            mock.get_macd_trend = MagicMock(return_value=TrendDirection.UPTREND)
            return mock

        self.chart_type = MagicMock(side_effect=mock_chart)
        self.strategy._get_higher_timeframes_macd_trend.__globals__["type"] = lambda obj: self.chart_type

        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)

    def test_no_signal_if_not_enough_candles(self):
        self.chart.get_recent_candles.return_value = [MagicMock()]
        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)

    def test_no_signal_if_timeframe_not_supported(self):
        self.chart.timeframe = Timeframe.MINUTE_5
        signal = self.strategy.generate_signal(self.chart)
        self.assertIsNone(signal)
