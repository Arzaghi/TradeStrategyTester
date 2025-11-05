import csv
import os

class CSVLogger:
    def __init__(self, filename, fieldnames):
        self.filename = filename
        self.fieldnames = fieldnames

        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

    def write(self, obj):
        write_header = not os.path.isfile(self.filename) or os.path.getsize(self.filename) == 0

        row = [getattr(obj, field, None) for field in self.fieldnames]

        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(self.fieldnames)
            writer.writerow(row)

class PositionsHistoryLogger(CSVLogger):
    def __init__(self, filename):
        fieldnames = ["type", "symbol", "interval", "entry", "initial_sl", "initial_tp", "exit_price", "open_time", "close_time", "duration", "profit"]
        super().__init__(filename=filename, fieldnames=fieldnames)

class CurrentPositionsLogger(CSVLogger):
    def __init__(self, filename):
        fieldnames = ["id", "type", "symbol", "interval", "open_time", "entry", "initial_sl", "current_sl", "next_tp", "current_profit", "current_price"]
        super().__init__(filename=filename, fieldnames=fieldnames)

    def write(self, positions):
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.writer(file) # overwrite the file
            writer.writerow(self.fieldnames)  # Write header
            for pos in positions:
                row = [getattr(pos, field, None) for field in self.fieldnames]
                writer.writerow(row)
