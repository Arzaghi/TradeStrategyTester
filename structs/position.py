from dataclasses import dataclass
from datetime import timedelta
from charts.chart_interface import IChart
from structs.signal import Signal

@dataclass
class Position:
    chart: IChart   
    entry: float
    initial_sl: float
    initial_tp: float
    sl: float
    tp: float    
    type: str
    status: str = ""
    open_timestamp: int = 0
    close_timestamp: int = 0

    exit_price: float = 0
    exit_reason: str = ""
    profit: float = 0

    # class-level counter
    _id_counter: int = 0
    def __post_init__(self):
        type(self)._id_counter += 1
        self.id = type(self)._id_counter

    @classmethod
    def generate_position(cls, chart, signal: Signal) -> "Position":
        return cls(
            chart = chart,
            entry=signal.entry,
            initial_sl=signal.sl,
            initial_tp=signal.tp,
            sl=signal.sl,
            tp=signal.tp,
            type=signal.type,
        )

    @property
    def duration(self) -> str:
        if self.open_timestamp == 0 or self.close_timestamp == 0:
            return ""
        seconds = self.close_timestamp - self.open_timestamp
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        days = td.days
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
        return " ".join(parts)
