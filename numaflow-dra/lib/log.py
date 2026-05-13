import logging
import logging.config
import os
import sys


def remove_filehandler_in_logger(logger: logging.Logger) -> logging.Logger:
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
            handler.close()

    return logger


def add_new_filehandler(logger: logging.Logger, filename: str) -> None:
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def change_handler_filename(logger: logging.Logger, filename: str) -> None:
    remove_filehandler_in_logger(logger)

    add_new_filehandler(logger, filename)


# set logger log-level to env LOGGER_LOG_LEVEL
def set_logger_log_level(logger: logging.Logger) -> None:
    # See https://docs.python.org/ja/3.12/library/logging.html#logging-levels
    log_level = os.getenv('LOGGER_LOG_LEVEL', 'NOTSET').upper()

    try:
        logger.setLevel(getattr(logging, log_level))
        logger.info(f'set LOGGER_LOG_LEVEL to {log_level}.')
    except AttributeError:
        logger.error(
            f'Invalid LOGGER_LOG_LEVEL: {log_level}. '
            f'Must be one of NOTSET, DEBUG, INFO, WARNING, ERROR, or CRITICAL.'
        )
        sys.exit(1)
