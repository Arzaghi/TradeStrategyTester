import time

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

    def open_position(self, position):
        if position is not None:
            self.position_counter += 1
            position.id = self.position_counter  # Assign unique ID
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
                        self._close_position(pos, price, "TP Hit")
                    else:
                        still_open.append(pos)

                elif pos.type == "Short":
                    if price >= pos.sl:
                        self._close_position(pos, price, "SL Hit")
                    elif price <= pos.tp:
                        self._close_position(pos, price, "TP Hit")
                    else:
                        still_open.append(pos)

            except Exception as e:
                print(f"[VirtualExchange] Error checking {pos.symbol}: {e}")
                still_open.append(pos)

        self.open_positions = still_open

    def _close_position(self, pos, exit_price, reason):
        pos.exit_price = exit_price
        pos.exit_reason = reason
        pos.status = "closed"
        pos.close_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        pos.duration = int(time.time() - pos.start_timestamp)
        pos.rr_ratio = round(abs((pos.tp - pos.entry) / (pos.entry - pos.sl)), 2) if pos.entry != pos.sl else 0.0

        self.closed_positions.append(pos)

        if reason == "TP Hit":
            self.tp_hits += 1
        elif reason == "SL Hit":
            self.sl_hits += 1

        if self.logger:
            try:
                self.logger.write(pos)
            except Exception as e:
                print(f"[VirtualExchange] Failed to log position: {e}")

        self._notify_close(pos)

    def _notify_open(self, pos):
        nclosed = len(self.closed_positions)
        nopen_ = len(self.open_positions)
        winrate = round((self.tp_hits / nclosed) * 100, 1) if nclosed > 0 else 0.0
        emoji = "🕒"
        message = (
            f"{emoji} *Opened #{pos.id}* | *{pos.symbol} {pos.type}* | *{pos.interval}*\n"
            f"*Entry:* `{pos.entry:.4f}` | *SL:* `{pos.sl:.4f}` | *TP:* `{pos.tp:.4f}`\n\n"
            f"📊 *Closed:* {nclosed} | *Open:* {nopen_} | *TP:* {self.tp_hits} | *SL:* {self.sl_hits} | *Winrate:* {winrate:.1f}%"
        )
        try:
            if self.notifier:
                self.notifier.send_message(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[VirtualExchange] Failed to send open notification: {e}")

    def _notify_close(self, pos):
        if self.notifier is None:
            return
        emoji = "✅" if pos.exit_reason == "TP Hit" else "🛑"
        nclosed = len(self.closed_positions)
        nopen_ = len(self.open_positions)-1
        winrate = round((self.tp_hits / nclosed) * 100, 1) if nclosed > 0 else 0.0

        message = (
            f"{emoji} *Closed #{pos.id}* | *{pos.exit_reason}*\n"
            f"*{pos.symbol} {pos.interval}* | `{pos.entry:.4f}` → `{pos.exit_price:.4f}`\n"
            f"*RR:* `{pos.rr_ratio}` | *Dur:* `{pos.duration}s`\n\n"
            f"📊 *Closed:* {nclosed} | *Open:* {nopen_} | *TP:* {self.tp_hits} | *SL:* {self.sl_hits} | *Winrate:* {winrate:.1f}%"
        )
        try:
            if self.notifier:
                self.notifier.send_message(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[VirtualExchange] Failed to send close notification: {e}")
