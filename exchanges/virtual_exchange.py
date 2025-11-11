from exchanges.exchange_interface import IExchange
from structs.position import Position
from structs.utils import get_utc_now_timestamp
from notifiers.notifier_interface import INotifier
from persistence.persistence_interface import IPersistence

class VirtualExchange(IExchange):
    def __init__(self, notifier: INotifier, positions_history_logger: IPersistence, current_positions_logger: IPersistence=None):
        self.notifier: INotifier = notifier
        self.positions_history_logger: IPersistence = positions_history_logger
        self.current_positions_logger: IPersistence = current_positions_logger
        self.open_positions: list[Position] = []
        self.closed_positions: list[Position] = []
        self.n_active_positions = 0
        self.tp_hits = 0
        self.sl_hits = 0
        self.breakeven_hits = 0
        self.profits_sum = 0

    def open_position(self, pos: Position):
        if pos is not None:
            self.n_active_positions += 1
            pos.open_timestamp = get_utc_now_timestamp()
            pos.status = "opened"
            self.open_positions.append(pos)
            self._notify_open(pos)

    def tick(self):
        still_open = []

        for pos in self.open_positions:
            try:
                price = pos.chart.get_current_price()
                pos.current_price = price
                if (pos.type == "Long" and price <= pos.sl) or (pos.type == "Short" and price >= pos.sl):
                    # STOP LOSS HIT
                    # Should decide based on strategy
                    # Should update profit
                    pos.exit_price = price
                    pos.exit_reason = "SL Hit"
                    pos.profit = -1
                    self._close_position(pos)
                elif (pos.type == "Long" and price >= pos.tp) or (pos.type == "Short" and price <= pos.tp):
                    # TAKE PROFIT HIT
                    # Should decide based on strategy
                    # Should update profit
                    pos.exit_price = price
                    pos.exit_reason = "TP Hit"
                    pos.profit = 1
                    self._close_position(pos)
                else:
                    still_open.append(pos)

            except Exception as e:
                print(f"[VirtualExchange] Error checking {pos.chart.symbol}:{pos.chart.timeframe.value}: {e}")
                still_open.append(pos)

        self.open_positions = still_open

        if self.current_positions_logger:
            try:
                self.current_positions_logger.write([op.to_active_position_row() for op in self.open_positions])
            except Exception as e:
                print(f"[VirtualExchange] Failed to log current positions table: {e}")

    def _close_position(self, pos: Position):
        if pos is not None:
            self.n_active_positions -= 1
            pos.close_timestamp = get_utc_now_timestamp()
            pos.status = "closed"
            self.closed_positions.append(pos)

            if pos.profit > 0:
                self.tp_hits += pos.profit
            elif pos.profit < 0:
                self.sl_hits += 1
            else:
                self.breakeven_hits += 1

            self.profits_sum += pos.profit

            if self.positions_history_logger:
                try:
                    self.positions_history_logger.write(pos.to_history_row())
                except Exception as e:
                    print(f"[VirtualExchange] Failed to log position: {e}")

            self._notify_close(pos)

    def _notify_open(self, pos: Position):
        if self.notifier is None:
            return
        
        nclosed = len(self.closed_positions)
        nopen_ = self.n_active_positions
        message = (
            f"⏳ *Position Opened* #Position{pos.id}\n"
            f"Type: *{pos.type}*\n"
            f"Symbol: *{pos.chart.symbol}*\n"
            f"Timeframe: *{pos.chart.timeframe.value}*\n"
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
                self.notifier.send_message(message)
        except Exception as e:
            print(f"[VirtualExchange] Failed to send following message to telegram: {e}")
            print(message)

    def _notify_close(self, pos: Position):
        if self.notifier is None:
            return
        
        nclosed = len(self.closed_positions)
        nopen_ = self.n_active_positions

        emoji = "✅" if pos.profit > 0 else "⛔" if pos.profit < 0 else "😐"
        message = (
            f"{emoji} *Position Closed* #Position{pos.id}\n"
            f"Type: *{pos.type}*\n"
            f"Symbol: *{pos.chart.symbol}*\n"
            f"Timeframe: *{pos.chart.timeframe.value}*\n"
            f"Profit: *{pos.profit}*\n"
            f"`{pos.entry:.4f}` → `{pos.exit_price:.4f}`\n"
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
            self.notifier.send_message(message)
        except Exception as e:
            print(f"[VirtualExchange] Failed to send following message to telegram: {e}")
            print(message)
