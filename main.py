import time
import os
from api import BinanceAPI
from strategy import *
from persistence import CSVLogger
from utils import get_git_commit_hash, OutputBuffer
from telegram_notifier import TelegramNotifier
from coin_watcher import CoinWatcher
from strategy import StrategyHammerCandles
from virtual_exchange import VirtualExchange

CURRENT_VERSION_HASH = get_git_commit_hash()
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT"]
intervals = ["5m", "15m", "30m", "1h", "4h", "1d", "1w"]

outputBuffer = OutputBuffer()
telegram = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID")) # Read from Github Secrets
api = BinanceAPI()
logger = CSVLogger()
strategy = StrategyHammerCandles()
watchers = [CoinWatcher(symbol, interval, api, strategy, None) for symbol in symbols for interval in intervals]
exchange = VirtualExchange(api, telegram, logger)

Message= ""
Message += f"Started Version On Server: {CURRENT_VERSION_HASH}\n"
Message += "Number of Watchers: " + str(len(watchers)) + "\n"
Message += "Watching Coins: " + str(symbols) + "\n"
Message += "Watching TimeFrames: " + str(intervals) + "\n"
print(Message)
telegram.send_message(Message)


while True:
    for watcher in watchers:
        position = watcher.watch()
        exchange.open_position(position)

    exchange.tick()
    time.sleep(1)