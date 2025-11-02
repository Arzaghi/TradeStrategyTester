import csv
import os
from models import Position

class CSVLogger:
    def __init__(self, filename="logs.csv"):
        self.filename = filename

    def write(self, position: Position):
        file_exists = os.path.isfile(self.filename)
        fieldnames = list(Position.__annotations__.keys())

        # Prepare row with formatted floats
        row = []
        for field in fieldnames:
            value = getattr(position, field)
            if isinstance(value, float):
                row.append(f"{value:.2f}")
            else:
                row.append(value)

        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(fieldnames)
            writer.writerow(row)