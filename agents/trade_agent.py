from structs.position import Position
from structs.signal import Signal
from agents.agent_interface import ITradeAgent
from strategies.strategy_interface import IStrategy
from charts.chart_interface import IChart

class TradeAgent(ITradeAgent):
    def __init__(self, chart: IChart, strategy: IStrategy):
        self.chart = chart
        self.strategy = strategy

    def analyze(self) -> Position | None:
        try:
            if not self.chart.have_new_data():
                return None

            signal : Signal = self.strategy.generate_signal(self.chart)
            
            if not signal:
                return None

            position = Position.generate_position(self.chart, signal)
            return position

        except Exception as e:
            print(f"[{self.chart.symbol} {self.chart.timeframe}] Error: {e}")
            return None
