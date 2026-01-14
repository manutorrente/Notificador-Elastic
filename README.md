# Notification Service API

A FastAPI-based notification service that supports multiple notification methods including Email (SMTP) and Discord bot messaging. This service provides a REST API to send notifications through configured notification channels.

## Features

- **Multi-channel notifications**: Send notifications via Email and Discord
- **REST API**: Simple HTTP interface for triggering notifications
- **Configurable**: Easy setup for different notification methods and recipients
- **Logging**: Comprehensive logging for debugging and monitoring
- **Docker support**: Containerized deployment ready

## Supported Notification Methods

- **Email (SMTP)**: Send emails via SMTP server
- **Discord Bot**: Send messages to Discord channels via bot

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized deployment)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# SMTP Email Configuration
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

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t notification-service .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 --env-file .env notification-service
   ```

### Docker Compose (Recommended)

1. **Start the service**
   ```bash
   docker-compose up -d
   ```

## API Documentation

Once the service is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### Send Notification
```http
POST /notify
```

**Request Body:**
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
