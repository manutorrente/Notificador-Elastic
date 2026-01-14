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
        "type": "discordBot",
        "config": {
            "channel_id": "1400908044388532330"
        }
    }
    
]

notificators = [
    {
        "id" : "email_only",
        "notification_methods": ["SMTPEmailMethodTest", "DiscordPetersenServer"]
    }
]