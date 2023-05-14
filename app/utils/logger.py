import logging
import sys
from enum import StrEnum

from loguru import logger as LOGGER


logging.basicConfig(level=logging.INFO)


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record: logging.LogRecord):
        try:
            level = LOGGER.level(record.levelname).name
        except (AttributeError, ValueError):
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            if frame.f_back:
                frame = frame.f_back
            depth += 1

        LOGGER.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomLogger:
    @classmethod
    def make_logger(cls, level: LogLevel) -> LOGGER:
        _logger = cls.customize_logging(level=level)
        return _logger

    @classmethod
    def customize_logging(cls, level: LogLevel) -> LOGGER:
        intercept_handler = InterceptHandler()
        format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> " "| <level>{message}</level>"
        LOGGER.remove()
        LOGGER.add(
            sink=sys.stdout,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=format,
        )

        lognames = [
            "asyncio",
            "aiogram.dispatcher",
            "aiogram.event",
            "deepl",
            "fastapi",
            "httpx",
            "passlib",
            "sqlalchemy.engine.Engine",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
        ]

        for _log in lognames:
            _logger = logging.getLogger(_log)
            _logger.handlers = [intercept_handler]
            _logger.propagate = False

        return LOGGER.bind(request_id=None, method=None)
