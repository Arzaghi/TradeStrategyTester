from datetime import datetime, timezone
from typing import Optional
import unittest
from unittest.mock import Mock, call, patch
from exchanges.virtual_exchange import VirtualExchange
from strategies.strategy_interface import IStrategy
from structs.position import Position
from structs.signal import Signal
from charts.chart_interface import IChart, Timeframe

class DummyStrategy(IStrategy):
    STRATEGY_NAME = "foolish"

    def generate_signal(self, _: IChart) -> Optional[Signal]:
        return None

class DummyChart(IChart):
    def __init__(self, symbol="BTCUSDT", timeframe=Timeframe.MINUTE_5, price=100.0):
        super().__init__(symbol, timeframe)
        self._raw_data = []
        self._price = price

    def get_current_candle_time(self):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    
    def get_current_price(self) -> float:
        return self._price

    def get_recent_raw_ohlcv(self, n: int) -> list:
        return self._raw_data[:n]

    def have_new_data(self, now = None):
        return True

class TestVirtualExchange(unittest.TestCase):
    def setUp(self):
        self.notifier = Mock()
        self.history_logger = Mock()
        self.current_logger = Mock()
        self.exchange = VirtualExchange(
            notifier=self.notifier,
            positions_history_logger=self.history_logger,
            current_positions_logger=self.current_logger
        )

    @patch("exchanges.virtual_exchange.get_utc_now_timestamp", return_value=1700000000)
    def test_open_position_sets_status_and_notifies(self, mock_time):
        chart = DummyChart()
        strategy = DummyStrategy()
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)

        self.exchange.open_position(pos)

        self.assertEqual(pos.status, "opened")
        self.assertEqual(pos.open_timestamp, 1700000000)
        self.assertIn(pos, self.exchange.open_positions)
        self.notifier.send_message.assert_called_once()
        self.assertEqual(self.exchange.n_active_positions, 1)

    @patch("exchanges.virtual_exchange.get_utc_now_timestamp", return_value=1700000000)
    def test_tick_hits_stop_loss_and_closes_position(self, mock_time):
        chart = DummyChart(price=89.0)
        strategy = DummyStrategy()
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)
        
        self.exchange.open_position(pos)
        
        mock_time.return_value = 1720000000
        self.exchange.tick()

        self.assertEqual(pos.status, "closed")
        self.assertEqual(pos.close_timestamp, 1720000000)
        self.assertEqual(pos.exit_reason, "SL Hit")
        self.assertEqual(pos.profit, -1.1)
        self.assertIn(pos, self.exchange.closed_positions)
        self.history_logger.write.assert_called_once_with(pos.to_history_row())
        self.notifier.send_message.assert_called()
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, -1.1)
        self.assertEqual(self.exchange.n_active_positions, 0)

    @patch("exchanges.virtual_exchange.get_utc_now_timestamp", return_value=1700000000)
    def test_tick_hits_take_profit_and_closes_position(self, mock_time):
        chart = DummyChart(price=111.0)
        strategy = DummyStrategy()
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)

        self.exchange.open_position(pos)
        
        mock_time.return_value = 1700000020
        self.exchange.tick()

        self.assertEqual(pos.status, "closed")
        self.assertEqual(pos.close_timestamp, 1700000020)
        self.assertEqual(pos.exit_reason, "TP Hit")
        self.assertEqual(pos.profit, 1.1)
        self.assertEqual(self.exchange.tp_hits, 1.1)
        self.assertEqual(self.exchange.sl_hits, 0)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1.1)
        self.assertEqual(self.exchange.n_active_positions, 0)
        self.history_logger.write.assert_called_once_with(pos.to_history_row())
        self.notifier.send_message.assert_called()

    @patch("exchanges.virtual_exchange.get_utc_now_timestamp", return_value=1700000000)
    def test_tick_keeps_position_open_if_no_hit(self, mock_time):
        chart = DummyChart(price=105.0)
        strategy = DummyStrategy()
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)
        self.exchange.open_position(pos)
        self.assertEqual(self.notifier.send_message.call_count, 1)

        self.exchange.tick()

        self.assertIn(pos, self.exchange.open_positions)
        self.assertEqual(pos.status, "opened")
        self.history_logger.write.assert_not_called()        
        self.current_logger.write.assert_called_once_with([pos.to_active_position_row()])
        self.assertEqual(self.notifier.send_message.call_count, 1) # No new call

    def test_tick_handles_chart_exception_gracefully(self):
        chart = DummyChart()
        strategy = DummyStrategy()
        chart.get_current_price = Mock(side_effect=Exception("fail"))
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertIn(pos, self.exchange.open_positions)

    def test_close_position_updates_stats_and_logs(self):
        chart = DummyChart()
        strategy = DummyStrategy()
        signal = Signal(entry=100, sl=90, tp=110, type="Long")
        pos = Position.generate_position(chart, strategy, signal)
        self.exchange._close_position(pos, None, "for test")

        self.assertEqual(pos.exit_reason, "for test")
        self.assertEqual(pos.status, "closed")
        self.assertIn(pos, self.exchange.closed_positions)
        self.assertEqual(self.exchange.breakeven_hits, 1)
        self.history_logger.write.assert_called_once_with(pos.to_history_row())
        self.notifier.send_message.assert_called()

    def test_open_position_none_does_nothing(self):
        self.exchange.open_position(None)
        self.assertEqual(self.exchange.n_active_positions, 0)
        self.notifier.send_message.assert_not_called()

    def test_close_position_none_does_nothing(self):
        self.exchange._close_position(None)
        self.notifier.send_message.assert_not_called()
        self.history_logger.write.assert_not_called()
