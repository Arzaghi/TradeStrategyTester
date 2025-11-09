import time
import os
import logging
from api import BinanceAPI
from strategies.strategy_hammer_candles import StrategyHammerCandles
from persistence import PositionsHistoryLogger, CurrentPositionsLogger
from utils import get_git_commit_hash
from notifiers.telegram_notifier import TelegramNotifier
from coin_watcher import CoinWatcher
from virtual_exchange import VirtualExchange
from charts.binance_chart import BinanceChart, Timeframe

def main():
    logging.basicConfig(level=logging.INFO)

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT", "TRXUSDT", "DOGEUSDT", "LINKUSDT", "SUIUSDT", "PAXGUSDT"]
    intervals = ["15m", "30m", "1h", "4h", "1d", "1w"]

    telegram_notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID"))
    api = BinanceAPI()
    positions_history_logger = PositionsHistoryLogger("/HDD/positions_history.csv")
    current_positions_logger = CurrentPositionsLogger("/HDD/current_positions.csv")
    strategy = StrategyHammerCandles()
    watchers = [CoinWatcher(symbol, interval, api, strategy, None) for symbol in symbols for interval in intervals]
    exchange = VirtualExchange(api, telegram_notifier, positions_history_logger=positions_history_logger, current_positions_logger=current_positions_logger)

    hello_message = (
        f"Started Version On Server: {get_git_commit_hash()}\n"
        f"Number of Watchers: {len(watchers)}\n"
        f"Watching Coins: {symbols}\n"
        f"Watching TimeFrames: {intervals}\n"
    )
    logging.info(hello_message)
    telegram_notifier.send_message(hello_message)

    try:
        while True:
            for watcher in watchers:
                position = watcher.watch()
                exchange.open_position(position)
            exchange.tick()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
