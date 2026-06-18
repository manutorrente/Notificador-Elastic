from notificationMethods.notificationMethod import NotificationMethod, NotificationMessage
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
    
    def __init__(self, id: str, webhook_url: str, admit_status_up: bool = True):
        super().__init__(id)
        self.webhook_url = webhook_url
        self.admit_status_up = admit_status_up

    def send_notification(self, message: NotificationMessage, **config) -> None:
        """
        Sends a formatted Card message to Google Chat using a webhook.
        
        Args:
            message: The structured NotificationMessage dataclass to send
            **config: Optional configuration from the document
                - status: "up" to indicate service is back up (resolved)
                - downtime: Pre-calculated downtime string (if available)
                - title: Custom title for the alert
        """
        try:
            
            if not self.admit_status_up and config.get("status", "").lower() == "up":
                logger.info(f"Skipping 'up' status notification for Google Chat (ID: {self.id})")
                return
            
            # Get current timestamp for the notification processing time
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if this is a resolved/up status
            status = config.get("status", "").lower()
            is_resolved = status == "up"
            
            # Set appearance and color based on status
            if is_resolved:
                emoji = "✅"
                default_text = "Elastic Alert Resolved"
                status_text = "Resolved"
                color_hex = "#34A853"  # Google Green
            else:
                emoji = "🔔"
                default_text = "Elastic Alert Notification"
                status_text = "Active"
                color_hex = "#EA4335"  # Google Red
            
            # Handle custom title and subtitle logic, keeping the emoji on the title
            custom_title = config.get("title")
            if custom_title:
                card_title = f"{emoji} {custom_title}"
                card_subtitle = default_text
            else:
                card_title = f"{emoji} {default_text}"
                card_subtitle = None
            
            # Build Header (applying the color here since Google Chat lacks a global card color)
            header = {
                "title": f"<font color=\"{color_hex}\"><b>{card_title}</b></font>"
            }
            if card_subtitle:
                header["subtitle"] = card_subtitle

            # Build the main body text using the separated dataclass fields
            main_message = f"<b>Time:</b> {message.timestamp}<br>{message.message}"

            # Build the widgets list for the primary section
            main_widgets = [
                {
                    "textParagraph": {
                        "text": main_message
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
                    main_widgets.append({
                        "decoratedText": {
                            "topLabel": "Downtime",
                            "text": downtime,
                            "startIcon": {
                                "knownIcon": "CLOCK"
                            }
                        }
                    })

            # Create a simulated footer section with gray text
            footer_text = (
                f"<font color=\"#808080\">"
                f"Notification ID: {self.id} • {current_timestamp}<br>"
                f"Alert from index: {message.index}"
                f"</font>"
            )
            
            footer_widgets = [
                {
                    "textParagraph": {
                        "text": footer_text
                    }
                }
            ]
            
            # Prepare the payload with sections
            payload = {
                "text": "<users/all>",  # This triggers the @all ping
                "cardsV2": [
                    {
                        "cardId": f"alert-{self.id}",
                        "card": {
                            "header": header,
                            "sections": [
                                {
                                    "widgets": main_widgets
                                },
                                {
                                    "widgets": footer_widgets
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