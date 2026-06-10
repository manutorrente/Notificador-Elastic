from notificationMethods.notificationMethod import NotificationMethod
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleChatWebhookMessage(NotificationMethod):
    """
    Google Chat notification method using webhooks.
    
    To create a Google Chat webhook:
    1. Navigate to the Google Chat space you want to send alerts to.
    2. Click the Space name dropdown at the top -> "Apps & integrations".
    3. Click "Manage webhooks" (you may need to add it if empty).
    4. Provide a name and optional avatar URL, then click "Save".
    5. Copy the generated webhook URL.
    """
    
    def __init__(self, id: str, webhook_url: str):
        super().__init__(id)
        self.webhook_url = webhook_url
    
    def send_notification(self, message: str, **config) -> None:
        """
        Sends a formatted Card message to Google Chat using a webhook.
        
        Args:
            message: The message content to send
            **config: Optional configuration from the document
                - status: "up" to indicate service is back up (resolved)
                - downtime: Pre-calculated downtime string (if available)
                - title: Custom title for the alert
        """
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if this is a resolved/up status
            status = config.get("status", "").lower()
            is_resolved = status == "up"
            
            # Set appearance based on status
            if is_resolved:
                default_title = "✅ Elastic Alert Resolved"
                status_text = "Resolved"
            else:
                default_title = "🔔 Elastic Alert Notification"
                status_text = "Active"
            
            # Handle custom title and subtitle fallback
            custom_title = config.get("title")
            if custom_title:
                card_title = custom_title
                # Google Chat textParagraph supports basic HTML tags like <b> and <br>
                card_message = f"<b>{default_title}</b><br><br>{message}"
            else:
                card_title = default_title
                card_message = message
            
            # Build the widgets list
            widgets = [
                {
                    "textParagraph": {
                        "text": card_message
                    }
                },
                {
                    "decoratedText": {
                        "topLabel": "Alert Status",
                        "text": f"<b>{status_text}</b>",
                        "startIcon": {
                            "knownIcon": "TICKET"
                        }
                    }
                },
                {
                    "decoratedText": {
                        "topLabel": "Source",
                        "text": "Elasticsearch",
                        "startIcon": {
                            "knownIcon": "DESCRIPTION"
                        }
                    }
                }
            ]
            
            # Add downtime field if available and status is resolved
            if is_resolved:
                downtime = config.get("downtime")
                if downtime:
                    widgets.append({
                        "decoratedText": {
                            "topLabel": "Downtime",
                            "text": downtime,
                            "startIcon": {
                                "knownIcon": "CLOCK"
                            }
                        }
                    })
            
            # Prepare the payload with the root text for the ping, and the cardsV2 for the rich embed
            payload = {
                "text": "<users/all>",  # This triggers the @all ping
                "cardsV2": [
                    {
                        "cardId": f"alert-{self.id}",
                        "card": {
                            "header": {
                                "title": card_title,
                                "subtitle": f"Notification ID: {self.id} • {timestamp}"
                            },
                            "sections": [
                                {
                                    "widgets": widgets
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Send the POST request to the webhook URL
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            # Google Chat returns 200 OK on success
            if response.status_code == 200:
                logger.info(f"Google Chat webhook message sent successfully (ID: {self.id})")
            else:
                logger.error(
                    f"Failed to send Google Chat webhook message (ID: {self.id}). "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while sending Google Chat webhook message (ID: {self.id})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Google Chat webhook message (ID: {self.id}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending Google Chat webhook message (ID: {self.id}): {e}")