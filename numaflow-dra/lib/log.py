import logging
import logging.config
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv


def setup_logger(logger_name) -> logging.Logger:
    # Load log config from yaml
    log_config_path = Path(__file__).parent / 'logging_config.yaml'
    with open(log_config_path) as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)

    return logging.getLogger(logger_name)


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


# set logger log-level to env LOG_LEVEL
def set_logger_log_level(logger: logging.Logger) -> None:
    load_dotenv(str(Path(__file__).parent / '../app.env'))
    log_level = os.getenv('LOGGER_LOG_LEVEL', 'NONE').upper()

    valid_log_level_list = os.getenv('VALID_LOG_LEVEL_LIST').split(',')
    if log_level in valid_log_level_list:
        logger.setLevel(getattr(logging, log_level))
        logger.info(f'set LOG_LEVEL to {log_level}.')
    else:
        logger.error(f'Invalid LOG_LEVEL: {log_level}. Must be one of {valid_log_level_list}.')
        sys.exit(1)
