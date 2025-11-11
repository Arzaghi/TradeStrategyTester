from charts.chart_interface import IChart
from models import Signal
from abc import ABC, abstractmethod
from typing import Optional

class IStrategy(ABC):
    STRATEGY_NAME: str

    @abstractmethod
    def generate_signal(self, chart: IChart) -> Optional[Signal]:
        raise NotImplementedError("Subclasses must implement this method")