import logging
from logging.handlers import MemoryHandler
from typing import Optional


def setup_logger():
    logger = logging.getLogger("rocktalk")

    # Check if handlers are already configured
    if not logger.handlers:
        log_level = logging.INFO
        logger.setLevel(log_level)
        handler = logging.StreamHandler()

        info_format_string = "\n%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        debug_format_string = "\n%(asctime)s - %(name)s/%(filename)s:%(lineno)d - %(levelname)s - %(message)s"

        if log_level == logging.DEBUG:
            format_string = debug_format_string
        else:
            format_string = info_format_string

        handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(handler)

        # Add memory handler
        memory_handler = MemoryHandler(capacity=1000, flushLevel=logging.ERROR)
        memory_handler.setLevel(logging.DEBUG)
        logger.addHandler(memory_handler)

    return logger


def get_log_memoryhandler() -> Optional[MemoryHandler]:
    """Get the memory handler for log viewing"""
    for handler in logger.handlers:
        if isinstance(handler, MemoryHandler):
            return handler
    return None


# Create the logger instance
logger = setup_logger()
