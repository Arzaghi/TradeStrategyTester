from dataclasses import dataclass

@dataclass
class Signal:
    entry: float
    sl: float
    tp: float
    type: str