from datetime import datetime
import statistics
import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from typing import List

@dataclass
class TrendMetrics:
    atr: float
    adx: float
    plus_di: float
    minus_di: float

@dataclass
class Candle:
    timestamp: int                     # Open time (Unix ms)
    open: float                        # Open price
    high: float                        # High price
    low: float                         # Low price
    close: float                       # Close price
    volume: float                      # Base asset volume
    close_time: int                    # Close time (Unix ms)
    quote_volume: float                # Quote asset volume
    trade_count: int                   # Number of trades
    taker_buy_base_volume: float       # Taker buy base asset volume
    taker_buy_quote_volume: float      # Taker buy quote asset volume

    def __eq__(self, other):
        # Used for comparison in tests
        return isinstance(other, Candle) and all(
            getattr(self, attr) == getattr(other, attr) 
            for attr in ['timestamp', 'open', 'close'] # Compare key attributes
        )

class Timeframe(Enum):
    MINUTE_1    = "1m"
    MINUTE_3    = "3m"
    MINUTE_5    = "5m"
    MINUTE_10   = "10m"
    MINUTE_15   = "15m"
    MINUTE_30   = "30m"
    HOURS_1     = "1h"
    HOURS_2     = "2h"
    HOURS_4     = "4h"
    HOURS_6     = "6h"
    HOURS_8     = "8h"
    HOURS_12    = "12h"
    DAY_1       = "1d"
    DAY_3       = "3d"
    WEEK_1      = "1w"
    MONTH_1     = "1M"

