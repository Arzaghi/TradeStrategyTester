import requests
from datetime import datetime, timedelta, timezone
from typing import List
from charts.chart_interface import IChart, Timeframe


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

class BinanceAPI:
    BASE_URL = "https://api.binance.com/api/v3"

    def get_candles(self, symbol, interval, limit=2):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] API Called → Symbol: {symbol} | Interval: {interval} | Limit: {limit}")
        response = requests.get(f"{self.BASE_URL}/klines", params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        response.raise_for_status()
        return response.json()

    def get_current_price(self, symbol):
        response = requests.get(f"{self.BASE_URL}/ticker/price", params={"symbol": symbol})
        response.raise_for_status()
        return float(response.json()["price"])

class BinanceChart(IChart):
    _shared_ohlcv_cache = {}  # key: (symbol, timeframe, n), value: (last_ts, data)

    def __init__(self, symbol: str, timeframe: Timeframe):
        if not BINANCE_INTERVAL_MAP.get(timeframe):
            raise ValueError(f"Unsupported timeframe: {timeframe.value}")
        super().__init__(symbol, timeframe)
        self._binance_api = BinanceAPI()
        self.last_seen_candle_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def get_current_candle_time(self) -> datetime:
        return self.last_seen_candle_dt

    def get_current_price(self) -> float:
        return self._binance_api.get_current_price(self.symbol)

    def get_recent_raw_ohlcv(self, n: int) -> List[list]:        
        interval_str = BINANCE_INTERVAL_MAP.get(self.timeframe)
        if not interval_str:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

        cache_key = (self.symbol, self.timeframe, n)
        cached = BinanceChart._shared_ohlcv_cache.get(cache_key)

        if cached and not self.have_new_data():
            _, data = cached
            return data

        # Fetch fresh data
        data = self._binance_api.get_candles(
            symbol=self.symbol,
            interval=interval_str,
            limit=n
        )

        if data:
            self.last_seen_candle_dt = datetime.fromtimestamp(data[-1][0] / 1000, tz=timezone.utc)
            BinanceChart._shared_ohlcv_cache[cache_key] = (self.last_seen_candle_dt, data)

        return data
    
    def get_next_candle_time(self) -> datetime:
        interval = self.timeframe.value
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == "m":
            # Round to next multiple of `value` minutes
            total_minutes = self.last_seen_candle_dt.hour * 60 + self.last_seen_candle_dt.minute
            next_total_minutes = ((total_minutes // value) + 1) * value
            next_hour = next_total_minutes // 60
            next_minute = next_total_minutes % 60
            next_dt = self.last_seen_candle_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_hour, minutes=next_minute)
            return next_dt.replace(tzinfo=timezone.utc)

        if unit == "h":
            # Round to next multiple of `value` hours
            next_hour = ((self.last_seen_candle_dt.hour // value) + 1) * value
            next_dt = self.last_seen_candle_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_hour)
            if next_dt.date() > self.last_seen_candle_dt.date():
                next_dt = datetime.combine(self.last_seen_candle_dt.date() + timedelta(days=1), datetime.min.time())
            return next_dt.replace(tzinfo=timezone.utc)

        if unit == "d":
            next_dt = datetime.combine(self.last_seen_candle_dt.date() + timedelta(days=value), datetime.min.time())
            return next_dt.replace(tzinfo=timezone.utc)

        if unit == "w":
            days_until_next_monday = (7 - self.last_seen_candle_dt.weekday()) % 7
            if days_until_next_monday == 0:
                days_until_next_monday = 7  # If already Monday, go to next Monday
            next_monday = self.last_seen_candle_dt.date() + timedelta(days=days_until_next_monday)
            next_dt = datetime.combine(next_monday, datetime.min.time())
            return next_dt.replace(tzinfo=timezone.utc)

        raise ValueError(f"Unsupported interval format: {interval}")
    
    def have_new_data(self, now: datetime = None) -> bool:
        if now is None:
            now = datetime.now(timezone.utc)
        next_candle_time = self.get_next_candle_time()
        return now >= next_candle_time
