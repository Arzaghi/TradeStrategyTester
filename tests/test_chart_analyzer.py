import unittest
import time
from unittest.mock import MagicMock, patch
from chart_analyzer import ChartAnalyzer
from models import Signal, Position
from datetime import datetime, timezone
from charts.binance_chart import BinanceChart, Timeframe


class TestChartAnalyzer(unittest.TestCase):

    def test_analyze_returns_none_if_no_new_data(self):
        strategy = MagicMock()
        chart = MagicMock()
        chart.have_new_data.return_value = False

        analyzer = ChartAnalyzer(chart, strategy)
        result = analyzer.analyze()

        self.assertIsNone(result)
        chart.have_new_data.assert_called_once()
        strategy.generate_signal.assert_not_called()

    def test_analyze_returns_none_if_no_signal(self):
        chart = MagicMock()
        chart.have_new_data.return_value = True

        strategy = MagicMock()
        strategy.generate_signal.return_value = None

        analyzer = ChartAnalyzer(chart, strategy)
        result = analyzer.analyze()

        self.assertIsNone(result)
        strategy.generate_signal.assert_called_once_with(chart)


    @patch("chart_analyzer.Position.generate_position")
    def test_generate_position_called_with_correct_args(self, mock_generate_position):
        # Arrange
        chart = MagicMock()
        chart.symbol = "BTCUSDT"
        chart.timeframe = Timeframe.MINUTE_5
        chart.have_new_data.return_value = True

        signal = Signal(entry=100.0, sl=95.0, tp=110.0, type="long")

        strategy = MagicMock()
        strategy.generate_signal.return_value = signal

        mock_position = MagicMock()
        mock_generate_position.return_value = mock_position

        analyzer = ChartAnalyzer(chart, strategy)

        result = analyzer.analyze()

        mock_generate_position.assert_called_once_with(chart, signal)
        self.assertEqual(result, mock_position)

    def test_analyze_handles_exception_from_chart(self):
        chart = MagicMock()
        chart.have_new_data.side_effect = Exception("chart error")

        strategy = MagicMock()

        analyzer = ChartAnalyzer(chart, strategy)
        result = analyzer.analyze()

        self.assertIsNone(result)

    def test_analyze_handles_exception_from_strategy(self):
        chart = MagicMock()
        chart.have_new_data.return_value = True
        chart.symbol = "BTCUSDT"
        chart.timeframe = Timeframe.MINUTE_5

        strategy = MagicMock()
        strategy.generate_signal.side_effect = Exception("strategy error")

        analyzer = ChartAnalyzer(chart, strategy)
        result = analyzer.analyze()

        self.assertIsNone(result)

