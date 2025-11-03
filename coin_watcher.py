import time
from models import Signal, Position
from datetime import datetime, timedelta, timezone

class CoinWatcher:
    def __init__(self, symbol: str, interval: str, api, strategy, notifier):
        self.symbol = symbol
        self.interval = interval
        self.api = api
        self.strategy = strategy
        self.notifier = notifier
        self.last_processed_candle_time = None

    def watch(self) -> Position | None:
        try:
            if not self._is_new_candle_due():
                return None

            candles = self.api.get_candles(self.symbol, self.interval, limit=self.strategy.REQUIRED_CANDLES)
            current_candle_time = candles[-1][0]
            if self.last_processed_candle_time == current_candle_time:
                return None

            self.last_processed_candle_time = current_candle_time
            signal = self.strategy.generate_signal(candles)
            if not signal:
                return None

            self.send_alert(signal)

            position = Position(
                symbol=self.symbol,
                interval=self.interval,
                candle_time=current_candle_time,
                open_time=datetime.fromtimestamp(current_candle_time / 1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                entry=signal.entry,
                sl=signal.sl,
                tp=signal.tp,
                status="open",
                type=signal.type,
                start_timestamp=time.time()
            )
            return position

        except Exception as e:
            print(f"[{self.symbol} {self.interval}] Error: {e}")
            return None

    def get_next_candle_time(last_candle_ms: int, interval: str) -> datetime:
        last_dt = datetime.fromtimestamp(last_candle_ms / 1000)
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == "m":
            # Round to next multiple of `value` minutes
            total_minutes = last_dt.hour * 60 + last_dt.minute
            next_total_minutes = ((total_minutes // value) + 1) * value
            next_hour = next_total_minutes // 60
            next_minute = next_total_minutes % 60
            next_dt = last_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_hour, minutes=next_minute)
            return next_dt

        elif unit == "h":
            # Round to next multiple of `value` hours
            next_hour = ((last_dt.hour // value) + 1) * value
            next_dt = last_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_hour)
            if next_dt.date() > last_dt.date():
                next_dt = datetime.combine(last_dt.date() + timedelta(days=1), datetime.min.time())
            return next_dt

        elif unit == "d":
            return datetime.combine(last_dt.date() + timedelta(days=value), datetime.min.time())

        elif unit == "w":
            days_until_next_monday = (7 - last_dt.weekday()) % 7
            if days_until_next_monday == 0:
                days_until_next_monday = 7  # If already Monday, go to next Monday
            next_monday = last_dt.date() + timedelta(days=days_until_next_monday)
            return datetime.combine(next_monday, datetime.min.time())

        else:
            raise ValueError(f"Unsupported interval format: {interval}")

    def _is_new_candle_due(self):
        if not self.last_processed_candle_time:
            return True  # First run

        now_dt = datetime.fromtimestamp(time.time())
        next_candle_dt = CoinWatcher.get_next_candle_time(self.last_processed_candle_time, self.interval)
        return now_dt >= next_candle_dt

    def send_alert(self, signal: Signal):
        if self.notifier is None:
            return
        emoji = "🟢" if signal.type == "Long" else "🔴"
        message = (
            f"{emoji} *{signal.type}* | *{self.symbol}* | *{self.interval}*\n"
            f"*Entry:* `{signal.entry:.4f}`\n"
            f"*Stop Loss:* `{signal.sl:.4f}`"
        )
        self.notifier.send_message(message, parse_mode="Markdown")
