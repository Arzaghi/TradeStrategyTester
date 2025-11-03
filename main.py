import time
import os
from datetime import datetime
from api import BinanceAPI
from strategy import *
from persistence import CSVLogger
from trader import TraderBot
from utils import clear_screen, get_git_commit_hash, OutputBuffer
from telegram_notifier import TelegramNotifier
from strategy_watcher import CoinWatcher
from strategy import StrategyHammerCandles

CURRENT_VERSION_HASH = get_git_commit_hash()
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT"]
intervals = ["5m", "15m", "30m", "1h", "4h", "1d", "1w"]

outputBuffer = OutputBuffer()
telegram = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID")) # Read from Github secrets and set it in docker image
api = BinanceAPI()
logger = CSVLogger()
strategy = StrategyHammerCandles()
watchers = [CoinWatcher(symbol, interval, api, strategy, telegram) for symbol in symbols for interval in intervals]


Message= ""
Message += f"Started Version On Server: {CURRENT_VERSION_HASH}\n"
Message += "Number of Watchers: " + str(len(watchers)) + "\n"
Message += "Watching Coins: " + str(symbols) + "\n"
Message += "Watching TimeFrames: " + str(intervals) + "\n"
print(Message)
telegram.send_message(Message)


while True:
    for watcher in watchers:
        watcher.watch()
    time.sleep(1)
