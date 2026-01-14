from abc import ABC, abstractmethod


class NotificationMethod(ABC):
    
    def __init__(self, id: str):
        self.id = id
    @abstractmethod
    def send_notification(self, message: str):
        pass
