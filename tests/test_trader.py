import unittest
from trader import TraderBot
from models import Position
import time

class MockAPI:
    def __init__(self):
        self.call_count = 0

    def get_candles(self, symbol, interval, limit=2):
        return [[0, "100", "110", "90", "105"], [1, "0", "0", "0", "0"]]

    def get_current_price(self, symbol):
        self.call_count += 1
        return 110.0 if self.call_count == 1 else 121.0  # Second tick hits TP

class MockStrategy:
    def __init__(self):
        self.called = False

    def generate_signal(self, candles):
        if not self.called:
            self.called = True
            return [
                Position("BTCUSDT", "1h", 1, "2023-01-01 00:00:00", 105, 90, 120, "OPEN", "Long", time.time(), rr_ratio=1.0),
                Position("BTCUSDT", "1h", 1, "2023-01-01 00:00:00", 105, 90, 135, "OPEN", "Long", time.time(), rr_ratio=2.0)
            ]
        return []

class MockLogger:
    def __init__(self):
        self.logged = []

    def write(self, pos):
        self.logged.append(pos)

class TestTraderBot(unittest.TestCase):
    def test_tick_opens_and_closes_positions(self):
        api = MockAPI()
        strategy = MockStrategy()
        logger = MockLogger()
        bot = TraderBot("BTCUSDT", "1h", api, strategy, logger)

        # First tick: open positions
        active = bot.tick(110)
        self.assertEqual(len(active), 2)
        self.assertEqual(len(logger.logged), 0)
        for pos in active:
            self.assertEqual(pos.status, "OPEN")

        # Second tick: price hits TP for the first
        active = bot.tick(121)
        self.assertEqual(len(active), 1)
        self.assertEqual(len(logger.logged), 1)
        self.assertEqual(logger.logged[0].status, "TAKE PROFIT HIT")

        # Third tick: price hits SL for the second position
        active = bot.tick(89)
        self.assertEqual(len(active), 0)
        self.assertEqual(len(logger.logged), 2)
        self.assertEqual(logger.logged[1].status, "STOP LOSS HIT")
