from dataclasses import dataclass
from charts.chart_interface import Timeframe

@dataclass
class Signal:
    entry: float
    sl: float
    tp: float
    type: str


@dataclass
class Position:
    symbol: str
    interval: Timeframe    
    entry: float
    initial_sl: float
    initial_tp: float
    sl: float
    tp: float    
    type: str
    status: str = ""
    open_timestamp: int = 0
    close_timestamp: int = 0
    duration: int = 0
    exit_price: float = 0
    exit_reason: str = ""
    profit: float = 0

    @classmethod
    def generate_position(cls, chart, signal: Signal) -> "Position":
        return cls(
            symbol=chart.symbol,
            interval=chart.timeframe,
            entry=signal.entry,
            initial_sl=signal.sl,
            initial_tp=signal.tp,
            sl=signal.sl,
            tp=signal.tp,
            type=signal.type,
        )


