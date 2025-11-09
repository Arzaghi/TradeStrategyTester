from dataclasses import dataclass

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
    

@dataclass
class Position:
    symbol: str
    interval: str
    candle_time: int
    open_time: str
    entry: float
    initial_sl: float
    initial_tp: float
    sl: float
    tp: float
    status: str
    type: str
    start_timestamp: float
    close_time: str = ""
    duration: str = ""
    exit_price: float = 0.0
    exit_reason: str = ""
    rr_ratio: float = 1.0
    profit: float = -1.0


@dataclass
class Signal:
    entry: float
    sl: float
    tp: float
    type: str

@dataclass
class TrendMetrics:
    atr: float
    adx: float
    plus_di: float
    minus_di: float
