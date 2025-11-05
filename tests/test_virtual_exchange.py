import unittest
import tempfile
import time
import csv
import os
from datetime import timedelta
from unittest.mock import MagicMock, patch
from virtual_exchange import VirtualExchange
from models import Position
from persistence import PositionsHistoryLogger

def create_position(symbol="BTCUSDT", interval="15m", entry=100.0, sl=90.0, tp=110.0, type="Long"):
    return Position(
        symbol=symbol,
        interval=interval,
        candle_time=1698768000000,
        open_time="2023-11-01 00:00:00",
        entry=entry,
        initial_sl=sl,
        initial_tp=tp,
        sl=sl,
        tp=tp,
        status="open",
        type=type,
        start_timestamp=time.time(),
        profit=-1.0
    )

class TestVirtualExchange(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.notifier = MagicMock()
        self.logger = MagicMock()
        self.exchange = VirtualExchange(self.api, self.notifier, self.logger)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.positions_history_logs_filename = os.path.join(self.temp_dir.name, "temp_positions_history_logs.csv")
        self.logger = PositionsHistoryLogger(filename=self.positions_history_logs_filename)
        self.exchange = VirtualExchange(self.api, self.notifier, self.logger)

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_positions_history_logs(self):
        with open(self.positions_history_logs_filename, newline='') as f:
            return list(csv.reader(f))

    def read_positions_history_logs_as_string(self):
        with open(self.positions_history_logs_filename, "r", encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def check_positions_history_logs(self, expected_csv_string):
        actual_csv_rows = self.read_positions_history_logs()
        expected_rows = [line.strip().split(",") for line in expected_csv_string.strip().splitlines()]
        self.assertEqual(len(actual_csv_rows), len(expected_rows), "Row count mismatch")

        header = actual_csv_rows[0]
        self.assertEqual(header, expected_rows[0], "Header mismatch")
        time_fields=("open_time", "close_time", "duration")

        for i in range(1, len(expected_rows)):
            actual_row = dict(zip(header, actual_csv_rows[i]))
            expected_row = dict(zip(header, expected_rows[i]))

            for field in header:
                if field in time_fields:
                    self.assertRegex(actual_row[field], r"\d{2}:\d{2}:\d{2}" if field == "duration" else r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
                else:
                    self.assertEqual(actual_row[field], expected_row[field], f"Mismatch in field '{field}'")

    def test_logger_writes_on_close_with_correct_duration(self):
        pos = create_position()
        pos.start_timestamp = time.time() - timedelta(hours=2, minutes=22, seconds=30).total_seconds()
        self.api.get_current_price.return_value = 89.0  # SL hit

        self.exchange.open_position(pos)
        self.exchange.tick()
        self.assertEqual(pos.duration, "02:22:30")

        expected_positions_history_logs = (
            "type,symbol,interval,entry,initial_sl,initial_tp,exit_price,open_time,close_time,duration,profit\n"
            "Long,BTCUSDT,15m,100.0,90.0,110.0,89.0,2023-01-01 00:00:00,2023-01-01 01:05:30,01:05:30,-1"
        )
        self.check_positions_history_logs(expected_positions_history_logs)

    def test_tp_extension_long_position(self):
        pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.api.get_current_price.side_effect = [110.0, 120.0, 130.0, 95.0]  # 3 TP hits, then SL
        self.exchange.open_position(pos)

        for _ in range(4):
            self.exchange.tick()

        self.assertEqual(pos.profit, 2)
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.profits_sum, 2)
        self.assertEqual(len(self.exchange.closed_positions), 1)

    def test_tp_extension_short_position(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.api.get_current_price.side_effect = [90.0, 80.0, 70.0, 111.0]  # 3 TP hits, then SL
        self.exchange.open_position(pos)

        for _ in range(4):
            self.exchange.tick()

        self.assertEqual(pos.profit, 2)
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.profits_sum, 2)
        self.assertEqual(len(self.exchange.closed_positions), 1)

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

    def test_long_tp2_hit(self):
        pos = create_position() # entry=100.0, sl=90.0, tp=110.0, type="Long"):
        self.api.get_current_price.return_value = 110.0
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `90.0000`\n"
            "Take Profit: `110.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

        self.assertEqual(pos.profit, -1)

        self.exchange.tick() # First TP hit

        # Position should still be open
        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)

        # Profit should be updated to 0
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 120)

        # No TP or SL hits yet
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 101.0
        self.exchange.tick() # Nothing Changed
        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 120)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 121.0
        self.exchange.tick() # new TP hit
        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 110)
        self.assertEqual(pos.tp, 130)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 131.0
        self.exchange.tick() # new TP hit
        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)
        self.assertEqual(pos.profit, 2)
        self.assertEqual(pos.sl, 120)
        self.assertEqual(pos.tp, 140)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 120.0
        self.exchange.tick() # stop loss
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 2)
        self.assertEqual(pos.sl, 120)
        self.assertEqual(pos.tp, 140)
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 0)

        expected = (
            "✅ *Position Closed* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *2*\n"
            "`100.0000` → `120.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `2`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_long_sl_on_entry_hit(self):
        pos = create_position() # entry=100.0, sl=90.0, tp=110.0, type="Long"):        
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `90.0000`\n"
            "Take Profit: `110.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

        self.assertEqual(pos.profit, -1)

        self.api.get_current_price.return_value = 110.0
        self.exchange.tick() # First TP hit

        # Position should still be open
        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)

        # Profit should be updated to 0
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 120)

        # No TP or SL hits yet
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 99
        self.exchange.tick() # Stop hit on Entry
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 120)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)
        self.assertEqual(self.exchange.breakeven_hits, 1)

        expected = (
            "😐 *Position Closed* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *0*\n"
            "`100.0000` → `99.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `0`\n"
            "EN Hits: `1`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_long_sl_without_tp_hit(self):
        pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `90.0000`\n"
            "Take Profit: `110.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_open, parse_mode="Markdown")
        self.assertEqual(pos.profit, -1)

        # Price drops below SL immediately
        self.api.get_current_price.return_value = 89.0
        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.exit_reason, "SL Hit")
        self.assertEqual(pos.exit_price, 89.0)
        self.assertEqual(pos.profit, -1)
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, -1)

        expected_close = (
            "⛔ *Position Closed* #Position_1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *-1*\n"
            "`100.0000` → `89.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `1`\n"
            "Total Profit: `-1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_short_tp2_hit(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `110.0000`\n"
            "Take Profit: `90.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_open, parse_mode="Markdown")
        self.assertEqual(pos.profit, -1)

        self.api.get_current_price.return_value = 90.0
        self.exchange.tick()  # First TP hit
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 80)

        self.api.get_current_price.return_value = 79.0
        self.exchange.tick()  # Second TP hit
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 70)

        self.api.get_current_price.return_value = 69.0
        self.exchange.tick()  # Third TP hit
        self.assertEqual(pos.profit, 2)
        self.assertEqual(pos.sl, 80)
        self.assertEqual(pos.tp, 60)

        self.api.get_current_price.return_value = 80.0
        self.exchange.tick()  # SL hit
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 0)

        expected_close = (
            "✅ *Position Closed* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"            
            "Profit: *2*\n"
            "`100.0000` → `80.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `2`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_short_sl_on_entry_hit(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `110.0000`\n"
            "Take Profit: `90.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_open, parse_mode="Markdown")
        self.assertEqual(pos.profit, -1)

        self.api.get_current_price.return_value = 90.0
        self.exchange.tick()  # First TP hit
        self.assertEqual(pos.profit, 0)
        self.assertEqual(pos.sl, 100)
        self.assertEqual(pos.tp, 80)

        self.api.get_current_price.return_value = 101.0
        self.exchange.tick()  # SL hit at entry
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 0)
        self.assertEqual(self.exchange.breakeven_hits, 1)

        expected_close = (
            "😐 *Position Closed* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *0*\n"
            "`100.0000` → `101.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `0`\n"
            "EN Hits: `1`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_sl_without_tp_hit_short(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Entry: `100.0000`\n"
            "Stop Loss: `110.0000`\n"
            "Take Profit: `90.0000`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `0`\n"
            "Open: `1`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_open, parse_mode="Markdown")
        self.assertEqual(pos.profit, -1)

        self.api.get_current_price.return_value = 111.0
        self.exchange.tick()  # SL hit immediately
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, -1)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.profits_sum, -1)

        expected_close = (
            "⛔ *Position Closed* #Position_1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"            
            "Profit: *-1*\n"
            "`100.0000` → `111.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `0`\n"
            "EN Hits: `0`\n"
            "SL Hits: `1`\n"
            "Total Profit: `-1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_tick_handles_api_exception_gracefully(self):
        pos = create_position()
        self.api.get_current_price.side_effect = Exception("API error")
        self.exchange.open_position(pos)

        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 0)

    def test_notify_open_skips_if_notifier_none(self):
        exchange = VirtualExchange(self.api, notifier = None)
        pos = create_position()
        exchange._notify_open(pos)  # Should not throw

    def test_notify_close_skips_if_notifier_none(self):
        exchange = VirtualExchange(self.api, notifier = None)
        pos = create_position()
        exchange._notify_close(pos)  # Should not throw

    def test_logger_failure_does_not_crash(self):
        failing_logger = MagicMock()
        failing_logger.write.side_effect = Exception("Disk error")
        self.exchange.logger = failing_logger

        pos = create_position()
        self.exchange.open_position(pos)

        self.api.get_current_price.return_value = 89.0

        # Should not crash even though logger fails to write!
        self.exchange.tick() # close position

        # assert that the logger was called
        failing_logger.write.assert_called_once()        

    @patch("builtins.print")
    def test_notify_open_prints_on_failure(self, mock_print):
        pos = create_position()
        self.notifier.send_message.side_effect = Exception("Telegram error")
        self.exchange.open_position(pos)
        mock_print.assert_called_with("[VirtualExchange] Failed to send open notification: Telegram error")

    @patch("builtins.print")
    def test_notify_close_prints_on_failure(self, mock_print):
        pos = create_position()                
        self.exchange.open_position(pos)

        self.api.get_current_price.return_value = 89.0
        self.notifier.send_message.side_effect = Exception("Telegram error")
        self.exchange.tick() # close position and send notification but error in sending
        mock_print.assert_called_with("[VirtualExchange] Failed to send close notification: Telegram error")

    def test_multiple_positions_winrate_calculation(self):
        # TP 2 Hit
        pos1 = create_position() # long 100, sl=90, tp=110
        self.exchange.open_position(pos1)

        self.api.get_current_price.return_value = 110
        self.exchange.tick()

        self.api.get_current_price.return_value = 120
        self.exchange.tick()

        self.api.get_current_price.return_value = 130
        self.exchange.tick()

        self.api.get_current_price.return_value = 119
        self.exchange.tick()

        # SL Hit
        pos2 = create_position()        
        self.exchange.open_position(pos2)
        self.api.get_current_price.return_value = 89.0
        self.exchange.tick()

        # entry Hit
        pos3 = create_position()        
        self.exchange.open_position(pos3)
        self.api.get_current_price.return_value = 110.0
        self.exchange.tick()
        self.api.get_current_price.return_value = 99.0
        self.exchange.tick()

        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 1)
        self.assertEqual(self.exchange.profits_sum, 1)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        
        expected = (
            "😐 *Position Closed* #Position_3\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"            
            "Profit: *0*\n"
            "`100.0000` → `99.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `3`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `1`\n"
            "SL Hits: `1`\n"
            "Total Profit: `1`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_mixed_long_and_short_positions(self):
        # Long position: 2 TP hits, then SL
        long_pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.exchange.open_position(long_pos)

        self.api.get_current_price.return_value = 110.0
        self.exchange.tick()  # TP → profit = 0, sl = 100, tp = 120

        self.api.get_current_price.return_value = 121.0
        self.exchange.tick()  # TP → profit = 1, sl = 110, tp = 130

        self.api.get_current_price.return_value = 120.0
        self.exchange.tick()  # SL → profit = 1

        # Short position: 1 TP hit, then SL
        short_pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(short_pos)

        self.api.get_current_price.return_value = 90.0
        self.exchange.tick()  # TP → profit = 0, sl = 100, tp = 80

        self.api.get_current_price.return_value = 101.0
        self.exchange.tick()  # SL → profit = 0 (breakeven)

        # Long position: SL hit immediately
        long_sl = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.exchange.open_position(long_sl)

        self.api.get_current_price.return_value = 89.0
        self.exchange.tick()  # SL → profit = -1

        # Short position: SL hit immediately
        short_sl = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(short_sl)

        self.api.get_current_price.return_value = 111.0
        self.exchange.tick()  # SL → profit = -1

        # Final assertions
        self.assertEqual(len(self.exchange.closed_positions), 4)
        self.assertEqual(len(self.exchange.open_positions), 0)

        self.assertEqual(self.exchange.tp_hits, 1)  # long: 1, short: 0 (only full TP counted)
        self.assertEqual(self.exchange.sl_hits, 2)  # long_sl + short_sl
        self.assertEqual(self.exchange.breakeven_hits, 1)  # short_pos
        self.assertEqual(self.exchange.profits_sum, -1)  # 1 + 0 + (-1) + (-1)

        # Final closed position notification (short_sl)
        expected_close = (
            "⛔ *Position Closed* #Position_4\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *-1*\n"
            "`100.0000` → `111.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `4`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `1`\n"
            "SL Hits: `2`\n"
            "Total Profit: `-1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_three_open_positions_mixed_directions(self):
        long_pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long", interval="30m")
        short_pos = create_position(entry=200.0, sl=210.0, tp=190.0, type="Short", interval="1h")
        long_sl = create_position(entry=300.0, sl=290.0, tp=310.0, type="Long", interval="4h")
        
        # It starts a few hours ago to test calculation of the duration
        short_pos.start_timestamp = time.time() - timedelta(hours=4, minutes=22, seconds=30).total_seconds()

        self.exchange.open_position(long_pos)
        self.exchange.open_position(short_pos)
        self.exchange.open_position(long_sl)
        self.assertEqual(len(self.exchange.open_positions), 3)
        self.assertEqual(len(self.exchange.closed_positions), 0)
        self.assertEqual(long_pos.profit, -1)
        self.assertEqual(short_pos.profit, -1)
        self.assertEqual(long_sl.profit, -1)        
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 0)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 0)


        # Tick 1: TP hit for long and short
        self.api.get_current_price.return_value = 110
        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 2)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(long_pos.profit, 0)
        self.assertEqual(short_pos.profit, 0)
        self.assertEqual(long_sl.profit, -1)        
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, -1)

        # Tick 2: SL hit for long and short
        self.api.get_current_price.return_value = 100
        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 1)
        self.assertEqual(len(self.exchange.closed_positions), 2)
        self.assertEqual(long_pos.profit, 0)
        self.assertEqual(short_pos.profit, 1)
        self.assertEqual(long_sl.profit, -1)        
        self.assertEqual(self.exchange.tp_hits, 0)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 1)
        self.assertEqual(self.exchange.profits_sum, -1)

        self.api.get_current_price.return_value = 190
        self.exchange.tick()
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        self.assertEqual(long_pos.profit, 0)
        self.assertEqual(short_pos.profit, 1)
        self.assertEqual(long_sl.profit, -1) 
        self.assertEqual(short_pos.duration, "04:22:30")       
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 1)
        self.assertEqual(self.exchange.profits_sum, 0)

        expected = (
            "✅ *Position Closed* #Position_2\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *1h*\n"
            "Profit: *1*\n"
            "`200.0000` → `190.0000`\n"
            "Duration: `04:22:30`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `3`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `1`\n"
            "SL Hits: `1`\n"
            "Total Profit: `0`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

        expected_positions_history_logs = (
            "type,symbol,interval,entry,initial_sl,initial_tp,exit_price,open_time,close_time,duration,profit\n"
            "Long,BTCUSDT,4h,300.0,290.0,310.0,110,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,-1\n"
            "Long,BTCUSDT,30m,100.0,90.0,110.0,100,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,0\n"
            "Short,BTCUSDT,1h,200.0,210.0,190.0,190,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,1\n"
        )
        self.check_positions_history_logs(expected_positions_history_logs)
