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
    
    def send_notification(self, message: str, **config) -> None:
        """
        Sends a formatted embedded message to Discord using a webhook.
        
        Args:
            message: The message content to send
            **config: Optional configuration from the document
                - status: "up" to indicate service is back up (resolved)
                - downtime: Pre-calculated downtime string (if available)
        """
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if this is a resolved/up status
            status = config.get("status", "").lower()
            is_resolved = status == "up"
            
            # Set appearance based on status
            if is_resolved:
                title = "✅ Elastic Alert Resolved"
                color = 0x2ECC71  # Green color for resolved
                status_field_name = "✅ Alert Status"
                status_field_value = "Resolved"
            else:
                title = "🔔 Elastic Alert Notification"
                color = 0xFF5733  # Orange-red color for alerts
                status_field_name = "⚠️ Alert Status"
                status_field_value = "Active"
            
            # Build fields list
            fields = [
                {
                    "name": status_field_name,
                    "value": status_field_value,
                    "inline": True
                },
                {
                    "name": "📊 Source",
                    "value": "Elasticsearch",
                    "inline": True
                }
            ]
            
            # Add downtime field if available and status is resolved
            if is_resolved:
                downtime = config.get("downtime")
                if downtime:
                    fields.append({
                        "name": "⏱️ Downtime",
                        "value": downtime,
                        "inline": True
                    })
            
            # Prepare the embed with proper formatting
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "footer": {
                    "text": f"Notification ID: {self.id} • {timestamp}"
                },
                "fields": fields
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
    
