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

    
    def send_notification(self, message: str, **config) -> None:
        """
        Send email notification via SMTP
        
        Args:
            message: The notification message to send
            **config: Additional configuration including alert status
        """
        # Check if we should ignore this alert based on status
        if self.ignore_status_up and config.get("status", "").lower() == "up":
            logger.info(f"Ignoring email notification: alert status is 'up' and ignore_status_up is enabled")
            return
        
        try:
            # Take subject from config object, else use truncated message content as subject.
            config_subject = config.get("subject")
            message_trunc = message[:50] + "..." if len(message) > 50 else message
            subject = config_subject if config_subject is not None else message_trunc
            subject = f"{self.subject_prefix} " + subject.replace("\n", " ")

            self.smtp_connection.send_email(
                subject=subject,
                body=message,
                recipient_emails=self.to_emails,
                html_type=False,
                quit_after_send=True
            )
            
            logger.info(f"Email notification sent successfully to {len(self.to_emails)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise Exception(f"Failed to send email: {e}")
