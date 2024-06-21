import logging
import time

CONSOLE_LEVEL = logging.INFO
FILE_LEVEL = logging.DEBUG


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(min(CONSOLE_LEVEL, FILE_LEVEL))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(CONSOLE_LEVEL)
    logger.addHandler(console_handler)
    file_handler = logging.FileHandler(f"logs/{time.time_ns()//1000}-{name}.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(FILE_LEVEL)
    logger.addHandler(file_handler)
    return logger
