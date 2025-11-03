from dataclasses import dataclass
from datetime import datetime

@dataclass
class Position:
    symbol: str
    interval: str
    candle_time: int
    open_time: str
    entry: float
    sl: float
    tp: float
    status: str
    type: str
    start_timestamp: float
    close_time: str = ""
    duration: int = 0
    exit_price: float = 0.0
    exit_reason: str = ""
    rr_ratio: float = 1.0


@dataclass
class Signal:
    entry: float
    sl: float
    tp: float
    type: str