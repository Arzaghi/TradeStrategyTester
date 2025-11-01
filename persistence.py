import csv
import os
from models import Position

class CSVLogger:
    def __init__(self, filename="logs.csv"):
        self.filename = filename

    def write(self, position: Position):
        file_exists = os.path.isfile(self.filename)
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(Position.__annotations__.keys())
            writer.writerow([
                position.symbol,
                position.interval,
                position.candle_time,
                position.open_time,
                position.duration,
                position.type,
                f"{position.entry:.2f}",
                f"{position.sl:.2f}",
                f"{position.tp:.2f}",
                f"{position.exit_price:.2f}",
                position.exit_reason,
                f"{position.rr_ratio:.2f}"
            ])
