import logging
from logging.handlers import MemoryHandler, RotatingFileHandler
import os
from pathlib import Path
from typing import Optional

ROCKTALK_DIR = os.getenv("ROCKTALK_DIR", str(Path.home() / ".rocktalk"))

# allow for custom log level via environment variable
USER_LOG_LEVEL = os.getenv("ROCKTALK_LOG_LEVEL", "INFO").upper()

# Always set base logger level to DEBUG to capture everything
BASE_LOG_LEVEL = logging.DEBUG


def setup_logger(log_level: str = USER_LOG_LEVEL) -> logging.Logger:
    # Configure logging
    logger = logging.getLogger("rocktalk")
    logger.setLevel(BASE_LOG_LEVEL)

    # Check if handlers are already configured
    if not logger.handlers:
        info_format_string = "\n%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        debug_format_string = "\n%(asctime)s - %(name)s/%(filename)s:%(lineno)d - %(levelname)s - %(message)s"

        format_string = (
            debug_format_string if log_level == "DEBUG" else info_format_string
        )
        formatter = logging.Formatter(format_string)

        # Create rotating file handler
        LOG_DIR = os.path.join(ROCKTALK_DIR, "logs")
        os.makedirs(LOG_DIR, exist_ok=True)

        # Default log file path
        LOG_FILE = os.path.join(LOG_DIR, "rocktalk.log")

        # Maximum log file size (200 MB by default), configurable via environment variable
        MAX_LOG_SIZE = int(
            os.getenv("ROCKTALK_MAX_LOG_SIZE", 10 * 1024 * 1024)
        )  # 200 MB in bytes

        # Number of backup log files to keep, configurable via environment variable
        BACKUP_COUNT = int(os.getenv("ROCKTALK_LOG_BACKUP_COUNT", 10))

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

        # Optionally, add console handler for stdout
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

        # Add memory handler
        memory_handler = MemoryHandler(capacity=1000, flushLevel=logging.ERROR)
        memory_handler.setFormatter(formatter)
        memory_handler.setLevel(BASE_LOG_LEVEL)
        logger.addHandler(memory_handler)

        logger.info(f"Logger initialized with handlers: {logger.handlers}")
    return logger


def get_log_memoryhandler() -> Optional[MemoryHandler]:
    """Get the memory handler for log viewing"""
    for handler in logger.handlers:
        if isinstance(handler, MemoryHandler):
            return handler
    return None


# Create the logger instance
logger = setup_logger()
