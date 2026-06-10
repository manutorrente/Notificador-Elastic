from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationMessage:
    timestamp: str
    message: str
    index: str

    def as_text(self) -> str:
        return (
            f"**Time:** {self.timestamp}\n"
            f"{self.message}\n\n"
            f"Alert from index: {self.index}"
        )


class NotificationMethod(ABC):
    
    def __init__(self, id: str):
        self.id = id
    @abstractmethod
    def send_notification(self, message: NotificationMessage, **config):
        pass
