import time
import unittest
from structs.utils import get_utc_now_timestamp

class TestUtils(unittest.TestCase):
    def test_current_timestamp_returns_utc_now(self):
        # Get UTC time from time
        utc_now = int(time.time())
        ts = get_utc_now_timestamp()

        # Allow small drift due to execution time
        self.assertTrue(abs(ts - utc_now) <= 1)

