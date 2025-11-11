import time
import os
import logging
from strategies.strategy_hammer_candles import StrategyHammerCandles
from persistence.persistence_interface import PositionsHistoryLogger, CurrentPositionsLogger
from utils import get_git_commit_hash
from notifiers.telegram_notifier import TelegramNotifier
from chart_analyzer import ChartAnalyzer
from exchanges.virtual_exchange import VirtualExchange
from charts.binance_chart import BinanceChart, Timeframe

def main():
    logging.basicConfig(level=logging.INFO)

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT", "TRXUSDT", "DOGEUSDT", "LINKUSDT", "SUIUSDT", "PAXGUSDT"]
    timeframes = [Timeframe.MINUTE_15, Timeframe.MINUTE_30, Timeframe.HOURS_1, Timeframe.HOURS_4, Timeframe.DAY_1, Timeframe.WEEK_1]

    telegram_notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID"))
    positions_history_logger = PositionsHistoryLogger("/HDD/positions_history.csv")
    current_positions_logger = CurrentPositionsLogger("/HDD/current_positions.csv")
    strategy = StrategyHammerCandles()
    analyzers = [ChartAnalyzer(BinanceChart(symbol, timeframe), strategy) for symbol in symbols for timeframe in timeframes]
    exchange = VirtualExchange(api, telegram_notifier, positions_history_logger=positions_history_logger, current_positions_logger=current_positions_logger)

    hello_message = (
        f"Started Version On Server: {get_git_commit_hash()}\n"
        f"Strategy: Hammer but reverse positions.!\n"
        f"Number of Analyzers: {len(analyzers)}\n"
        f"Watching Coins: {symbols}\n"
        f"Watching TimeFrames: {[timeframe.value for timeframe in timeframes]}\n"
    )
    logging.info(hello_message)
    telegram_notifier.send_message(hello_message)

    try:
        while True:
            for analyzer in analyzers:
                position = analyzer.analyze()
                exchange.open_position(position)
            exchange.tick()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
