import unittest
from unittest.mock import MagicMock, patch
from virtual_exchange import VirtualExchange
from models import Position
import time


def create_position(symbol="BTCUSDT", interval="15m", entry=100.0, sl=90.0, tp=110.0, type="Long"):
    return Position(
        symbol=symbol,
        interval=interval,
        candle_time=1698768000000,
        open_time="2023-11-01 00:00:00",
        entry=entry,
        sl=sl,
        tp=tp,
        status="open",
        type=type,
        start_timestamp=time.time()
    )

class TestVirtualExchange(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.notifier = MagicMock()
        self.logger = MagicMock()
        self.exchange = VirtualExchange(self.api, self.notifier, self.logger)

    def test_open_position_assigns_id_and_notifies(self):
        pos = create_position()
        self.exchange.open_position(pos)

        self.assertEqual(pos.id, 1)
        self.assertIn(pos, self.exchange.open_positions)
        self.notifier.send_message.assert_called_once()

    def test_open_position_skips_none(self):
        self.exchange.open_position(None)
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.notifier.send_message.assert_not_called()

    def test_tick_closes_on_tp_hit(self):
        pos = create_position()
        self.api.get_current_price.return_value = 110.0
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)
        self.logger.write.assert_called_once()
        self.notifier.send_message.assert_called()

    def test_tick_closes_on_sl_hit(self):
        pos = create_position()
        self.api.get_current_price.return_value = 89.0
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.logger.write.assert_called_once()
        self.notifier.send_message.assert_called()

    def test_tick_keeps_position_open_if_price_between_sl_tp(self):
        pos = create_position()
        self.api.get_current_price.return_value = 100.0
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)
        self.logger.write.assert_not_called()

    def test_tick_handles_short_tp_hit(self):
        pos = create_position(type="Short", entry=100.0, sl=110.0, tp=90.0)
        self.api.get_current_price.return_value = 90.0
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(pos.exit_reason, "TP Hit")

    def test_tick_handles_short_sl_hit(self):
        pos = create_position(type="Short", entry=100.0, sl=110.0, tp=90.0)
        self.api.get_current_price.return_value = 111.0
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(pos.exit_reason, "SL Hit")

    def test_tick_handles_api_exception_gracefully(self):
        pos = create_position()
        self.api.get_current_price.side_effect = Exception("API error")
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)

    def test_notify_open_skips_if_notifier_none(self):
        exchange = VirtualExchange(self.api, None)
        pos = create_position()
        exchange.open_position(pos)  # Should not throw

    def test_notify_close_skips_if_notifier_none(self):
        exchange = VirtualExchange(self.api, None)
        pos = create_position()
        exchange._close_position(pos, 110.0, "TP Hit")  # Should not throw

    def test_logger_failure_does_not_crash(self):
        pos = create_position()
        self.api.get_current_price.return_value = 110.0
        self.logger.write.side_effect = Exception("Disk error")
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.closed_positions), 1)

    @patch("builtins.print")
    def test_notify_open_prints_on_failure(self, mock_print):
        pos = create_position()
        self.notifier.send_message.side_effect = Exception("Telegram error")
        self.exchange.open_position(pos)

        mock_print.assert_called_with("[VirtualExchange] Failed to send open notification: Telegram error")

    @patch("builtins.print")
    def test_notify_close_prints_on_failure(self, mock_print):
        pos = create_position()
        self.api.get_current_price.return_value = 110.0
        self.notifier.send_message.side_effect = Exception("Telegram error")
        self.exchange.open_position(pos)

        self.exchange.tick()

        mock_print.assert_called_with("[VirtualExchange] Failed to send close notification: Telegram error")

    def test_open_notification_format(self):
        pos = create_position()
        self.exchange.open_position(pos)

        self.notifier.send_message.assert_called_once()
        message = self.notifier.send_message.call_args[0][0]

        self.assertIn("🕒", message)
        self.assertIn(f"Opened #{pos.id}", message)
        self.assertIn(pos.symbol, message)
        self.assertIn(pos.interval, message)
        self.assertIn(f"{pos.entry:.4f}", message)
        self.assertIn(f"{pos.sl:.4f}", message)
        self.assertIn(f"{pos.tp:.4f}", message)

    def test_close_notification_tp_hit_stats(self):
        pos = create_position()
        self.api.get_current_price.return_value = 110.0
        self.exchange.open_position(pos)
        self.exchange.tick()

        message = self.notifier.send_message.call_args_list[-1][0][0]

        self.assertIn("✅", message)
        self.assertIn("TP Hit", message)
        self.assertIn(f"Closed #{pos.id}", message)
        self.assertIn(f"{pos.entry:.4f}", message)
        self.assertIn(f"{pos.exit_price:.4f}", message)
        self.assertIn("📊", message)
        self.assertIn("*Closed:* 1", message)
        self.assertIn("*Open:* 0", message)
        self.assertIn("*TP:* 1", message)
        self.assertIn("*SL:* 0", message)
        self.assertIn("*Winrate:* 100.0%", message)

    def test_close_notification_sl_hit_stats(self):
        pos = create_position()
        self.api.get_current_price.return_value = 89.0
        self.exchange.open_position(pos)
        self.exchange.tick()

        message = self.notifier.send_message.call_args_list[-1][0][0]

        self.assertIn("🛑", message)
        self.assertIn("SL Hit", message)
        self.assertIn("*Closed:* 1", message)
        self.assertIn("*TP:* 0", message)
        self.assertIn("*SL:* 1", message)
        self.assertIn("*Winrate:* 0.0%", message)

    def test_multiple_positions_winrate_calculation(self):
        # TP Hit
        pos1 = create_position()
        self.api.get_current_price.return_value = 110.0
        self.exchange.open_position(pos1)
        self.exchange.tick()

        # SL Hit
        pos2 = create_position()
        self.api.get_current_price.return_value = 89.0
        self.exchange.open_position(pos2)
        self.exchange.tick()

        # TP Hit
        pos3 = create_position()
        self.api.get_current_price.return_value = 110.0
        self.exchange.open_position(pos3)
        self.exchange.tick()

        message = self.notifier.send_message.call_args_list[-1][0][0]

        self.assertIn("*Closed:* 3", message)
        self.assertIn("*TP:* 2", message)
        self.assertIn("*SL:* 1", message)
        self.assertIn("*Winrate:* 66.7%", message)