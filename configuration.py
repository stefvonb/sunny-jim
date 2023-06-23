import yaml
import logging
from logging.handlers import RotatingFileHandler


def load_config(file_path: str) -> dict:
    with open(file_path, 'r') as config_file:
        return yaml.safe_load(config_file)


def configure_logging(config: dict):
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    log_handler = RotatingFileHandler(
        config["application"]["logs"]["log_filename"],
        mode='a',
        maxBytes=config["application"]["logs"]["max_filesize"] * 1024 * 1024,
        backupCount=config["application"]["logs"]["num_backups"],
        encoding=None,
        delay=0
    )

    log_level = logging.DEBUG if config["application"]["debug"] else logging.INFO
    log_handler.setLevel(log_level)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[log_handler]
    )
