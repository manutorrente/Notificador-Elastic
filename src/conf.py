import os
from dotenv import load_dotenv

load_dotenv(override=True)

# =============================================================================
# Elasticsearch Configuration
# =============================================================================
elasticsearch_config = {
    "host": os.getenv("ELASTICSEARCH_HOST", "localhost"),
    "port": int(os.getenv("ELASTICSEARCH_PORT", "9200")),
    "username": os.getenv("ELASTICSEARCH_USERNAME", "elastic"),
    "password": os.getenv("ELASTICSEARCH_PASSWORD"),
    "verify_certs": os.getenv("ELASTICSEARCH_VERIFY_CERTS", "false").lower() == "true",
    "ca_certs": os.getenv("ELASTICSEARCH_CA_CERTS", None),
    "timeout": 60
}

# Polling interval in seconds
polling_interval = int(os.getenv("POLLING_INTERVAL", "15"))

# =============================================================================
# Notification Methods Configuration
# =============================================================================
notification_methods = [
    {
        "id": "SMTPEmailMethodTest",
        "type" : "emailSMTP",
        "config": {
            "to_emails": ["mtorrente@dblandit.com"],
            "subject_prefix": "[Test]"
        }
    },
    {
        "id" : "DiscordPetersenServer",
        "type": "discordWebhook",
        "config": {
            "webhook_url": "https://discord.com/api/webhooks/1365429107671961741/uRgS3hwUdHGI3LXg3cMD8PC6iAGoxUZ0xQ9ur8wR_u5JNipkDnQ24ymHwoxZFS1TELvQ"
        }
    },
    {
        "id" : "DiscordTestChannel",
        "type" : "discordWebhook",
        "config": {
            "webhook_url": "https://discord.com/api/webhooks/1400908128102645932/ZW-R6ZucvgCF7FngTPF5Xj7pXVvP63OZy7POInCDtYgjgs1Ooghw6yBg-tZ3OUYplaMD"
        }
    }
    
]

# =============================================================================
# Notificators Configuration
# =============================================================================
notificators = [
    {
        "id" : "email_only",
        "notification_methods": ["SMTPEmailMethodTest"]
    },
    {
        "id" : "email_and_discord",
        "notification_methods": ["SMTPEmailMethodTest", "DiscordPetersenServer"]
    },
    {
        "id" : "discord_only",
        "notification_methods": ["DiscordPetersenServer"]
    },
    {
        "id" : "discord_test_channel",
        "notification_methods": ["DiscordTestChannel"]
    }
]

# =============================================================================
# Indexes to Monitor
# Each index should have an associated notificator_id
# The script will poll these indexes for unprocessed alert documents
# =============================================================================
indexes_to_monitor = [
    {
        "index" : "alertas-impala",
        "notificator_id" : "discord_test_channel"
    },
    {
        "index" : "alertas-servicios-down",
        "notificator_id" : "discord_test_channel"
    }
]