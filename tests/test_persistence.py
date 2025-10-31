import unittest
from unittest.mock import mock_open, patch
from persistence import CSVLogger
from models import Position
import time

class TestCSVLogger(unittest.TestCase):
    @patch("persistence.os.path.isfile", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    def test_write_creates_file_with_header(self, mock_file, mock_exists):
        logger = CSVLogger("test.csv")
        pos = Position("BTCUSDT", "1h", 1, "2023-01-01 00:00:00", 100, 90, 110, "STOP LOSS HIT", "Buy", time.time(), "2023-01-01 01:00:00", 3600, 90, "SL")
        logger.write(pos)
        handle = mock_file()
        self.assertTrue(handle.write.called)
