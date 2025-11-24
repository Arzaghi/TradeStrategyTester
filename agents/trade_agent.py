import logging
from config import config
from agents.agent_interface import ITradeAgent
from charts.chart_interface import IChart
from exchanges.exchange_interface import IExchange
from strategies.strategy_interface import IStrategy
from structs.position import Position
from structs.signal import Signal


class TradeAgent(ITradeAgent):
    def __init__(self, charts: list[IChart], strategies: list[IStrategy], exchange: IExchange):
        self.charts = charts
        self.strategies = strategies
        self.exchange = exchange

    def analyze(self):
        if not config.enabled("agent.analyze"):
            return
        
        for chart in self.charts:
            try:
                if not chart.have_new_data():
                    continue
                
                for strategy in self.strategies: 
                    signal: Signal | None = strategy.generate_signal(chart)
                    if (
                        signal and 
                        (
                            (signal.type == "Long" and config.enabled("agent.long")) or 
                            (signal.type == "Short" and config.enabled("agent.short"))
                        )
                    ):
                        new_position = Position.generate_position(chart, strategy, signal)

                        duplicate_found = False
                        for open_pos in self.exchange.open_positions:
                            if (new_position.chart.symbol == open_pos.chart.symbol and 
                                new_position.chart.timeframe == open_pos.chart.timeframe and 
                                new_position.type == open_pos.type and
                                new_position.strategy.STRATEGY_NAME == open_pos.strategy.STRATEGY_NAME
                            ):
                                open_pos.sl = new_position.sl
                                open_pos.tp = new_position.tp
                                duplicate_found = True
                                break

                        if not duplicate_found:
                            self.exchange.open_position(new_position)
            except Exception as e:
                logging.info(f"[{chart.symbol} {chart.timeframe}] Error: {e}")
