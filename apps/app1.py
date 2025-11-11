import logging
import os
from strategies.strategy_hammer_candles import StrategyHammerCandles
from persistence.csv_persistence import CSVPersistence
from structs.utils import get_git_commit_hash
from notifiers.telegram_notifier import TelegramNotifier
from agents.trade_agent import TradeAgent
from exchanges.virtual_exchange import VirtualExchange
from charts.binance_chart import BinanceChart, Timeframe

class App1:    
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT", "TRXUSDT", "DOGEUSDT", "LINKUSDT", "SUIUSDT", "PAXGUSDT"]
        timeframes = [Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOURS_1, Timeframe.HOURS_4, Timeframe.DAY_1, Timeframe.WEEK_1]
        telegram_notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID"))

        positions_history_logger = CSVPersistence("/HDD/positions_history.csv", True)
        current_positions_logger = CSVPersistence("/HDD/current_positions.csv", False)
        strategies = [StrategyHammerCandles()]
        charts = [BinanceChart(symbol, tf) for symbol in symbols for tf in timeframes]
        self.virtual_exchange = VirtualExchange(telegram_notifier, positions_history_logger, current_positions_logger)
        self.agent = TradeAgent(charts, strategies, self.virtual_exchange)

        hello_message = (
            f"Started Version On Server: {get_git_commit_hash()}"
        )
        logging.info(hello_message)
        telegram_notifier.send_message(hello_message)

    def tick(self):
        self.agent.analyze()
        self.virtual_exchange.tick()
