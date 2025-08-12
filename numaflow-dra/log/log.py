import os
import logging
import logging.config
import yaml
import sys

from dotenv import load_dotenv
from pathlib import Path

load_dotenv("../system-config.env")

def setup_logger(logger_name) -> logging.Logger:
    # Load log config from yaml
    log_config_path = Path(__file__).parent / "logging_config.yaml"
    with open(log_config_path, 'r') as f:
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

    return
    


def change_handler_filename(logger: logging.Logger, filename: str) -> None:

    remove_filehandler_in_logger(logger)

    add_new_filehandler(logger, filename)

    return


# set logger log-level to env LOG_LEVEL
def set_logger_log_level(logger: logging.Logger) -> None:
    log_level = os.getenv("LOGGER_LOG_LEVEL", "NONE").upper()

    VALID_LOG_LEVEL_LIST = os.getenv("VALID_LOG_LEVEL_LIST").split(",")
    if log_level in VALID_LOG_LEVEL_LIST:
        logger.setLevel(getattr(logging, log_level))
        logger.info(f"set LOG_LEVEL to {log_level}.")
    else:
        logger.error(f"Invalid LOG_LEVEL: {log_level}. Must be one of {VALID_LOG_LEVEL_LIST}.")
        sys.exit(1)

    return

