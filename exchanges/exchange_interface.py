from abc import ABC, abstractmethod
from models import Position

class IExchange(ABC):
    @abstractmethod
    def open_position(self, pos: Position):
        pass
