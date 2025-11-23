import unittest
from unittest.mock import MagicMock, patch
from agents.trade_agent import TradeAgent
from structs.signal import Signal
from charts.binance_chart import Timeframe

class TestTradeAgent(unittest.TestCase):
    
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

    @patch("agents.trade_agent.config")
    def test_analyze_disabled_by_config(self, mock_config):
        mock_config.enabled.return_value = False
        agent = TradeAgent([self.chart1], [self.strategy1], self.exchange)
        agent.analyze()
        self.chart1.have_new_data.assert_not_called()

    @patch("agents.trade_agent.config")
    def test_analyze_skips_charts_with_no_new_data(self, mock_config):
        mock_config.enabled.return_value = True
        self.chart1.have_new_data.return_value = False
        self.chart2.have_new_data.return_value = False

        agent = TradeAgent([self.chart1, self.chart2], [self.strategy1], self.exchange)
        agent.analyze()

        self.chart1.have_new_data.assert_called_once()
        self.chart2.have_new_data.assert_called_once()
        self.strategy1.generate_signal.assert_not_called()
        self.exchange.open_position.assert_not_called()

    @patch("agents.trade_agent.config")
    def test_analyze_skips_strategies_that_return_none(self, mock_config):
        mock_config.enabled.return_value = True
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
    @patch("agents.trade_agent.config")
    def test_analyze_opens_position_for_each_valid_signal(self, mock_config, mock_generate_position):
        # Enable all agent actions
        def config_side_effect(key):
            return True
        mock_config.enabled.side_effect = config_side_effect

        self.chart1.have_new_data.return_value = True
        self.chart2.have_new_data.return_value = True

        # Note: The type is capitalized "Long" and "Short" in trade_agent.py
        signal1 = Signal(entry=100.0, sl=95.0, tp=110.0, type="Long")
        signal2 = Signal(entry=200.0, sl=190.0, tp=220.0, type="Short")

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

    @patch("agents.trade_agent.Position.generate_position")
    @patch("agents.trade_agent.config")
    def test_analyze_skips_long_if_disabled(self, mock_config, mock_generate_position):
        # Disable long, enable short
        def config_side_effect(key):
            return key != "agent.long"
        mock_config.enabled.side_effect = config_side_effect

        self.chart1.have_new_data.return_value = True
        self.chart2.have_new_data.return_value = True

        long_signal = Signal(entry=100.0, sl=95.0, tp=110.0, type="Long")
        short_signal = Signal(entry=200.0, sl=190.0, tp=220.0, type="Short")
        self.strategy1.generate_signal.side_effect = [long_signal, short_signal]

        pos_short = MagicMock()
        mock_generate_position.return_value = pos_short

        agent = TradeAgent([self.chart1, self.chart2], [self.strategy1], self.exchange)
        agent.analyze()

        # Only the short position should be opened
        mock_generate_position.assert_called_once_with(self.chart2, self.strategy1, short_signal)
        self.exchange.open_position.assert_called_once_with(pos_short)

class TestTradeAgentDuplicateLogic(unittest.TestCase):
    @patch("agents.trade_agent.config")
    def setUp(self, mock_config):
        def config_side_effect(key):
            return True
        mock_config.enabled.side_effect = config_side_effect
        self.mock_config = mock_config

        # Mock chart
        self.chart = MagicMock()
        self.chart.symbol = "BTCUSDT"
        self.chart.timeframe = "5m"
        self.chart.have_new_data.return_value = True

        # Mock strategy
        self.strategy = MagicMock()
        self.strategy.STRATEGY_NAME = "TestStrategy"
        self.signal = Signal(entry=100, sl=90, tp=120, type="Long")
        self.strategy.generate_signal.return_value = self.signal

        # Mock exchange
        self.exchange = MagicMock()
        self.exchange.open_positions = []

        # Agent
        self.agent = TradeAgent(charts=[self.chart], strategies=[self.strategy], exchange=self.exchange)

    @patch("agents.trade_agent.Position.generate_position")
    @patch("agents.trade_agent.config")
    def test_new_position_added_when_no_duplicate(self, mock_config, mock_generate_position):
        mock_config.enabled.return_value = True

        pos = MagicMock()
        pos.chart.symbol = "BTCUSDT"
        pos.chart.timeframe = "5m"
        pos.type = "Long"
        pos.strategy.STRATEGY_NAME = "TestStrategy"
        mock_generate_position.return_value = pos

        # Make open_position append to open_positions
        def open_position_side_effect(p):
            self.exchange.open_positions.append(p)
        self.exchange.open_position.side_effect = open_position_side_effect

        self.agent.analyze()
        self.agent.analyze()

        # Now only one call, because duplicate is detected
        self.exchange.open_position.assert_called_once()
        new_pos = self.exchange.open_position.call_args[0][0]
        self.assertEqual(new_pos.chart.symbol, "BTCUSDT")
        self.assertEqual(new_pos.type, "Long")
        self.assertEqual(new_pos.strategy.STRATEGY_NAME, "TestStrategy")

    @patch("agents.trade_agent.config")
    def test_duplicate_position_updates_sl_tp(self, mock_config):
        mock_config.enabled.return_value = True
        # Existing position with same symbol, timeframe, type, and strategy name
        existing_pos = MagicMock()
        existing_pos.chart.symbol = "BTCUSDT"
        existing_pos.chart.timeframe = "5m"
        existing_pos.type = "Long"
        existing_pos.strategy.STRATEGY_NAME = "TestStrategy"
        existing_pos.sl = 85
        existing_pos.tp = 115

        self.exchange.open_positions = [existing_pos]

        self.agent.analyze()

        # Should not call open_position
        self.exchange.open_position.assert_not_called()

        # Should update SL and TP
        self.assertEqual(existing_pos.sl, self.signal.sl)
        self.assertEqual(existing_pos.tp, self.signal.tp)

    @patch("agents.trade_agent.config")
    def test_different_strategy_name_does_not_trigger_duplicate(self, mock_config):
        mock_config.enabled.return_value = True
        # Existing position with same symbol, timeframe, type but different strategy name
        existing_pos = MagicMock()
        existing_pos.chart.symbol = "BTCUSDT"
        existing_pos.chart.timeframe = "5m"
        existing_pos.type = "Long"
        existing_pos.strategy.STRATEGY_NAME = "OtherStrategy"

        self.exchange.open_positions = [existing_pos]

        self.agent.analyze()

        # Should add new position because strategy name differs
        self.exchange.open_position.assert_called_once()

    @patch("agents.trade_agent.config")
    def test_different_symbol_does_not_trigger_duplicate(self, mock_config):
        mock_config.enabled.return_value = True
        existing_pos = MagicMock()
        existing_pos.chart.symbol = "ETHUSDT"
        existing_pos.chart.timeframe = "5m"
        existing_pos.type = "Long"
        existing_pos.strategy.STRATEGY_NAME = "TestStrategy"

        self.exchange.open_positions = [existing_pos]

        self.agent.analyze()

        # Should add new BTCUSDT position
        self.exchange.open_position.assert_called_once()

    @patch("agents.trade_agent.config")
    def test_different_type_does_not_trigger_duplicate(self, mock_config):
        mock_config.enabled.return_value = True
        existing_pos = MagicMock()
        existing_pos.chart.symbol = "BTCUSDT"
        existing_pos.chart.timeframe = "5m"
        existing_pos.type = "Short"  # Different type
        existing_pos.strategy.STRATEGY_NAME = "TestStrategy"

        self.exchange.open_positions = [existing_pos]

        self.agent.analyze()

        # Should add new Long position
        self.exchange.open_position.assert_called_once()
