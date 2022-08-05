import yaml
import logging
from logging.handlers import RotatingFileHandler

# Open up a config file
with open("config.yaml", 'r') as config_file:
    config = yaml.safe_load(config_file)


def configure_logging():
    log_handler = logging.handlers.RotatingFileHandler(
        config["application"]["logs"]["log_filename"],
        mode='a',
        maxBytes=config["application"]["logs"]["max_filesize"] * 1024 * 1024,
        backupCount=config["application"]["logs"]["num_backups"],
        encoding=None,
        delay=0
    )
    log_handler.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[log_handler]
    )
