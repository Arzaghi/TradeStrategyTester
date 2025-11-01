from models import Position
from datetime import datetime
import time
from enum import Enum

class HammerCandle(Enum):
    NON_HAMMER = 0
    BULLISH_HAMMER = 1
    BEARISH_HAMMER = 2

class StrategyAllCandles:
    def __init__(self, symbol, interval, reward_to_risk_ratios=[1.0]):
        self.symbol = symbol
        self.interval = interval
        self.reward_to_risk_ratios = reward_to_risk_ratios
        self.last_candle_time = None

    def generate_signal(self, candles):
        prev = candles[-2]
        open_, high, low, close = map(float, (prev[1], prev[2], prev[3], prev[4]))
        candle_time = candles[-1][0]
        readable_time = datetime.fromtimestamp(prev[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        if self.last_candle_time == readable_time:
            return []

        self.last_candle_time = readable_time
        entry = close
        positions = []

        if close > open_:
            sl = low
            risk = entry - sl
            for rr in self.reward_to_risk_ratios:
                tp = entry + risk * rr
                positions.append(Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Buy", time.time(), rr_ratio=rr))

        elif close < open_:
            sl = high
            risk = sl - entry
            for rr in self.reward_to_risk_ratios:
                tp = entry - risk * rr
                positions.append(Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Sell", time.time(), rr_ratio=rr))

        return positions

class StrategyHammerCandles:
    def __init__(self, symbol, interval, reward_to_risk_ratios=[1.0]):
        self.symbol = symbol
        self.interval = interval
        self.reward_to_risk_ratios = reward_to_risk_ratios
        self.last_candle_time = None

    def candle_hammer_type(self, open_, high, low, close):
        MIN_SHADOW_TO_BODY_RATIO = 2.0
        MAX_OPPOSITE_SHADOW_RATIO = 0.2

        body_size = abs(close - open_)
        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low

        is_green_candle = close > open_
        is_red_candle = close < open_

        if is_green_candle:
            has_long_lower_shadow = lower_shadow >= MIN_SHADOW_TO_BODY_RATIO * body_size
            has_short_upper_shadow = upper_shadow <= MAX_OPPOSITE_SHADOW_RATIO * lower_shadow
            if has_long_lower_shadow and has_short_upper_shadow:
                return HammerCandle.BULLISH_HAMMER

        elif is_red_candle:
            has_long_upper_shadow = upper_shadow >= MIN_SHADOW_TO_BODY_RATIO * body_size
            has_short_lower_shadow = lower_shadow <= MAX_OPPOSITE_SHADOW_RATIO * upper_shadow
            if has_long_upper_shadow and has_short_lower_shadow:
                return HammerCandle.BEARISH_HAMMER

        return HammerCandle.NON_HAMMER

    def generate_signal(self, candles):
        prev = candles[-2]
        open_, high, low, close = map(float, (prev[1], prev[2], prev[3], prev[4]))
        candle_time = candles[-1][0]
        readable_time = datetime.fromtimestamp(prev[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        if self.last_candle_time == readable_time:
            return []

        self.last_candle_time = readable_time
        hammer_type = self.candle_hammer_type(open_, high, low, close)
        positions = []
        entry = close

        if hammer_type == HammerCandle.BULLISH_HAMMER:
            sl = low
            risk = entry - sl
            for rr in self.reward_to_risk_ratios:
                tp = entry + risk * rr
                positions.append(Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Buy", time.time(), rr_ratio=rr))

        elif hammer_type == HammerCandle.BEARISH_HAMMER:
            sl = high
            risk = sl - entry
            for rr in self.reward_to_risk_ratios:
                tp = entry - risk * rr
                positions.append(Position(self.symbol, self.interval, candle_time, readable_time, entry, sl, tp, "OPEN", "Sell", time.time(), rr_ratio=rr))

        return positions
