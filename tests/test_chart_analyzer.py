import unittest
import time
from unittest.mock import MagicMock, patch
from chart_analyzer import ChartAnalyzer
from models import Signal, Position
from datetime import datetime
from charts.binance_chart import BinanceChart, Timeframe


class TestChartAnalyzer(unittest.TestCase):
    def setUp(self):
        self.chart = BinanceChart("BTCUSDT", Timeframe.MINUTE_15)
        self.chart._binance_api = MagicMock()
        self.chart._binance_api.get_candles.return_value = [
            [1698767900000, 100.0, 105.0, 95.0, 102.0, 1500.0, 1630000005000, 153000.0, 120, 700.0, 71500.0, None],
            [1698768900000, 100.0, 105.0, 95.0, 102.0, 1500.0, 1630000005000, 153000.0, 120, 700.0, 71500.0, None]
        ]
        
        self.strategy = MagicMock()
        self.strategy.REQUIRED_CANDLES = 2
        self.chart_analyzer = ChartAnalyzer(self.chart, self.strategy)

    def test_first_run_skips_time_check(self):
        self.chart_analyzer.last_processed_candle_time = None
        self.assertTrue(self.chart_analyzer._is_new_candle_due())

    def test_new_candle_due_logic(self):
        now = int(time.time() * 1000)
        interval_ms = 15 * 60_000
        self.chart_analyzer.last_processed_candle_time = now - interval_ms
        self.assertTrue(self.chart_analyzer._is_new_candle_due())

    def test_no_new_candle_due(self):
        now = int(time.time() * 1000)
        self.chart_analyzer.last_processed_candle_time = now
        self.assertFalse(self.chart_analyzer._is_new_candle_due())

    def test_analyze_skips_if_no_new_candle_due(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=False)
        result = self.chart_analyzer.analyze()
        self.chart._binance_api.get_candles.assert_not_called()
        self.assertIsNone(result)

    def test_analyze_skips_if_duplicate_candle(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=True)
        self.chart._binance_api.get_candles.return_value = [[123, "100", "110", "90", "105"], [123, "105", "115", "95", "110"]]
        self.chart_analyzer.last_processed_candle_time = 123
        result = self.chart_analyzer.analyze()
        self.assertIsNone(result)

    def test_analyze_sends_alert_on_signal(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=True)
        self.strategy.generate_signal = MagicMock(return_value=Signal(entry=105.0, sl=95.0, tp=115.0, type="Long"))
        self.chart_analyzer.analyze()

    def test_analyze_no_alert_if_no_signal(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=True)
        self.strategy.generate_signal = MagicMock(return_value=None)
        result = self.chart_analyzer.analyze()
        self.assertIsNone(result)

    def test_analyze_returns_position_on_signal(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=True)
        self.chart._binance_api.get_candles.return_value = [
            [1698767900000, 100.0, 105.0, 95.0, 102.0, 1500.0, 1630000005000, 153000.0, 120, 700.0, 71500.0, None],
            [1698768900000, 100.0, 105.0, 95.0, 102.0, 1500.0, 1630000005000, 153000.0, 120, 700.0, 71500.0, None]
        ]
        self.strategy.generate_signal = MagicMock(return_value=Signal(entry=105.0, sl=95.0, tp=115.0, type="Long"))

        position = self.chart_analyzer.analyze()

        self.assertIsInstance(position, Position)
        self.assertEqual(position.symbol, self.chart.symbol)
        self.assertEqual(position.interval, self.chart.timeframe)
        self.assertEqual(position.candle_time, 1698768900000)
        self.assertEqual(position.entry, 105.0)
        self.assertEqual(position.sl, 95.0)
        self.assertEqual(position.tp, 115.0)
        self.assertEqual(position.status, "open")
        self.assertEqual(position.type, "Long")
        self.assertGreater(position.start_timestamp, 0)
        self.assertEqual(position.open_time, "2023-10-31 16:15:00")

    def test_analyze_returns_none_if_no_signal(self):
        self.chart_analyzer._is_new_candle_due = MagicMock(return_value=True)

        self.strategy.generate_signal = MagicMock(return_value=None)

        position = self.chart_analyzer.analyze()

        self.assertIsNone(position)

    def test_get_next_candle_time(self):
        cases = [
            (Timeframe.MINUTE_5,  datetime(2025,11,2,20,0,0),  datetime(2025,11,2,20,5,0)),
            (Timeframe.MINUTE_5,  datetime(2025,11,2,20,2,0),  datetime(2025,11,2,20,5,0)),
            (Timeframe.MINUTE_15, datetime(2025,11,2,20,0,0),  datetime(2025,11,2,20,15,0)),
            (Timeframe.MINUTE_15, datetime(2025,11,2,20,1,0),  datetime(2025,11,2,20,15,0)),
            (Timeframe.MINUTE_30, datetime(2025,11,2,20,0,0),  datetime(2025,11,2,20,30,0)),
            (Timeframe.MINUTE_30, datetime(2025,11,2,20,10,0), datetime(2025,11,2,20,30,0)),
            (Timeframe.HOURS_1,   datetime(2025,11,2,20,0,0),  datetime(2025,11,2,21,0,0)),
            (Timeframe.HOURS_1,   datetime(2025,11,2,20,45,0), datetime(2025,11,2,21,0,0)),
            (Timeframe.HOURS_2,   datetime(2025,11,2,20,0,0),  datetime(2025,11,2,22,0,0)),
            (Timeframe.HOURS_2,   datetime(2025,11,2,21,15,0), datetime(2025,11,2,22,0,0)),
            (Timeframe.HOURS_4,   datetime(2025,11,2,20,0,0),  datetime(2025,11,3,0,0,0)),
            (Timeframe.HOURS_4,   datetime(2025,11,2,21,30,0), datetime(2025,11,3,0,0,0)),
            (Timeframe.DAY_1,     datetime(2025,11,2,23,59,59), datetime(2025,11,3,0,0,0)),
            (Timeframe.WEEK_1,    datetime(2025,11,2,12,0,0),   datetime(2025,11,3,0,0,0)),
            (Timeframe.WEEK_1,    datetime(2025,11,3,0,0,0),    datetime(2025,11,10,0,0,0)),
        ]

        for tf, last_dt, expected in cases:
            result = ChartAnalyzer.get_next_candle_time(int(last_dt.timestamp() * 1000), tf)
            self.assertEqual(result, expected)

    def test_is_new_candle_due(self):
        scenarios = [
            {"timeframe": Timeframe.MINUTE_5,   "last": datetime(2025, 11, 2, 22, 0, 0),    "checks": [(datetime(2025, 11, 2, 22, 0, 0), False),    (datetime(2025, 11, 2, 22, 4, 59), False),  (datetime(2025, 11, 2, 22, 5, 0), True)]    },
            {"timeframe": Timeframe.MINUTE_5,   "last": datetime(2025, 11, 2, 22, 2, 0),    "checks": [(datetime(2025, 11, 2, 22, 2, 0), False),    (datetime(2025, 11, 2, 22, 4, 59), False),  (datetime(2025, 11, 2, 22, 5, 0), True)]    },
            {"timeframe": Timeframe.MINUTE_15,  "last": datetime(2025, 11, 2, 22, 0, 0),    "checks": [(datetime(2025, 11, 2, 22, 0, 0), False),    (datetime(2025, 11, 2, 22, 14, 59), False), (datetime(2025, 11, 2, 22, 15, 0), True)]   },
            {"timeframe": Timeframe.MINUTE_15,  "last": datetime(2025, 11, 2, 22, 5, 0),    "checks": [(datetime(2025, 11, 2, 22, 5, 0), False),    (datetime(2025, 11, 2, 22, 14, 59), False), (datetime(2025, 11, 2, 22, 15, 0), True)]   },
            {"timeframe": Timeframe.MINUTE_30,  "last": datetime(2025, 11, 2, 22, 0, 0),    "checks": [(datetime(2025, 11, 2, 22, 0, 0), False),    (datetime(2025, 11, 2, 22, 29, 59), False), (datetime(2025, 11, 2, 22, 30, 0), True)]   },
            {"timeframe": Timeframe.MINUTE_30,  "last": datetime(2025, 11, 2, 22, 10, 0),   "checks": [(datetime(2025, 11, 2, 22, 10, 0), False),   (datetime(2025, 11, 2, 22, 29, 59), False), (datetime(2025, 11, 2, 22, 30, 0), True)]   },
            {"timeframe": Timeframe.HOURS_1,    "last": datetime(2025, 11, 2, 22, 0, 0),    "checks": [(datetime(2025, 11, 2, 22, 0, 0), False),    (datetime(2025, 11, 2, 22, 59, 59), False), (datetime(2025, 11, 2, 23, 0, 0), True)]    },
            {"timeframe": Timeframe.HOURS_1,    "last": datetime(2025, 11, 2, 22, 5, 0),    "checks": [(datetime(2025, 11, 2, 22, 5, 0), False),    (datetime(2025, 11, 2, 22, 59, 59), False), (datetime(2025, 11, 2, 23, 0, 0), True)]    },
            {"timeframe": Timeframe.HOURS_2,    "last": datetime(2025, 11, 2, 20, 0, 0),    "checks": [(datetime(2025, 11, 2, 20, 0, 0), False),    (datetime(2025, 11, 2, 21, 59, 59), False), (datetime(2025, 11, 2, 22, 0, 0), True)]    },
            {"timeframe": Timeframe.HOURS_2,    "last": datetime(2025, 11, 2, 19, 30, 0),   "checks": [(datetime(2025, 11, 2, 19, 30, 0), False),   (datetime(2025, 11, 2, 19, 59, 59), False), (datetime(2025, 11, 2, 20, 0, 0), True)]    },
            {"timeframe": Timeframe.HOURS_4,    "last": datetime(2025, 11, 2, 20, 0, 0),    "checks": [(datetime(2025, 11, 2, 20, 0, 0), False),    (datetime(2025, 11, 2, 23, 59, 59), False), (datetime(2025, 11, 3, 0, 0, 0), True)]     },
            {"timeframe": Timeframe.HOURS_4,    "last": datetime(2025, 11, 2, 16, 50, 50),  "checks": [(datetime(2025, 11, 2, 16, 50, 50), False),  (datetime(2025, 11, 2, 19, 59, 59), False), (datetime(2025, 11, 2, 20, 0, 0), True)]    },
            {"timeframe": Timeframe.DAY_1,      "last": datetime(2025, 11, 2, 0, 0, 0),     "checks": [(datetime(2025, 11, 2, 0, 0, 0), False),     (datetime(2025, 11, 2, 23, 59, 59), False), (datetime(2025, 11, 3, 0, 0, 0), True)]     },
            {"timeframe": Timeframe.DAY_1,      "last": datetime(2025, 11, 2, 2, 15, 50),   "checks": [(datetime(2025, 11, 2, 2, 15, 50), False),   (datetime(2025, 11, 2, 23, 59, 59), False), (datetime(2025, 11, 3, 0, 0, 0), True)]     },
            {"timeframe": Timeframe.WEEK_1,     "last": datetime(2025, 11, 3, 0, 0, 0),     "checks": [(datetime(2025, 11, 3, 0, 0, 0), False),     (datetime(2025, 11, 9, 23, 59, 59), False), (datetime(2025, 11, 10, 0, 0, 0), True)]    },
            {"timeframe": Timeframe.WEEK_1,     "last": datetime(2025, 11, 6, 15, 50, 40),  "checks": [(datetime(2025, 11, 6, 15, 50, 40), False),  (datetime(2025, 11, 9, 23, 59, 59), False), (datetime(2025, 11, 10, 0, 0, 0), True)]    },
        ]

        for scenario in scenarios:
            chart_analyzer = ChartAnalyzer(BinanceChart("BTCUSDT", scenario["timeframe"]), self.strategy)
            chart_analyzer.last_processed_candle_time = int(scenario["last"].timestamp() * 1000)

            for now_dt, expected in scenario["checks"]:
                    with patch("time.time", return_value=now_dt.timestamp()):
                        self.assertEqual(chart_analyzer._is_new_candle_due(), expected)
