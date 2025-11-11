import csv
import os
from typing import Any, List
from persistence.persistence_interface import IPersistence

class CSVPersistence(IPersistence):
    def __init__(self, filename: str, append_mode: bool = True):
        self.filename = filename
        self.append_mode = append_mode
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

    def write(self, obj: Any | List[Any]) -> None:
        items = obj if isinstance(obj, list) else [obj]
        if not items:
            return

        first = items[0]
        data = first.__dict__ if hasattr(first, "__dict__") else first
        fieldnames = list(data.keys())

        write_header = not os.path.isfile(self.filename) or os.path.getsize(self.filename) == 0
        mode = 'a' if self.append_mode else 'w'

        with open(self.filename, mode=mode, newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if write_header or not self.append_mode:
                writer.writeheader()
            for item in items:
                row = item.__dict__ if hasattr(item, "__dict__") else item
                writer.writerow(row)
