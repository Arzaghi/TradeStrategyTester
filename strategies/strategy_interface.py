from charts.chart_interface import Candle
from models import Signal
from abc import ABC, abstractmethod
from typing import List, Optional

class IStrategy(ABC):
    STRATEGY_NAME: str
    REQUIRED_CANDLES: int

    @abstractmethod
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        raise NotImplementedError("Subclasses must implement this method")