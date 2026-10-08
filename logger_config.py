# Shared logger - writes to both the console and logs/pipeline_YYYY-MM-DD.log

import logging
import sys
from datetime import datetime

from config import LOGS_DIR

_LOG_FILE = LOGS_DIR / f"pipeline_{datetime.now():%Y-%m-%d}.log"

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger() is called
    # more than once for the same module (e.g. on re-import).
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(_FORMATTER)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_FORMATTER)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
