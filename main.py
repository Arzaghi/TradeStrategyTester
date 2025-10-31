import time
from datetime import datetime
from api import BinanceAPI
from strategy import Strategy
from persistence import CSVLogger
from trader import TraderBot
from utils import clear_screen, OutputBuffer

symbols = ["BTCUSDT"]
intervals = ["15m", "1h", "4h"]
ratios = [1,2,3,4,5]

outputBuffer = OutputBuffer()
api = BinanceAPI()
logger = CSVLogger()
bots = [TraderBot(s, i, api, Strategy(s, i, r), logger) for s in symbols for i in intervals for r in ratios]

all_active_positions = []

while True:
    try:
        
        outputBuffer.add(f"--- Strategy Monitor --- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
                symbol_prices[symbol] = None  # fallback


        for bot in bots:
            price = symbol_prices.get(bot.symbol)
            if price is not None:
                active_positions = bot.tick(price)
                all_active_positions.extend(active_positions)

        clear_screen()
        outputBuffer.flush()
        time.sleep(2)

    except Exception as e:
        outputBuffer.add(f"Error: {e}")
        outputBuffer.flush()
        time.sleep(5)
