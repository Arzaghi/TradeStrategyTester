from abc import ABC, abstractmethod

class INotifier(ABC):

    @abstractmethod
    def send_message(self, text: str):
        raise NotImplementedError("Subclasses must implement this method")