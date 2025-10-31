from models import Position
from datetime import datetime
import time

class TraderBot:
    def __init__(self, symbol, interval, api, strategy, logger):
        self.symbol = symbol
        self.interval = interval
        self.api = api
        self.strategy = strategy
        self.logger = logger
        self.positions = []

    def tick(self, current_price: float):
        candles = self.api.get_candles(self.symbol, self.interval)

        new_position = self.strategy.generate_signal(candles)
        if new_position:
            self.positions.append(new_position)

        active = []
        for pos in self.positions:
            if pos.status == "OPEN":
                if pos.type == "Buy":
                    if current_price <= pos.sl:
                        pos.status, pos.exit_price, pos.exit_reason = "STOP LOSS HIT", current_price, "SL"
                    elif current_price >= pos.tp:
                        pos.status, pos.exit_price, pos.exit_reason = "TAKE PROFIT HIT", current_price, "TP"
                elif pos.type == "Sell":
                    if current_price >= pos.sl:
                        pos.status, pos.exit_price, pos.exit_reason = "STOP LOSS HIT", current_price, "SL"
                    elif current_price <= pos.tp:
                        pos.status, pos.exit_price, pos.exit_reason = "TAKE PROFIT HIT", current_price, "TP"

            if pos.status != "OPEN":
                pos.close_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                pos.duration = int(time.time() - pos.start_timestamp)
                self.logger.write(pos)
            else:
                active.append(pos)

        self.positions = active
        return active
