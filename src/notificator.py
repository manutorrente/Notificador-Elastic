from notificationMethods.notificationMethod import NotificationMethod
import logging

logger = logging.getLogger(__name__)

class Notificator:

    def __init__(self, id: str, notification_methods: list[NotificationMethod]) -> None:
        self.id = id
        self.notification_methods = notification_methods



    def notify(self, message: str) -> None:
        for method in self.notification_methods:
            try:
                method.send_notification(message)
                logger.info(f"Notification sent via {method.id} for notificator {self.id}")
            except Exception as e:
                logger.error(f"Error sending notification for {method.id} in notificator {self.id}: ")
                logger.exception(e)
                continue

# 