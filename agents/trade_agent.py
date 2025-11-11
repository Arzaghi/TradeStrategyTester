from structs.position import Position
from structs.signal import Signal
from agents.agent_interface import ITradeAgent
from strategies.strategy_interface import IStrategy
from charts.chart_interface import IChart
from exchanges.exchange_interface import IExchange

class TradeAgent(ITradeAgent):
    def __init__(self, charts: list[IChart], strategies: list[IStrategy], exchange: IExchange):
        self.charts = charts
        self.strategies = strategies
        self.exchange = exchange

    def analyze(self):
        for chart in self.charts:
            try:
                if not chart.have_new_data():
                    continue
                for strategy in self.strategies:
                    signal: Signal = strategy.generate_signal(chart)
                    if signal:
                        position = Position.generate_position(chart, signal)
                        position.strategy = strategy
                        self.exchange.open_position(position)
            except Exception as e:
                print(f"[{chart.symbol} {chart.timeframe}] Error: {e}")