class TrendDirection(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    NEUTRAL = "neutral"

class IChart(ABC):
    def __init__(self, symbol: str, timeframe: Timeframe):
        self._symbol = symbol
        self._timeframe = timeframe
    
    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe
    
    @abstractmethod
    def get_current_candle_time(self) -> datetime:
        pass

    @abstractmethod
    def have_new_data(self, now: datetime = None) -> bool:
        pass

    @abstractmethod
    def get_current_price(self) -> float:
        pass

    @abstractmethod
    def get_recent_raw_ohlcv(self, n: int) -> List[list]:
        pass

    def get_recent_candles(self, n: int) -> List[Candle]:
            raw_candles = self.get_recent_raw_ohlcv(n)
            return [
                Candle(
                    timestamp=int(ts),
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                    close_time=int(ct),
                    quote_volume=float(qv),
                    trade_count=int(tc),
                    taker_buy_base_volume=float(tbv),
                    taker_buy_quote_volume=float(tbqv)
                )
                for ts, o, h, l, c, v, ct, qv, tc, tbv, tbqv, _ in raw_candles
            ]

    def get_recent_dataframes(self, period: int) -> pd.DataFrame:
        """
        Helper to convert raw OHLCV data directly into a Pandas DataFrame,
        bypassing object instantiation for maximum efficiency.
        
        Fetches one extra candle (period + 1) for accurate indicator calculations
        which often require the prior close or delta.
        """
        # Fetch raw data list of lists
        raw_candles = self.get_recent_raw_ohlcv(period + 1) 
        
        if not raw_candles:
            return pd.DataFrame()

        df = pd.DataFrame(raw_candles, columns=[
            'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 
            'close_time', 'quote_volume', 'trade_count', 
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore' # Binance API returns 12 fields
        ])
        
        # Convert necessary columns from string (Binance API output) to float/numeric
        # Only Open, High, Low, Close are needed for OHLCV indicators
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[numeric_cols] = df[numeric_cols].astype(float)
        
        # Clean up and set index
        df.drop(columns=['ignore'], inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # The DataFrame already contains the (period + 1) rows required, so no need 
        # for df.iloc[-(period + 1):] if we assume the API returns the exact limit amount.
        return df

    def get_sma(self, period: int) -> float:
        df = self.get_recent_dataframes(period)
        if df.empty: return 0.0
        
        # ta.sma returns a Series of SMA values
        sma_series = ta.sma(df['Close'], length=period)
        # Return the latest, non-NaN value (the current period's SMA)
        return sma_series.iloc[-1]

    def get_ema(self, period: int) -> float:
        df = self.get_recent_dataframes(period)
        if df.empty: return 0.0
        
        # ta.ema returns a Series of EMA values
        ema_series = ta.ema(df['Close'], length=period)
        return ema_series.iloc[-1]
    
    def get_rsi(self, period: int) -> float:
        df = self.get_recent_dataframes(period + 100)  # Ensure enough data for smoothing
        
        if df.empty or len(df) < period + 20:
            return 50.0  # Fallback

        close = df['Close']
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        rsi = rsi.where(avg_loss != 0, 100)
        rsi = rsi.where(avg_gain != 0, 0)

        rsi_clean = rsi.dropna()
        return rsi_clean.iloc[-1] if not rsi_clean.empty else 50.0

    def get_volatility(self, period: int) -> float:
        closes = [c.close for c in self.get_recent_candles(period)]
        return statistics.stdev(closes) if len(closes) > 1 else 0.0

    def get_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        df = self.get_recent_dataframes(slow + signal + 100)
        if df.empty: return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}

        macd_df = ta.macd(df['Close'], fast=fast, slow=slow, signal=signal)
        
        # The column names are dynamically generated, so we find the last value of each
        macd_line = macd_df.iloc[-1].filter(like='MACD_').iloc[0]
        signal_line = macd_df.iloc[-1].filter(like='MACDs_').iloc[0]
        histogram = macd_df.iloc[-1].filter(like='MACDh_').iloc[0]

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def get_macd_trend(self, fast: int = 12, slow: int = 26, signal: int = 9) -> TrendDirection:
        macd_data = self.get_macd(fast, slow, signal)
        macd = macd_data["macd"]
        signal = macd_data["signal"]

        if macd > signal:
            return TrendDirection.UPTREND
        elif macd < signal:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.NEUTRAL

    def get_bollinger_bands(self, period: int = 20, multiplier: float = 2.0) -> dict:
        df = self.get_recent_dataframes(period)
        if df.empty: return {"upper": 0.0, "middle": 0.0, "lower": 0.0}

        # ta.bbands returns a DataFrame with upper, middle, and lower bands
        bbands_df = ta.bbands(df['Close'], length=period, std=multiplier)

        # The column names are dynamically generated, so we find the last value of each
        upper = bbands_df.iloc[-1].filter(like='BBU_').iloc[0]
        middle = bbands_df.iloc[-1].filter(like='BBM_').iloc[0]
        lower = bbands_df.iloc[-1].filter(like='BBL_').iloc[0]
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
    
    def _compute_trend_components(self, period: int) -> dict:
        """
        Uses pandas_ta ADX function which reliably returns ADX, +DI, and -DI.
        We also include ATR as it is a core component.
        """
        # ADX requires OHLC data
        df = self.get_recent_dataframes(period+100)
        if df.empty:
            return {"atr": 0.0, "adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}

        # ta.adx returns a DataFrame with ADX, +DI, and -DI
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=period)
        
        # ta.atr returns a Series for Average True Range
        atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=period)

        # Get the latest values
        latest = adx_df.iloc[-1]
        adx = latest.filter(like='ADX_').iloc[0]
        plus_di = latest.filter(like='DMP_').iloc[0]
        minus_di = latest.filter(like='DMN_').iloc[0]
        atr = atr_series.iloc[-1]
        
        return {
            "atr": atr,
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    def get_atr(self, period: int) -> float:
        return self._compute_trend_components(period)["atr"]

    def get_adx(self, period: int) -> float:
        return self._compute_trend_components(period)["adx"]

    def get_trend_metrics(self, period: int = 14) -> TrendMetrics:
        data = self._compute_trend_components(period)
        return TrendMetrics(**data)

    def get_trend_direction(self, period: int = 14) -> TrendDirection:
        data = self._compute_trend_components(period)

        if data["adx"] > 25:
            if data["plus_di"] > data["minus_di"]:
                return TrendDirection.UPTREND
            elif data["minus_di"] > data["plus_di"]:
                return TrendDirection.DOWNTREND

        return TrendDirection.NEUTRAL