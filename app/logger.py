"""Logging module for the data warehouse ETL process."""

import logging
from pathlib import Path


def get_logger(level: str = logging.INFO) -> logging.Logger:
    """Initialize and configure a logger instance.

    The logger is named after the current script filename and uses the specified logging
    level.

    :param level: Logging level (default: logging.INFO)
    :type level: int or str
    :return: Configured logger instance
    :rtype: logging.Logger
    """
    log_format = "[%(levelname)s] - [%(filename)s] - [%(asctime)s] - %(message)s"

    logging.basicConfig(level=level, format=log_format)

    filename = Path(__import__("sys").argv[0]).name
    logger = logging.getLogger(filename)
    log_path = Path.cwd() / "dwh.log"

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format))

    logger.addHandler(file_handler)

    return logger
