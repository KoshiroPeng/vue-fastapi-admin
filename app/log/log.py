import sys
from pathlib import Path

from loguru import logger as loguru_logger

from app.settings import settings


class Loggin:
    def __init__(self) -> None:
        debug = settings.DEBUG
        if debug:
            self.level = "DEBUG"
        else:
            self.level = "INFO"

    def setup_logger(self):
        logs_root = Path(settings.LOGS_ROOT)
        logs_root.mkdir(parents=True, exist_ok=True)

        loguru_logger.remove()
        loguru_logger.add(sink=sys.stdout, level=self.level)
        loguru_logger.add(
            sink=logs_root / "application.log",
            level=self.level,
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
            enqueue=True,
        )
        return loguru_logger


loggin = Loggin()
logger = loggin.setup_logger()
