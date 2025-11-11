import unittest
from unittest.mock import MagicMock, patch
from agents.trade_agent import TradeAgent
from structs.signal import Signal
from charts.binance_chart import Timeframe

class TestTradeAgentMulti(unittest.TestCase):
    def setUp(self):
        self.chart1 = MagicMock()
        self.chart1.symbol = "BTCUSDT"
        self.chart1.timeframe = Timeframe.MINUTE_5

        self.chart2 = MagicMock()
        self.chart2.symbol = "ETHUSDT"
        self.chart2.timeframe = Timeframe.MINUTE_15

        self.strategy1 = MagicMock()
        self.strategy2 = MagicMock()

        self.exchange = MagicMock()

    def test_analyze_skips_charts_with_no_new_data(self):
        self.chart1.have_new_data.return_value = False
        self.chart2.have_new_data.return_value = False

        agent = TradeAgent([self.chart1, self.chart2], [self.strategy1], self.exchange)
        agent.analyze()

        self.chart1.have_new_data.assert_called_once()
        self.chart2.have_new_data.assert_called_once()
        self.strategy1.generate_signal.assert_not_called()
        self.exchange.open_position.assert_not_called()

    def test_analyze_skips_strategies_that_return_none(self):
        self.chart1.have_new_data.return_value = True
        self.chart2.have_new_data.return_value = True

        self.strategy1.generate_signal.return_value = None
        self.strategy2.generate_signal.return_value = None

        agent = TradeAgent([self.chart1, self.chart2], [self.strategy1, self.strategy2], self.exchange)
        agent.analyze()

        self.assertEqual(self.strategy1.generate_signal.call_count, 2)
        self.assertEqual(self.strategy2.generate_signal.call_count, 2)
        self.exchange.open_position.assert_not_called()

    @patch("agents.trade_agent.Position.generate_position")
    def test_analyze_opens_position_for_each_valid_signal(self, mock_generate_position):
        self.chart1.have_new_data.return_value = True
        self.chart2.have_new_data.return_value = True

        signal1 = Signal(entry=100.0, sl=95.0, tp=110.0, type="long")
        signal2 = Signal(entry=200.0, sl=190.0, tp=220.0, type="short")

        self.strategy1.generate_signal.side_effect = [signal1, None]
        self.strategy2.generate_signal.side_effect = [None, signal2]

        pos1 = MagicMock()
        pos2 = MagicMock()
        mock_generate_position.side_effect = [pos1, pos2]

        agent = TradeAgent([self.chart1, self.chart2], [self.strategy1, self.strategy2], self.exchange)
        agent.analyze()

        mock_generate_position.assert_has_calls([
            unittest.mock.call(self.chart1, self.strategy1, signal1),
            unittest.mock.call(self.chart2, self.strategy2, signal2)
        ])
        self.exchange.open_position.assert_has_calls([
            unittest.mock.call(pos1),
            unittest.mock.call(pos2)
        ])
        self.assertEqual(self.exchange.open_position.call_count, 2)

