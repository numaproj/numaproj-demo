import logging
import os
import sys
from datetime import datetime


def stdout_filter(record: logging.LogRecord):
    # Output logs milder than ERROR (WARNING, INFO, ...) to stdout
    return record.levelno < logging.ERROR


class ISO8601Formatter(logging.Formatter):
    def __init__(self, fmt):
        super().__init__(fmt)
        self._tzinfo = datetime.today().astimezone().tzinfo

    def formatTime(self, record: logging.LogRecord, _datafmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self._tzinfo)
        return dt.astimezone().isoformat(timespec='seconds')


def setup_logging(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    level = os.getenv('LOGGER_LOG_LEVEL', 'NOTSET').upper()
    formatter = ISO8601Formatter('%(asctime)s %(levelname)-8s %(message)s')

    logger.setLevel(level)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(stdout_filter)
    stdout_handler.setLevel(level)
    logger.addHandler(stdout_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.ERROR)
    logger.addHandler(stderr_handler)

    return logger
