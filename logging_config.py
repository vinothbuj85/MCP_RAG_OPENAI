import sys
from loguru import logger
from app.config import settings


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="{time} | {level} | {message}",
        serialize=False,
    )
    return logger


log = setup_logging()
