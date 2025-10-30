import requests
import time
import os
import csv
from datetime import datetime


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


class TraderBot:
    def __init__(self, symbol, interval):
        self.symbol = symbol
        self.interval = interval
        self.last_processed_candle = None
        self.positions = []
        
    def get_candles(self):
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": 2
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_current_price(self):
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": self.symbol}
        response = requests.get(url, params=params)
        return float(response.json()["price"])

    def write_to_csv(self, position):
        filename = "logs.csv"
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Symbol", "Interval",
                    "Open Time", "Close Time", "Duration (s)", "Type",
                    "Entry", "SL", "TP", "Exit Price", "Exit Reason"
                ])
            writer.writerow([
                position["symbol"],
                position["interval"],
                position["open_time"],
                position["close_time"],
                position["duration"],
                position["type"],
                f"{position['entry']:.2f}",
                f"{position['sl']:.2f}",
                f"{position['tp']:.2f}",
                f"{position['exit_price']:.2f}",
                position["exit_reason"]
            ])

    def tick(self):
        candles = self.get_candles()
        prev = candles[-2]
        prev_open = float(prev[1])
        prev_high = float(prev[2])
        prev_low = float(prev[3])
        prev_close = float(prev[4])
        current_price = self.get_current_price()

        current_candle_time = candles[-1][0]
        
        readable_open_time = datetime.fromtimestamp(prev[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # If candle changed
        if self.last_processed_candle != readable_open_time:
            self.last_processed_candle = readable_open_time
            if prev_close > prev_open:
                # Buy setup
                entry = prev_close
                sl = prev_low
                tp = entry + (entry - sl)
                self.positions.append({
                    "symbol": self.symbol,
                    "interval": self.interval,
                    "candle_time": current_candle_time,
                    "open_time": readable_open_time,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "status": "OPEN",
                    "type": "Buy",
                    "start_timestamp": time.time()
                })
            elif prev_close < prev_open:
                # Sell setup
                entry = prev_close
                sl = prev_high
                tp = entry - (sl - entry)
                self.positions.append({
                    "symbol": self.symbol,
                    "interval": self.interval,
                    "candle_time": current_candle_time,
                    "open_time": readable_open_time,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "status": "OPEN",
                    "type": "Sell",
                    "start_timestamp": time.time()
                })

        # Update positions
        active_positions = []
        for pos in self.positions:
            if pos["status"] == "OPEN":
                if pos["type"] == "Buy":
                    if current_price <= pos["sl"]:
                        pos["status"] = "STOP LOSS HIT"
                        pos["exit_price"] = current_price
                        pos["exit_reason"] = "SL"
                    elif current_price >= pos["tp"]:
                        pos["status"] = "TAKE PROFIT HIT"
                        pos["exit_price"] = current_price
                        pos["exit_reason"] = "TP"
                elif pos["type"] == "Sell":
                    if current_price >= pos["sl"]:
                        pos["status"] = "STOP LOSS HIT"
                        pos["exit_price"] = current_price
                        pos["exit_reason"] = "SL"
                    elif current_price <= pos["tp"]:
                        pos["status"] = "TAKE PROFIT HIT"
                        pos["exit_price"] = current_price
                        pos["exit_reason"] = "TP"

            if pos["status"] != "OPEN":
                pos["close_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                pos["duration"] = int(time.time() - pos["start_timestamp"])
                self.write_to_csv(pos)
            else:
                active_positions.append(pos)

        self.positions = active_positions
        return active_positions





symbols = ["BTCUSDT"]
intervals = ["15m", "1h", "4h"]

# Create all bot instances
bots = [TraderBot(symbol, interval) for symbol in symbols for interval in intervals]
all_active_positions = []
while True:
    try:
        clear_screen()
        print(f"--- Strategy Monitor --- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Display all active positions
        print("Open Positions:")
        for i, pos in enumerate(all_active_positions[::-1], 1):
            print(f"{i}. {pos['symbol']} | {pos['interval']} | {pos['type']} | Entry: {pos['entry']:.2f}, SL: {pos['sl']:.2f}, TP: {pos['tp']:.2f}, Status: {pos['status']}")

        all_active_positions = []

        for bot in bots:
            active_positions = bot.tick()
            all_active_positions.extend(active_positions)



        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
