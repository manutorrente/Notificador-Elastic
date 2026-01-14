import logging
import logging.config
import yaml
import os

# Path to logger_config.yaml (assumes it's in the same directory as this file)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'logger_config.yaml')

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger('src')
