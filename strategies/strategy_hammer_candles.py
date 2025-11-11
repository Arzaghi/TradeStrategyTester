from enum import Enum
from typing import Optional
from charts.chart_interface import IChart
from structs.signal import Signal
from strategies.strategy_interface import IStrategy

class HammerCandle(Enum):
    NON_HAMMER = 0
    BULLISH_HAMMER = 1
    BEARISH_HAMMER = 2

class HammerCandle(Enum):
    NON_HAMMER = 0
    BULLISH_HAMMER = 1
    BEARISH_HAMMER = 2

class StrategyHammerCandles(IStrategy):
    STRATEGY_NAME = "Hammer Candle"

    def _candle_hammer_type(self, open_, high, low, close):
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

    def generate_signal(self, chart: IChart) -> Optional[Signal]:
        candles = chart.get_recent_candles(2)
        if len(candles) < 2:
            return None

        open_, high, low, close = candles[0].open, candles[0].high, candles[0].low, candles[0].close
        hammer_type = self._candle_hammer_type(open_, high, low, close)
        if hammer_type == HammerCandle.BULLISH_HAMMER:
            bottom_shadow = min(open_, close) - low
            sl = low + (bottom_shadow / 2)
            tp = close + (close - sl)
            return Signal(entry=close, sl=sl, tp=tp, type="Long")

        elif hammer_type == HammerCandle.BEARISH_HAMMER:
            top_shadow = high - max(open_, close)
            sl = high - (top_shadow / 2)
            tp = close - (sl - close)
            return Signal(entry=close, sl=sl, tp=tp, type="Short")

        return None
