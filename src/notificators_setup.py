from notificator import Notificator
from notificationMethods.emailMethod import SMTPEmailMethod, smtp_conn
from notificationMethods.discordMethod import DiscordChannelMessage
from notificationMethods.discordWebhookMethod import DiscordWebhookMessage
from conf import notification_methods as notif_methods_config, notificators as notificators_config
import os
import logging 

logger = logging.getLogger(__name__)

notification_method_instances = {}

notification_method_type_mapping = {
    "emailSMTP": SMTPEmailMethod,
    "discordWebhook": DiscordWebhookMessage,
    "discordBot": DiscordChannelMessage
    
}

for method_config in notif_methods_config:
    method_type = method_config["type"]
    try:
        method_type_class = notification_method_type_mapping.get(method_type)
    except KeyError as e:
        logger.error(f"Missing 'type' in notification method config: {method_config}")
        continue
    
    if method_type_class:
        notification_method_instances[method_config["id"]] = method_type_class(method_config["id"], **method_config["config"])

notificators = {}
for notificator_config in notificators_config:
    methods = []
    for method_name in notificator_config["notification_methods"]:
        if method_name in notification_method_instances:
            methods.append(notification_method_instances[method_name])
        else:
            logger.warning(f"Notification method '{method_name}' not found")

    notificators[notificator_config["id"]] = Notificator(
        id=notificator_config["id"],
        notification_methods=methods
    )


