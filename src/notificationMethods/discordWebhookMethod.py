from notificationMethods.notificationMethod import NotificationMethod
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordWebhookMessage(NotificationMethod):
    """
    Discord notification method using webhooks.
    This is simpler than the bot token method and doesn't require a persistent connection.
    
    To create a Discord webhook:
    1. Go to Server Settings -> Integrations -> Webhooks
    2. Click "New Webhook"
    3. Configure the webhook (name, channel, avatar)
    4. Copy the webhook URL
    """
    
    def __init__(self, id: str, webhook_url: str):
        super().__init__(id)
        self.webhook_url = webhook_url
    
    def send_notification(self, message: str) -> None:
        """
        Sends a formatted embedded message to Discord using a webhook.
        
        Args:
            message: The message content to send
        """
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Prepare the embed with proper formatting
            embed = {
                "title": "🔔 Elastic Alert Notification",
                "description": message,
                "color": 0xFF5733,  # Orange-red color for alerts
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": f"Notification ID: {self.id} • {timestamp}"
                },
                "fields": [
                    {
                        "name": "⚠️ Alert Status",
                        "value": "Active",
                        "inline": True
                    },
                    {
                        "name": "📊 Source",
                        "value": "Elasticsearch",
                        "inline": True
                    }
                ]
            }
            
            # Prepare the payload with the embed
            payload = {
                "embeds": [embed]
            }
            
            # Send the POST request to the webhook URL
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            # Check if the request was successful
            if response.status_code == 204:
                logger.info(f"Discord webhook message sent successfully (ID: {self.id})")
            else:
                logger.error(
                    f"Failed to send Discord webhook message (ID: {self.id}). "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while sending Discord webhook message (ID: {self.id})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord webhook message (ID: {self.id}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending Discord webhook message (ID: {self.id}): {e}")
    
