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

    def test_notify_open_multiline(self):
        exchange = VirtualExchange(api=None, notifier=MagicMock(), logger=None)
        exchange.tp_hits = 3
        exchange.sl_hits = 2
        exchange.closed_positions = [1, 2, 3, 4, 5]
        exchange.open_positions = [10, 11]

        pos = Position(
            symbol="BTCUSDT",
            interval="1h",
            candle_time=0,
            open_time="2025-11-04 01:00:00",
            entry=43200.1234,
            sl=43000.0000,
            tp=44000.0000,
            status="open",
            type="LONG",
            start_timestamp=0.0
        )
        pos.id = 5
        exchange._notify_open(pos)

        expected = (
            "⏳ *Position Opened #5*\n"
            "Type: *LONG*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *1h*\n"
            "Entry: `43200.1234`\n"
            "Stop Loss: `43000.0000`\n"
            "Take Profit: `44000.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `5`\n"
            "Open: `2`\n"
            "TP Hits: `3`\n"
            "SL Hits: `2`\n"
            "Winrate: `60.0%`"
        )

        exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_notify_close_tp_multiline(self):
        exchange = VirtualExchange(api=None, notifier=MagicMock(), logger=None)
        exchange.tp_hits = 3
        exchange.sl_hits = 2
        exchange.closed_positions = [1, 2, 3, 4, 5]
        exchange.open_positions = [10, 11]

        pos = Position(
            symbol="ETHUSDT",
            interval="4h",
            candle_time=0,
            open_time="2025-11-04 00:00:00",
            entry=3200.0000,
            sl=3150.0000,
            tp=3300.0000,
            status="closed",
            type="SHORT",
            start_timestamp=0.0,
            close_time="2025-11-04 04:00:00",
            duration=3661,
            exit_price=3100.0000,
            exit_reason="TP Hit",
            rr_ratio=2.0
        )
        pos.id = 1
        exchange._notify_close(pos)

        expected = (
            "✅ *Position Closed #1 — TP Hit*\n"
            "Type: *SHORT*\n"
            "Symbol: *ETHUSDT*\n"
            "Timeframe: *4h*\n"
            "Entry → Exit: `3200.0000` → `3100.0000`\n"
            "Duration: `01:01:01`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `5`\n"
            "Open: `1`\n"
            "TP Hits: `3`\n"
            "SL Hits: `2`\n"
            "Winrate: `60.0%`"
        )

        exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_notify_close_sl_multiline(self):
        exchange = VirtualExchange(api=None, notifier=MagicMock(), logger=None)
        exchange.tp_hits = 3
        exchange.sl_hits = 2
        exchange.closed_positions = [1, 2, 3, 4, 5]
        exchange.open_positions = [10, 11]

        pos = Position(
            symbol="SOLUSDT",
            interval="15m",
            candle_time=0,
            open_time="2025-11-04 00:45:00",
            entry=55.0000,
            sl=54.0000,
            tp=58.0000,
            status="closed",
            type="LONG",
            start_timestamp=0.0,
            close_time="2025-11-04 01:00:00",
            duration=900,
            exit_price=53.0000,
            exit_reason="SL Hit",
            rr_ratio=1.0
        )
        pos.id = 0
        exchange._notify_close(pos)

        expected = (
            "🛑 *Position Closed #0 — SL Hit*\n"
            "Type: *LONG*\n"
            "Symbol: *SOLUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry → Exit: `55.0000` → `53.0000`\n"
            "Duration: `00:15:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `5`\n"
            "Open: `1`\n"
            "TP Hits: `3`\n"
            "SL Hits: `2`\n"
            "Winrate: `60.0%`"
        )

        exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

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


        expected = ("✅ *Position Closed #3 — TP Hit*\n"
                    "Type: *Long*\n"
                    "Symbol: *BTCUSDT*\n"
                    "Timeframe: *15m*\n"
                    "Entry → Exit: `100.0000` → `110.0000`\n"
                    "Duration: `00:00:00`\n\n\n"
                    "📊 *Stats*\n"
                    "Closed: `3`\n"
                    "Open: `0`\n"
                    "TP Hits: `2`\n"
                    "SL Hits: `1`\n"
                    "Winrate: `66.7%`")
        
        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")