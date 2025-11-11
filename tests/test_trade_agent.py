import unittest
from unittest.mock import MagicMock, patch
from agents.trade_agent import TradeAgent
from structs.signal import Signal
from charts.binance_chart import Timeframe

class TestTradeAgent(unittest.TestCase):
    def test_analyze_returns_none_if_no_new_data(self):
        strategy = MagicMock()
        chart = MagicMock()
        chart.have_new_data.return_value = False

        agent = TradeAgent(chart, strategy)
        result = agent.analyze()

        self.assertIsNone(result)
        chart.have_new_data.assert_called_once()
        strategy.generate_signal.assert_not_called()

    def test_analyze_returns_none_if_no_signal(self):
        chart = MagicMock()
        chart.have_new_data.return_value = True

        strategy = MagicMock()
        strategy.generate_signal.return_value = None

        agent = TradeAgent(chart, strategy)
        result = agent.analyze()

        self.assertIsNone(result)
        strategy.generate_signal.assert_called_once_with(chart)


    @patch("agents.trade_agent.Position.generate_position")
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

        agent = TradeAgent(chart, strategy)

        result = agent.analyze()

        mock_generate_position.assert_called_once_with(chart, signal)
        self.assertEqual(result, mock_position)

    def test_analyze_handles_exception_from_chart(self):
        chart = MagicMock()
        chart.have_new_data.side_effect = Exception("chart error")

        strategy = MagicMock()

        agent = TradeAgent(chart, strategy)
        result = agent.analyze()

        self.assertIsNone(result)

    def test_analyze_handles_exception_from_strategy(self):
        chart = MagicMock()
        chart.have_new_data.return_value = True
        chart.symbol = "BTCUSDT"
        chart.timeframe = Timeframe.MINUTE_5

        strategy = MagicMock()
        strategy.generate_signal.side_effect = Exception("strategy error")

        agent = TradeAgent(chart, strategy)
        result = agent.analyze()

        self.assertIsNone(result)
