from enum import Enum
from typing import Optional
from charts.chart_interface import IChart, TrendDirection
from structs.signal import Signal
from strategies.strategy_interface import IStrategy

class FullBodyCandle(Enum):
    NONE = 0
    FULL_BODY_GREEN = 1
    FULL_BODY_RED = 2

class StrategyFullBodyInMacdZones(IStrategy):
    STRATEGY_NAME = "FBdy+MCD"

    def _candle_full_body_type(self, open_, high, low, close):
        body = abs(close - open_)
        range_ = high - low
        if range_ == 0:
            return FullBodyCandle.NONE  # Avoid division by zero

        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low

        body_ratio = body / range_
        shadow_ratio = (upper_shadow + lower_shadow) / range_

        if close > open_ and body_ratio >= 0.8 and shadow_ratio <= 0.2:
            return FullBodyCandle.FULL_BODY_GREEN
        elif close < open_ and body_ratio >= 0.8 and shadow_ratio <= 0.2:
            return FullBodyCandle.FULL_BODY_RED
        else:
            return FullBodyCandle.NONE

    def generate_signal(self, chart: IChart) -> Optional[Signal]:
        candles = chart.get_recent_candles(2)
        if len(candles) < 2:
            return None

        open_, high, low, close = candles[0].open, candles[0].high, candles[0].low, candles[0].close
        candle_type = self._candle_full_body_type(open_, high, low, close)
        macd_trend = chart.get_macd_trend()
        if candle_type == FullBodyCandle.FULL_BODY_GREEN and macd_trend == TrendDirection.UPTREND:
            sl = open_
            tp = close + (close - sl)*3
            return Signal(entry=close, sl=sl, tp=tp, type="Long")

        elif candle_type == FullBodyCandle.FULL_BODY_RED and macd_trend == TrendDirection.DOWNTREND:
            sl = open_
            tp = close - 3*(sl - close)
            return Signal(entry=close, sl=sl, tp=tp, type="Short")

        return None
