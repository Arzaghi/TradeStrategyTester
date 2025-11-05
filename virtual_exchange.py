from datetime import timedelta
import time

class VirtualExchange:
    def __init__(self, api, notifier, logger=None):
        self.api = api
        self.notifier = notifier
        self.logger = logger
        self.open_positions = []
        self.closed_positions = []
        self.position_counter = 0
        self.tp_hits = 0
        self.sl_hits = 0
        self.breakeven_hits = 0
        self.profits_sum = 0

    def open_position(self, position):
        if position is not None:
            self.position_counter += 1
            position.id = self.position_counter
            position.profit = -1  # Initial profit
            position.risk = abs(position.entry - position.sl)  # Initial risk
            self.open_positions.append(position)
            self._notify_open(position)

    def tick(self):
        still_open = []

        for pos in self.open_positions:
            try:
                price = self.api.get_current_price(pos.symbol)

                if pos.type == "Long":
                    if price <= pos.sl:
                        self._close_position(pos, price, "SL Hit")
                    elif price >= pos.tp:
                        self._handle_tp_extension(pos)
                        still_open.append(pos)
                    else:
                        still_open.append(pos)

                elif pos.type == "Short":
                    if price >= pos.sl:
                        self._close_position(pos, price, "SL Hit")
                    elif price <= pos.tp:
                        self._handle_tp_extension(pos)
                        still_open.append(pos)
                    else:
                        still_open.append(pos)

            except Exception as e:
                print(f"[VirtualExchange] Error checking {pos.symbol}: {e}")
                still_open.append(pos)

        self.open_positions = still_open

    def _handle_tp_extension(self, pos):
        if pos.type == "Long":
            pos.sl += pos.risk
            pos.tp += pos.risk
        elif pos.type == "Short":
            pos.sl -= pos.risk
            pos.tp -= pos.risk
        pos.profit += 1

    def _close_position(self, pos, exit_price, reason):
        pos.exit_price = exit_price
        pos.exit_reason = reason
        pos.status = "closed"
        pos.close_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        pos.duration = str(timedelta(seconds=int(time.time() - pos.start_timestamp))).zfill(8)

        self.closed_positions.append(pos)

        if pos.profit > 0:
            self.tp_hits += pos.profit
        elif pos.profit < 0:
            self.sl_hits += 1
        else:
            self.breakeven_hits += 1
        self.profits_sum += pos.profit

        if self.logger:
            try:
                self.logger.write(pos)
            except Exception as e:
                print(f"[VirtualExchange] Failed to log position: {e}")

        self._notify_close(pos)

    def _notify_open(self, pos):
        if self.notifier is None:
            return
        nclosed = len(self.closed_positions)
        nopen_ = len(self.open_positions)
        message = (
            f"⏳ *Position Opened #{pos.id}*\n"
            f"Type: *{pos.type}*\n"
            f"Symbol: *{pos.symbol}*\n"
            f"Timeframe: *{pos.interval}*\n"
            f"Entry: `{pos.entry:.4f}`\n"
            f"Stop Loss: `{pos.sl:.4f}`\n"
            f"Take Profit: `{pos.tp:.4f}`\n\n\n"
            f"📊 *Stats*\n"
            f"Closed: `{nclosed}`\n"
            f"Open: `{nopen_}`\n"
            f"TP Hits: `{self.tp_hits}`\n"
            f"EN Hits: `{self.breakeven_hits}`\n"
            f"SL Hits: `{self.sl_hits}`\n"
            f"Total Profit: `{self.profits_sum}`\n"
        )
        try:
            if self.notifier:
                self.notifier.send_message(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[VirtualExchange] Failed to send open notification: {e}")

    def _notify_close(self, pos):
        if self.notifier is None:
            return
        nclosed = len(self.closed_positions)
        nopen_ = len(self.open_positions) - 1
        h, m, s = map(int, pos.duration.split(":"))
        f"Duration: `{h:02}:{m:02}:{s:02}`\n\n\n"

        emoji = "✅" if pos.profit > 0 else "⛔" if pos.profit < 0 else "😐"
        message = (
            f"{emoji} *Position Closed #{pos.id} — {pos.exit_reason}*\n"
            f"Type: *{pos.type}*\n"
            f"Symbol: *{pos.symbol}*\n"
            f"Timeframe: *{pos.interval}*\n"
            f"Entry → Exit: `{pos.entry:.4f}` → `{pos.exit_price:.4f}`\n"
            f"Profit: *{pos.profit}*\n"
            f"Duration: `{pos.duration}`\n\n\n"
            f"📊 *Stats*\n"
            f"Closed: `{nclosed}`\n"
            f"Open: `{nopen_}`\n"
            f"TP Hits: `{self.tp_hits}`\n"
            f"EN Hits: `{self.breakeven_hits}`\n"
            f"SL Hits: `{self.sl_hits}`\n"
            f"Total Profit: `{self.profits_sum}`\n"
        )
        try:
            if self.notifier:
                self.notifier.send_message(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[VirtualExchange] Failed to send close notification: {e}")
