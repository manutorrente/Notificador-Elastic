import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import logging
from .notificationMethod import NotificationMethod
import traceback
import os
from dotenv import load_dotenv

load_dotenv(override=True)


logger = logging.getLogger(__name__)

class SMTPConnection:
    def __init__(self, host, username, password, sender_email, receiver_emails: list[str] | None  = None, port=587, use_tls=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.receiver_emails = receiver_emails
        self.server = None
        self.retries = 0
        self.use_tls = use_tls # Added parameter to control TLS
        

    def initialize_server(self):
        try:
            self.server = smtplib.SMTP(self.host, self.port)
            
            # Conditionally start TLS based on the flag
            if self.use_tls:
                self.server.starttls()
                
            # Only attempt login if credentials actually exist
            if self.username and self.password:
                self.server.login(self.username, self.password)
                
        except Exception as e:
            logger.error(f"Failed to initialize SMTP server: {e}")
            logger.error(traceback.format_exc())
            self.server = None
    
    def disconnect(self):
        if self.server is not None:
            try:
                self.server.quit()
            except Exception as e:
                logger.error(f"Error disconnecting SMTP server: {e}")
        else:
            logger.warning("disconnect() called but server is None")
        

    def send_email(self, subject, body, recipient_emails = None, html_type=False, quit_after_send=True):
        try:
            if self.server is None:
                self.initialize_server()
            if self.server is None:
                raise Exception("SMTP server is not initialized. Check host and credentials.")
            if recipient_emails is None:
                recipient_emails = self.receiver_emails
            if not recipient_emails or not isinstance(recipient_emails, list):
                raise ValueError("recipient_emails must be a non-empty list of strings")

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join([str(email) for email in recipient_emails])
            msg['Subject'] = subject
            if html_type:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            self.server.sendmail(self.sender_email, recipient_emails, msg.as_string())
            self.retries = 0
        except Exception as e:
            logger.error("Error sending email")
            logger.error(traceback.format_exc())
            if self.retries == 0:
                self.retries += 1
                self.initialize_server()
                if self.server is not None:
                    self.send_email(subject, body, recipient_emails, html_type)
                else:
                    logger.error("Retry failed: SMTP server is still not initialized.")
        finally:
            if quit_after_send:
                self.disconnect()

                
smtp_conn = SMTPConnection(
    host="SRVEXGPSA01P.petersen.corp",
    username=os.getenv("SMTP_USERNAME"),
    password=os.getenv("SMTP_PASSWORD"),
    sender_email="operativagobdato@gbsj.com.ar",
    use_tls=False # Explicitly setting it to False here, though it is now the default
)

class SMTPEmailMethod(NotificationMethod):
    """
    SMTP Email notification method implementation
    """
    
    def __init__(
        self,
        id: str,
        to_emails: List[str],
        subject_prefix: str = "[Notification]",
        smtp_connection: SMTPConnection = smtp_conn,
        ignore_status_up: bool = True,
    ):
        """
        Initialize SMTP email notification method
        
        Args:
            id: Notification method ID
            to_emails: List of recipient email addresses
            subject_prefix: Prefix for email subject line
            smtp_connection: SMTP connection object
            ignore_status_up: If True, ignore alerts with status='up' (default: True)
        """
        super().__init__(id)
        self.smtp_connection = smtp_connection
        self.to_emails = to_emails
        self.subject_prefix = subject_prefix
        self.ignore_status_up = ignore_status_up

    def _parse_message(self, message: str) -> tuple[str, str, str]:
        """
        Parse the formatted message to extract index, timestamp, and alert message.
        Expected format: "**Alert from index: {index}**\n**Time:** {timestamp}\n\n{message}"
        
        Returns:
            Tuple of (index, timestamp, alert_message)
        """
        lines = message.split("\n")
        index = "Unknown"
        timestamp = "Unknown"
        alert_message = message
        
        # Try to extract index from first line
        if len(lines) > 0 and "Alert from index:" in lines[0]:
            try:
                index = lines[0].replace("**Alert from index: ", "").replace("**", "").strip()
            except:
                pass
        
        # Try to extract timestamp from second line
        if len(lines) > 1 and "Time:" in lines[1]:
            try:
                timestamp = lines[1].replace("**Time:** ", "").replace("**", "").strip()
            except:
                pass
        
        # Extract the actual alert message (everything after the header lines)
        if len(lines) > 2:
            alert_message = "\n".join(lines[2:]).strip()
        
        return index, timestamp, alert_message
    
    def _build_html_email(self, index: str, timestamp: str, alert_message: str, **config) -> str:
        """
        Build a formatted HTML email body.
        
        Args:
            index: The Elasticsearch index name
            timestamp: Alert timestamp
            alert_message: The main alert message
            **config: Additional configuration (status, downtime, etc.)
        
        Returns:
            HTML string for the email body
        """
        status = config.get("status", "").lower()
        downtime = config.get("downtime", "")
        
        # Determine status display
        if status == "up":
            status_label = "Resolved"
            status_color = "#2ECC71"  # Green
            status_icon = "✓"
        else:
            status_label = "Active"
            status_color = "#FF5733"  # Orange-red
            status_icon = "!"
        
        html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px 8px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                    .content {{ background: #f9f9f9; padding: 25px; border-radius: 0 0 8px 8px; }}
                    .info-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #e0e0e0; }}
                    .info-block {{ }}
                    .info-label {{ font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
                    .info-value {{ font-size: 14px; color: #333; margin-top: 5px; font-family: 'Monaco', 'Courier New', monospace; }}
                    .status-badge {{ display: inline-block; background: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
                    .message-section {{ background: white; padding: 20px; border-radius: 6px; border-left: 4px solid #667eea; margin-top: 20px; }}
                    .message-section h3 {{ margin-top: 0; color: #333; }}
                    .message-text {{ background: #f5f5f5; padding: 15px; border-radius: 4px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }}
                    .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{status_icon} Elasticsearch Alert Notification</h1>
                    </div>
                    <div class="content">
                        <div class="info-row">
                            <div class="info-block">
                                <div class="info-label">Alert Status</div>
                                <div><span class="status-badge">{status_label}</span></div>
                            </div>
                            <div class="info-block">
                                <div class="info-label">Source Index</div>
                                <div class="info-value">{index}</div>
                            </div>
                        </div>
                        
                        <div class="info-row">
                            <div class="info-block">
                                <div class="info-label">Timestamp</div>
                                <div class="info-value">{timestamp}</div>
                            </div>
                            {f'<div class="info-block"><div class="info-label">Downtime</div><div class="info-value">{downtime}</div></div>' if downtime else ''}
                        </div>
                        
                        <div class="message-section">
                            <h3>Alert Message</h3>
                            <div class="message-text">{alert_message}</div>
                        </div>
                    </div>
                    <div class="footer">
                        <p>This is an automated alert from the Elasticsearch Alert Notificator Service</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return html

    def send_notification(self, message: str, **config) -> None:
        """
        Send email notification via SMTP
        
        Args:
            message: The formatted notification message to send
            **config: Additional configuration including alert status, downtime, etc.
        """
        # Check if we should ignore this alert based on status
        if self.ignore_status_up and config.get("status", "").lower() == "up":
            logger.info(f"Ignoring email notification: alert status is 'up' and ignore_status_up is enabled")
            return
        
        try:
            # Parse the message to extract components
            index, timestamp, alert_message = self._parse_message(message)
            
            # Build HTML email body
            html_body = self._build_html_email(index, timestamp, alert_message, **config)
            
            # Create subject - use first line of alert message or config subject
            config_subject = config.get("subject")
            subject_text = config_subject if config_subject else alert_message.split("\n")[0][:50]
            if not config_subject and len(alert_message.split("\n")[0]) > 50:
                subject_text += "..."
            subject = f"{self.subject_prefix} {subject_text.replace(chr(10), ' ')}"

            self.smtp_connection.send_email(
                subject=subject,
                body=html_body,
                recipient_emails=self.to_emails,
                html_type=True,
                quit_after_send=True
            )
            
            logger.info(f"Email notification sent successfully to {len(self.to_emails)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise Exception(f"Failed to send email: {e}")
