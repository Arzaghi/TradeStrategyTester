from models import Position
from datetime import datetime
import time

class Strategy:
    def __init__(self, symbol, interval, reward_to_risk_ratio=1.0):
        self.symbol = symbol
        self.interval = interval
        self.reward_to_risk_ratio = reward_to_risk_ratio
        self.last_candle_time = None

    def generate_signal(self, candles):
        prev = candles[-2]
        open_, high, low, close = map(float, (prev[1], prev[2], prev[3], prev[4]))
        candle_time = candles[-1][0]
        readable_time = datetime.fromtimestamp(prev[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        if self.last_candle_time == readable_time:
            return None

        self.last_candle_time = readable_time
        entry = close

        if close > open_:
            sl = low
            risk = entry - sl
            tp = entry + risk * self.reward_to_risk_ratio
            return Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Buy", time.time(), rr_ratio=self.reward_to_risk_ratio)

        elif close < open_:
            sl = high
            risk = sl - entry
            tp = entry - risk * self.reward_to_risk_ratio
            return Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Sell", time.time(), rr_ratio=self.reward_to_risk_ratio)

        return None
