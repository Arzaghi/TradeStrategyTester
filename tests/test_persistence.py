import unittest
from unittest.mock import mock_open, patch, call
from persistence import CSVLogger
from models import Position
import time

class TestCSVLogger(unittest.TestCase):
    @patch("persistence.os.path.isfile", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    def test_write_creates_file_with_all_fields(self, mock_file, mock_exists):
        logger = CSVLogger("test.csv")
        pos = Position(
            symbol="BTCUSDT",
            interval="1h",
            candle_time=1,
            open_time="2023-01-01 00:00:00",
            entry=100,
            sl=90,
            tp=110,
            status="STOP LOSS HIT",
            type="Long",
            start_timestamp=time.time(),
            close_time="2023-01-01 01:00:00",
            duration=3600,
            exit_price=90,
            exit_reason="SL",
            rr_ratio=1.5
        )

        logger.write(pos)

        # Get the actual calls to write()
        handle = mock_file()
        written_lines = [call_arg[0][0] for call_arg in handle.write.call_args_list]

        # Extract header and row
        header = written_lines[0].strip().split(",")
        row = written_lines[1].strip().split(",")

        # Check header matches Position fields
        expected_fields = list(Position.__annotations__.keys())
        self.assertEqual(header, expected_fields)

        # Check row length matches header length
        self.assertEqual(len(row), len(expected_fields))
