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

        new_positions = self.strategy.generate_signal(candles)
        if new_positions:
            self.positions.extend(new_positions)

        active = []
        for pos in self.positions:
            if pos.status == "OPEN":
                if pos.type == "Long":
                    if current_price <= pos.sl:
                        pos.status = "STOP LOSS HIT"
                        pos.exit_price = current_price
                        pos.exit_reason = "SL"
                    elif current_price >= pos.tp:
                        pos.status = "TAKE PROFIT HIT"
                        pos.exit_price = current_price
                        pos.exit_reason = "TP"
                elif pos.type == "Short":
                    if current_price >= pos.sl:
                        pos.status = "STOP LOSS HIT"
                        pos.exit_price = current_price
                        pos.exit_reason = "SL"
                    elif current_price <= pos.tp:
                        pos.status = "TAKE PROFIT HIT"
                        pos.exit_price = current_price
                        pos.exit_reason = "TP"

            if pos.status != "OPEN":
                pos.close_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                pos.duration = int(time.time() - pos.start_timestamp)
                self.logger.write(pos)
            else:
                active.append(pos)

        self.positions = active
        return active
