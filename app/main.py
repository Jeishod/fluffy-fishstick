from fastapi import FastAPI
from loguru import logger as LOGGER

from app.client import KucoinClient
from app.configs import Settings
from app.logger import CustomLogger, LogLevel
from app.router import system_router, kucoin_router


class Application(FastAPI):
    logger: LOGGER
    config: Settings

    def __init__(self, settings: Settings):
        self.config = settings
        self.logger = CustomLogger.make_logger(level=LogLevel.DEBUG)
        self.client = KucoinClient(
            api_key=self.config.KUCOIN_API_KEY,
            api_secret=self.config.KUCOIN_API_SECRET,
            api_passphrase=self.config.KUCOIN_API_PASSPHRASE,
        )
        self.docs_url = "/"

        super().__init__(
            title=self.config.APP_TITLE,
            description=self.config.APP_DESCRIPTION,
            docs_url=self.docs_url,
        )
        self.add_event_handler("startup", self.mount_routers)

    def mount_routers(self) -> None:
        self.include_router(router=kucoin_router, prefix="/api/v1", tags=["Kucoin"])
        self.include_router(router=system_router, prefix="/api/v1", tags=["System"])


app = Application(settings=Settings())
