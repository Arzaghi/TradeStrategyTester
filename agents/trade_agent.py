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
                        new_position = Position.generate_position(chart, strategy, signal)
                        new_position.strategy = strategy

                        duplicate_found = False
                        for open_pos in self.exchange.open_positions:
                            if new_position.chart.symbol == open_pos.chart.symbol and new_position.chart.timeframe == open_pos.chart.timeframe and new_position.type == open_pos.type:
                                open_pos.sl = new_position.sl
                                open_pos.tp = new_position.tp
                                duplicate_found = True

                        if not duplicate_found:
                            self.exchange.open_position(new_position)
            except Exception as e:
                print(f"[{chart.symbol} {chart.timeframe}] Error: {e}")
