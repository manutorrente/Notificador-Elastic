from notificationMethods.notificationMethod import NotificationMethod, NotificationMessage
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
    
    def send_notification(self, message: NotificationMessage, **config) -> None:
        """
        Sends a formatted embedded message to Discord using a webhook.
        
        Args:
            message: The structured NotificationMessage dataclass to send
            **config: Optional configuration from the document
                - status: "up" to indicate service is back up (resolved)
                - downtime: Pre-calculated downtime string (if available)
                - title: Custom title for the alert
        """
        try:
            # Get current timestamp for the notification processing time
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if this is a resolved/up status
            status = config.get("status", "").lower()
            is_resolved = status == "up"
            
            # Set appearance based on status
            if is_resolved:
                emoji = "✅"
                default_text = "Elastic Alert Resolved"
                color = 0x2ECC71  # Green color for resolved
                status_field_name = "✅ Alert Status"
                status_field_value = "Resolved"
            else:
                emoji = "🔔"
                default_text = "Elastic Alert Notification"
                color = 0xFF5733  # Orange-red color for alerts
                status_field_name = "⚠️ Alert Status"
                status_field_value = "Active"
            
            # Handle custom title and subtitle logic, keeping the emoji on the title
            custom_title = config.get("title")
            if custom_title:
                embed_title = f"{emoji} {custom_title}"
                embed_subtitle = default_text
            else:
                embed_title = f"{emoji} {default_text}"
                embed_subtitle = None
                
            # Build the main body text using the separated dataclass fields
            body_text = f"**Time:** {message.timestamp}\n\n{message.message}"
            
            # Discord lacks a native 'subtitle', so if a subtitle exists, bold it at the top of the description
            if embed_subtitle:
                embed_description = f"**{embed_subtitle}**\n\n{body_text}"
            else:
                embed_description = body_text
            
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
            
            # Combine the ID, timestamp, and index into the native footer
            footer_text = f"Notification ID: {self.id} • {current_timestamp}\nAlert from index: {message.index}"
            
            # Prepare the embed with proper formatting
            embed = {
                "title": embed_title,
                "description": embed_description,
                "color": color,
                "footer": {
                    "text": footer_text
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