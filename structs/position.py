from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from charts.chart_interface import IChart
from strategies.strategy_interface import IStrategy
from structs.signal import Signal

@dataclass
class Position:
    chart: IChart
    strategy: IStrategy
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
    current_price = 0

    # class-level counter
    _id_counter: int = 0
    def __post_init__(self):
        type(self)._id_counter += 1
        self.id = type(self)._id_counter

    @classmethod
    def generate_position(cls, chart, strategy: IStrategy, signal: Signal) -> "Position":
        return cls(
            strategy = strategy,
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
        total_seconds = self.close_timestamp - self.open_timestamp
        td = timedelta(seconds=total_seconds)

        total_hours = td.days * 24 + td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60

        return f"{total_hours:02}:{minutes:02}:{seconds:02}"
    
    def to_active_position_row(self):
        active_position_row = {
            "id": self.id,
            "strategy": self.strategy.STRATEGY_NAME,
            "type":  self.type,
            "symbol":  self.chart.symbol,
            "interval":  self.chart.timeframe.value,
            "open_time":  datetime.fromtimestamp(self.open_timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "entry": self.entry,
            "initial_sl": self.initial_sl,
            "current_sl":  self.sl,
            "next_tp":  self.tp,
            "current_profit":  self.profit,
            "current_price": self.current_price
        }
        return active_position_row
    
    def to_history_row(self):
        history_row = {
            "strategy": self.strategy.STRATEGY_NAME,
            "profit": self.profit, 
            "type": self.type, 
            "symbol": self.chart.symbol,
            "interval": self.chart.timeframe.value,
            "entry": self.entry,
            "initial_sl": self.initial_sl,
            "initial_tp": self.initial_tp,
            "exit_price": self.exit_price,
            "open_time": datetime.fromtimestamp(self.open_timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "close_time": datetime.fromtimestamp(self.close_timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "duration": self.duration
        }
        return history_row
