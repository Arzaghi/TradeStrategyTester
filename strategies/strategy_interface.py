from charts.chart_interface import IChart
from structs.position import Position
from abc import ABC, abstractmethod
from typing import Optional
from structs.signal import Signal

class IStrategy(ABC):
    STRATEGY_NAME: str

    @abstractmethod
    def generate_signal(self, chart: IChart) -> Optional[Signal]:
        raise NotImplementedError("Subclasses must implement this method")