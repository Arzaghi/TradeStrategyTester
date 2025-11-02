import time
from datetime import datetime
from api import BinanceAPI
from strategy import *
from persistence import CSVLogger
from trader import TraderBot
from utils import clear_screen, get_git_commit_hash, OutputBuffer

CURRENT_VERSION_HASH = get_git_commit_hash()
symbols = ["BTCUSDT","ETHUSDT"]
intervals = ["15m", "1h", "4h"]
ratios = [1,2]

outputBuffer = OutputBuffer()
api = BinanceAPI()
logger = CSVLogger()
bots = [TraderBot(s, i, api, StrategyHammerCandles(s, i, ratios), logger) for s in symbols for i in intervals]

all_active_positions = []

while True:
    try:
        outputBuffer.add(f"Version: {CURRENT_VERSION_HASH}")
        outputBuffer.add(f"StrategyHammerCandles Monitor : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        outputBuffer.add("Open Positions:")
        for i, pos in enumerate(all_active_positions[::-1], 1):
            outputBuffer.add(f"{i}. {pos.symbol} | {pos.interval} | {pos.type} | Entry: {pos.entry:.2f}, SL: {pos.sl:.2f}, TP: {pos.tp:.2f}, RR: {pos.rr_ratio}, Status: {pos.status}")

        all_active_positions = []

        # Cache current prices per symbol
        symbol_prices = {}
        for symbol in symbols:
            try:
                symbol_prices[symbol] = api.get_current_price(symbol)
            except Exception as e:
                outputBuffer.add(f"Error fetching price for {symbol}: {e}")
                symbol_prices[symbol] = None


        for bot in bots:
            price = symbol_prices.get(bot.symbol)
            if price is not None:
                active_positions = bot.tick(price)
                all_active_positions.extend(active_positions)

        outputBuffer.add("----------------------------------------------------------------------")
        outputBuffer.flush()
        time.sleep(2)

    except Exception as e:
        outputBuffer.add(f"Error: {e}")
        outputBuffer.flush()
        time.sleep(5)
