from abc import ABC, abstractmethod
from structs.position import Position

class ITradeAgent(ABC):
    @abstractmethod
    def analyze(self):
        pass
