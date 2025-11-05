from dataclasses import dataclass
from datetime import datetime

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
    rr_ratio: float = 1.0,
    profit: float = -1.0


@dataclass
class Signal:
    entry: float
    sl: float
    tp: float
    type: str