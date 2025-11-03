from enum import Enum
from models import Signal

class HammerCandle(Enum):
    NON_HAMMER = 0
    BULLISH_HAMMER = 1
    BEARISH_HAMMER = 2

class StrategyHammerCandles:
    STRATEGY_NAME = "Hammer Candle"
    REQUIRED_CANDLES = 2 # Current and Previous Candle

    def __init__(self):
        pass

    def candle_hammer_type(self, open_, high, low, close):
        MIN_SHADOW_TO_BODY_RATIO = 2.0
        MAX_OPPOSITE_SHADOW_RATIO = 0.2

        body_size = abs(close - open_)
        if body_size == 0:
            return HammerCandle.NON_HAMMER

        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low

        is_candle_green = close > open_
        is_candle_red = close < open_

        if is_candle_green and \
            lower_shadow >= MIN_SHADOW_TO_BODY_RATIO * body_size and \
            upper_shadow <= MAX_OPPOSITE_SHADOW_RATIO * lower_shadow:
                return HammerCandle.BULLISH_HAMMER

        elif is_candle_red and \
            upper_shadow >= MIN_SHADOW_TO_BODY_RATIO * body_size and \
            lower_shadow <= MAX_OPPOSITE_SHADOW_RATIO * upper_shadow:
                return HammerCandle.BEARISH_HAMMER

        return HammerCandle.NON_HAMMER

    def generate_signal(self, candles):
        if len(candles) < self.REQUIRED_CANDLES:
            return None

        candle = candles[0] # Previous Closed Candle
        open_, high, low, close = map(float, (candle[1], candle[2], candle[3], candle[4]))

        hammer_type = self.candle_hammer_type(open_, high, low, close)
        if hammer_type == HammerCandle.BULLISH_HAMMER:
            return Signal(entry=high, sl=low, type="Long")
        elif hammer_type == HammerCandle.BEARISH_HAMMER:
            return Signal(entry=low, sl=high, type="Short")
        else:
            return None