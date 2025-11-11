from typing import Any, List
from abc import ABC, abstractmethod

class IPersistence(ABC):
    @abstractmethod
    def write(self, obj: Any | List[Any]):
        pass
