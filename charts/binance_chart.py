import statistics
from typing import List
from charts.chart_interface import IChart, Timeframe, Candle
from api import BinanceAPI

BINANCE_INTERVAL_MAP = {
    Timeframe.MINUTE_1    : "1m",
    Timeframe.MINUTE_3    : "3m",
    Timeframe.MINUTE_5    : "5m",
    # Binance does not support 10-minute candles at the moment!
    Timeframe.MINUTE_15   : "15m",
    Timeframe.MINUTE_30   : "30m",
    Timeframe.HOURS_1     : "1h",
    Timeframe.HOURS_2     : "2h",
    Timeframe.HOURS_4     : "4h",
    Timeframe.HOURS_6     : "6h",
    Timeframe.HOURS_8     : "8h",
    Timeframe.HOURS_12    : "12h",
    Timeframe.DAY_1       : "1d",
    Timeframe.DAY_3       : "3d",
    Timeframe.WEEK_1      : "1w",
    Timeframe.MONTH_1     : "1M",
}

class BinanceChart(IChart):
    def __init__(self, symbol: str, timeframe: Timeframe):
        if not BINANCE_INTERVAL_MAP.get(timeframe):
            raise ValueError(f"Unsupported timeframe: {timeframe.value}")
        super().__init__(symbol, timeframe)
        self._binance_api = BinanceAPI()

    def get_current_price(self) -> float:
        return self._binance_api.get_current_price(self.symbol)

    def _get_recent_raw_ohlcv(self, n: int) -> List[list]:
        interval = BINANCE_INTERVAL_MAP.get(self.timeframe)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")
        
        data = self._binance_api.get_candles(
            symbol=self.symbol,
            interval=interval,
            limit=n
        )
        return data
