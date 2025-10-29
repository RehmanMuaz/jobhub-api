from loguru import logger
import sys


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", backtrace=False, diagnose=False)