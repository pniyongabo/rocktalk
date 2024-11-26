import logging

logger = logging.getLogger("rocktalk")
log_level = logging.DEBUG
logger.setLevel(log_level)
handler = logging.StreamHandler()

info_format_string = "\n%(asctime)s - %(name)s - %(levelname)s - %(message)s"
debug_format_string = (
    "\n%(asctime)s - %(name)s/%(filename)s:%(lineno)d - %(levelname)s - %(message)s"
)

if log_level == logging.DEBUG:
    format_string = debug_format_string
else:
    format_string = info_format_string
handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(handler)
