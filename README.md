# Elasticsearch Alert Notificator Service

A polling-based notification service that monitors Elasticsearch indexes for alert documents and sends notifications through configured channels (Email, Discord). Designed to run as a Linux systemd service.

## How It Works

1. **Kibana Alert Rules** create documents in Elasticsearch indexes when alerts trigger
2. **This service** polls those indexes for unprocessed alert documents
3. **Notifications** are sent through configured channels (Discord, Email)
4. **Documents** are marked as processed to prevent duplicate notifications

## Alert Document Format

Alert documents in Elasticsearch should have the following structure:

```json
{
    "processed": false,
    "timestamp": "2026-01-14T10:30:00Z",
    "message": "Alert message content here"
}
```

## Features

- **Multi-channel notifications**: Send notifications via Email (SMTP) and Discord (Webhook)
- **Polling-based**: No need for Elastic Enterprise license
- **Graceful shutdown**: Handles SIGTERM/SIGINT for clean service stops
- **Automatic reconnection**: Reconnects to Elasticsearch if connection is lost
- **Systemd ready**: Designed to run as a Linux service
- **Configurable polling interval**: Adjust how often to check for new alerts
- **Docker support**: Containerized deployment ready

## Supported Notification Methods

- **Email (SMTP)**: Send emails via SMTP server
- **Discord Webhook**: Send messages to Discord channels via webhook

## Quick Start

### Prerequisites

- Python 3.11+
- Elasticsearch 8.x
- Docker (optional, for containerized deployment)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Elasticsearch Configuration
ELASTICSEARCH_HOSTS=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_password
ELASTICSEARCH_VERIFY_CERTS=true
# ELASTICSEARCH_CA_CERTS=/path/to/ca.crt  # Optional, for HTTPS

# Polling Configuration
POLLING_INTERVAL=30  # seconds

# SMTP Email Configuration (if using email notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd NotificadorAlertasElastic
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   cd src
   python main.py
   ```

The service will start polling Elasticsearch for unprocessed alerts.

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t elastic-alert-notificator .
   ```

2. **Run the container**
   ```bash
   docker run --env-file .env elastic-alert-notificator
   ```

### Docker Compose (Recommended)

1. **Start the service**
   ```bash
   docker-compose up -d
   ```

## Systemd Service Installation

To run as a Linux service:

1. **Copy service file**
   ```bash
   sudo cp elastic-alert-notificator.service /etc/systemd/system/
   ```

2. **Edit the service file** to match your installation paths

3. **Create a service user** (optional but recommended)
   ```bash
   sudo useradd -r -s /bin/false notificator
   ```

4. **Enable and start the service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable elastic-alert-notificator
   sudo systemctl start elastic-alert-notificator
   ```

5. **Check status**
   ```bash
   sudo systemctl status elastic-alert-notificator
   ```

6. **View logs**
   ```bash
   sudo journalctl -u elastic-alert-notificator -f
   ```
```json
{
  "notificator_id": "email_only",
  "message": "Your notification message here"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Notification sent successfully",
  "notificator_id": "email_only"
}
```

## Configuration

### Notification Methods

Edit `src/conf.py` to configure notification methods:

```python
notification_methods = [
    {
        "id": "SMTPEmailMethodTest",
        "type": "emailSMTP",
        "config": {
            "to_emails": ["recipient@example.com"],
            "subject_prefix": "[Alert]"
        }
    },
    {
        "id": "DiscordChannel",
        "type": "discordBot",
        "config": {
            "channel_id": "your_discord_channel_id"
        }
    }
]
```

### Notificators

Configure notificators that can use multiple notification methods:

```python
notificators = [
    {
        "id": "email_only",
        "notification_methods": ["SMTPEmailMethodTest"]
    },
    {
        "id": "multi_channel",
        "notification_methods": ["SMTPEmailMethodTest", "DiscordChannel"]
    }
]
```

## Project Structure

```
NotificadorAlertasElastic/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── notificator.py            # Core notificator logic
│   ├── notificators_setup.py     # Setup and configuration loader
│   ├── conf.py                   # Configuration definitions
│   ├── logger.py                 # Logging configuration
│   ├── logger_config.yaml        # Logging YAML config
│   ├── test.py                   # Test utilities
│   └── notificationMethods/
│       ├── notificationMethod.py # Abstract base class
│       ├── emailMethod.py        # SMTP email implementation
│       └── discordMethod.py      # Discord bot implementation
├── requirements.txt              # Python dependencies
├── Dockerfile                   # Docker container definition
├── docker-compose.yml           # Docker Compose configuration
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## Development

### Adding New Notification Methods

1. Create a new class inheriting from `NotificationMethod` in the `notificationMethods/` directory
2. Implement the `send_notification` method
3. Add the new method to the type mapping in `notificators_setup.py`
4. Configure it in `conf.py`

Example:
```python
from notificationMethods.notificationMethod import NotificationMethod

class SlackMethod(NotificationMethod):
    def __init__(self, id: str, webhook_url: str):
        super().__init__(id)
        self.webhook_url = webhook_url
    
    def send_notification(self, message: str) -> None:
        # Implementation here
        pass
```

### Logging

The application uses structured logging configured via `logger_config.yaml`. Logs are output to both console and file (if configured).

### Testing

Run the test file to verify your configuration:
```bash
cd src
python test.py
```

## Discord Bot Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and copy the bot token
3. Add the bot to your Discord server with appropriate permissions
4. Get the channel ID where you want to send messages
5. Set the `DISCORD_BOT_TOKEN` environment variable

## SMTP Email Setup

For Gmail:
1. Enable 2-factor authentication
2. Generate an app password
3. Use the app password in the `SMTP_PASSWORD` environment variable

## Troubleshooting

### Common Issues

1. **Discord bot not responding**
   - Verify the bot token is correct
   - Ensure the bot has permissions in the target channel
   - Check that the channel ID is correct

2. **Email not sending**
   - Verify SMTP credentials
   - Check if your email provider requires app passwords
   - Ensure SMTP server and port are correct

3. **Docker container not starting**
   - Check that all environment variables are set
   - Verify the `.env` file is properly formatted
   - Check Docker logs: `docker logs <container_name>`

### Health Check

The API provides a simple health check endpoint:
```http
GET /
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions, please create an issue in the project repository.
