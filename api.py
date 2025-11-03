import requests
from datetime import datetime

class BinanceAPI:
    BASE_URL = "https://api.binance.com/api/v3"

    def get_candles(self, symbol, interval, limit=2):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] API Called → Symbol: {symbol} | Interval: {interval} | Limit: {limit}")
        response = requests.get(f"{self.BASE_URL}/klines", params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        response.raise_for_status()
        return response.json()

    def get_current_price(self, symbol):
        response = requests.get(f"{self.BASE_URL}/ticker/price", params={"symbol": symbol})
        response.raise_for_status()
        return float(response.json()["price"])
