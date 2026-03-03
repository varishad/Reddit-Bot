import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOG_FILE = os.path.join(LOGS_DIR, "app.log")


def setup_logger(name: str = "RedditBot") -> logging.Logger:
    """
    Return a named logger with rotating file + console handlers.
    Safe to call multiple times — handlers are only added once per logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if called multiple times with the same name
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Rotating file handler (5 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Root/global instance (used by modules that just do `from logger import logger`)
logger = setup_logger("RedditBot")
