import unittest
import tempfile
import time
import csv
import os
from datetime import timedelta
from unittest.mock import MagicMock, patch
from virtual_exchange import VirtualExchange
from models import Position
from persistence import PositionsHistoryLogger, CurrentPositionsLogger

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

        self.temp_dir = tempfile.TemporaryDirectory()
        self.positions_history_logs_filename = os.path.join(self.temp_dir.name, "temp_positions_history_logs.csv")
        self.positions_history_logger = PositionsHistoryLogger(filename=self.positions_history_logs_filename)
        
        self.current_positions_logs_filename = os.path.join(self.temp_dir.name, "temp_current_positions_logs.csv")
        self.current_positions_logger = CurrentPositionsLogger(filename=self.current_positions_logs_filename)
        
        self.exchange = VirtualExchange(api=self.api, notifier=self.notifier, positions_history_logger=self.positions_history_logger, current_positions_logger=self.current_positions_logger)

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_logs(self, filename):
        with open(filename, newline='') as f:
            return list(csv.reader(f))

    def read_logs_as_string(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def check_logs(self, filename, expected_csv_string):
        actual_csv_rows = self.read_logs(filename)
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
        self.check_logs(self.positions_history_logs_filename, expected_positions_history_logs)

    def test_tp_extension_long_position(self):
        pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.api.get_current_price.side_effect = [110.0, 120.0, 130.0, 95.0]  # 3 TP hits, then SL
        self.exchange.open_position(pos)

        for _ in range(4):
            self.exchange.tick()

        self.assertEqual(pos.profit, 1)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.profits_sum, 1)
        self.assertEqual(len(self.exchange.closed_positions), 1)

    def test_tp_extension_short_position(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.api.get_current_price.side_effect = [90.0, 80.0, 70.0, 111.0]  # 3 TP hits, then SL
        self.exchange.open_position(pos)

        for _ in range(4):
            self.exchange.tick()

        self.assertEqual(pos.profit, 1)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.profits_sum, 1)
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
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected = (
            "⏳ *Position Opened* #Position1\n"
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

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        # Position should still be open
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)

        # Profit should be updated to 0
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)

        # No TP or SL hits yet
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 101.0
        self.exchange.tick() # Nothing Changed

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)


        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 121.0
        self.exchange.tick() # new TP hit



        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)


        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 131.0
        self.exchange.tick() # new TP hit
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 120.0
        self.exchange.tick() # stop loss
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        expected = (
            "✅ *Position Closed* #Position1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *1*\n"
            "`100.0000` → `110.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `1`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")
        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

    def test_long_sl_on_entry_hit(self):
        pos = create_position() # entry=100.0, sl=90.0, tp=110.0, type="Long"):        
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected = (
            "⏳ *Position Opened* #Position1\n"
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
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)

        # Profit should be updated to 0
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)

        # No TP or SL hits yet
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        self.api.get_current_price.return_value = 100
        self.exchange.tick() # Stop hit on Entry
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 90)
        self.assertEqual(pos.tp, 110)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)
        self.assertEqual(self.exchange.breakeven_hits, 0)

        expected = (
            "✅ *Position Closed* #Position1\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *1*\n"
            "`100.0000` → `110.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_long_sl_without_tp_hit(self):
        pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position1\n"
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
            "⛔ *Position Closed* #Position1\n"
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
            "⏳ *Position Opened* #Position1\n"
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
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 110)
        self.assertEqual(pos.tp, 90)

        self.api.get_current_price.return_value = 79.0
        self.exchange.tick()  # Second TP hit
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 110)
        self.assertEqual(pos.tp, 90)

        self.api.get_current_price.return_value = 69.0
        self.exchange.tick()  # Third TP hit
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 110)
        self.assertEqual(pos.tp, 90)

        self.api.get_current_price.return_value = 80.0
        self.exchange.tick()  # SL hit
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(self.exchange.tp_hits, 1)
        self.assertEqual(self.exchange.sl_hits, 0)

        expected_close = (
            "✅ *Position Closed* #Position1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"            
            "Profit: *1*\n"
            "`100.0000` → `90.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_short_sl_on_entry_hit(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position1\n"
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
        self.assertEqual(pos.profit, 1)
        self.assertEqual(pos.sl, 110)
        self.assertEqual(pos.tp, 90)

        self.api.get_current_price.return_value = 100.0
        self.exchange.tick()  # SL hit at entry
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 1)
        self.assertEqual(pos.profit, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)

        expected_close = (
            "✅ *Position Closed* #Position1\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *1*\n"
            "`100.0000` → `90.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `1`\n"
            "Open: `0`\n"
            "TP Hits: `1`\n"
            "EN Hits: `0`\n"
            "SL Hits: `0`\n"
            "Total Profit: `1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_sl_without_tp_hit_short(self):
        pos = create_position(entry=100.0, sl=110.0, tp=90.0, type="Short")
        self.exchange.open_position(pos)
        self.notifier.send_message.assert_called()

        expected_open = (
            "⏳ *Position Opened* #Position1\n"
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
            "⛔ *Position Closed* #Position1\n"
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

    def test_history_logger_failure_does_not_crash(self):
        failing_logger = MagicMock()
        failing_logger.write.side_effect = Exception("Disk error")
        self.exchange.positions_history_logger = failing_logger

        pos = create_position()
        self.exchange.open_position(pos)

        self.api.get_current_price.return_value = 89.0

        # Should not crash even though logger fails to write!
        self.exchange.tick() # close position

        # assert that the logger was called
        failing_logger.write.assert_called_once()

    def test_current_positions_logger_failure_does_not_crash(self):
        failing_logger = MagicMock()
        failing_logger.write.side_effect = Exception("Disk error")
        self.exchange.current_positions_logger = failing_logger

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
        self.api.get_current_price.return_value = 100.0
        self.exchange.tick()

        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        
        expected = (
            "✅ *Position Closed* #Position3\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"            
            "Profit: *1*\n"
            "`100.0000` → `110.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `3`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `0`\n"
            "SL Hits: `1`\n"
            "Total Profit: `1`\n"
        )

        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

    def test_mixed_long_and_short_positions_with_simultaneous_openings(self):
        # Long position: 2 TP hits, then SL
        long_pos = create_position(entry=100.0, sl=90.0, tp=110.0, type="Long")
        self.exchange.open_position(long_pos)

        self.api.get_current_price.return_value = 110.0
        self.exchange.tick()

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        self.api.get_current_price.return_value = 121.0
        self.exchange.tick()  # TP → profit = 1, sl = 110, tp = 130

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        # Open long and short positions simultaneously
        long_simul = create_position(entry=120.0, sl=110.0, tp=130.0, type="Long")
        short_simul = create_position(entry=120.0, sl=140.0, tp=100.0, type="Short")
        self.exchange.open_position(long_simul)
        self.exchange.open_position(short_simul)

        self.api.get_current_price.return_value = 120.0
        self.exchange.tick()  # 2 open Positions now

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
            "2,Long,BTCUSDT,15m,2023-11-01 00:00:00,120.0,110.0,110.0,130.0,-1,120.0\n"
            "3,Short,BTCUSDT,15m,2023-11-01 00:00:00,120.0,140.0,140.0,100.0,-1,120.0\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        self.api.get_current_price.return_value = 94.0
        self.exchange.tick()

        self.api.get_current_price.return_value = 96.0
        self.exchange.tick()

        self.api.get_current_price.return_value = 94.0
        self.exchange.tick()

        print(self.read_logs_as_string(self.current_positions_logs_filename))
        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        self.api.get_current_price.return_value = 120.0
        self.exchange.tick()

        expected_current_positions_logs = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
        )
        self.check_logs(self.current_positions_logs_filename, expected_current_positions_logs)

        # Final assertions
        self.assertEqual(len(self.exchange.closed_positions), 3)
        self.assertEqual(len(self.exchange.open_positions), 0)

        self.assertEqual(self.exchange.tp_hits, 2)  # short_simul
        self.assertEqual(self.exchange.sl_hits, 1)  # long_simul
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1)

        # Final closed position notification (long_simul)
        expected_close = (
            "✅ *Position Closed* #Position3\n"
            "Type: *Short*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *15m*\n"
            "Profit: *1*\n"
            "`120.0000` → `94.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `3`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `0`\n"
            "SL Hits: `1`\n"
            "Total Profit: `1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected_close, parse_mode="Markdown")

    def test_realistic_example(self):
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

        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        self.assertEqual(long_pos.profit, 1)
        self.assertEqual(short_pos.profit, 1)
        self.assertEqual(long_sl.profit, -1)        
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1)

        # Tick 2: SL hit for long and short
        self.api.get_current_price.return_value = 100
        self.exchange.tick()

        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        self.assertEqual(long_pos.profit, 1)
        self.assertEqual(short_pos.profit, 1)
        self.assertEqual(long_sl.profit, -1)        
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1)

        self.api.get_current_price.return_value = 190
        self.exchange.tick()
        self.assertEqual(len(self.exchange.open_positions), 0)
        self.assertEqual(len(self.exchange.closed_positions), 3)
        self.assertEqual(long_pos.profit, 1)
        self.assertEqual(short_pos.profit, 1)
        self.assertEqual(long_sl.profit, -1) 
        self.assertEqual(short_pos.duration, "04:22:30")       
        self.assertEqual(self.exchange.tp_hits, 2)
        self.assertEqual(self.exchange.sl_hits, 1)
        self.assertEqual(self.exchange.breakeven_hits, 0)
        self.assertEqual(self.exchange.profits_sum, 1)

        expected = (
            "⛔ *Position Closed* #Position3\n"
            "Type: *Long*\n"
            "Symbol: *BTCUSDT*\n"
            "Timeframe: *4h*\n"
            "Profit: *-1*\n"
            "`300.0000` → `110.0000`\n"
            "Duration: `00:00:00`\n\n\n"
            "📊 *Stats*\n"
            "Closed: `3`\n"
            "Open: `0`\n"
            "TP Hits: `2`\n"
            "EN Hits: `0`\n"
            "SL Hits: `1`\n"
            "Total Profit: `1`\n"
        )
        self.exchange.notifier.send_message.assert_called_with(expected, parse_mode="Markdown")

        expected_positions_history_logs = (
            "type,symbol,interval,entry,initial_sl,initial_tp,exit_price,open_time,close_time,duration,profit\n"
            "Long,BTCUSDT,30m,100.0,90.0,110.0,110,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,1\n"
            "Short,BTCUSDT,1h,200.0,210.0,190.0,110,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,1\n"
            "Long,BTCUSDT,4h,300.0,290.0,310.0,110,2023-11-01 00:00:00,2025-11-05 10:34:54,00:00:00,-1\n"
        )
        self.check_logs(self.positions_history_logs_filename, expected_positions_history_logs)
