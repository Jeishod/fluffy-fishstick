import asyncio

import redis
from fastapi import FastAPI
from loguru import logger as LOGGER
from redis.asyncio import Redis
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.bot import TGBot
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.configs import Settings
from app.db.crud_triggers import KucoinTriggersManager
from app.db.session import Database
from app.routers.account import accounts_router
from app.routers.detector import detector_router
from app.routers.market import market_router
from app.routers.system import system_router
from app.utils.logger import CustomLogger, LogLevel


class Application(FastAPI):
    config: Settings
    api_client: APIClient
    ws_client: WSClient
    bot: TGBot | None
    cache: Redis | None
    db: Database | None
    db_triggers: KucoinTriggersManager | None

    def __init__(self, settings: Settings):
        CustomLogger.make_logger(level=LogLevel.DEBUG)
        self.docs_url = "/"

        self.config = settings
        self.api_client = APIClient(
            api_key=self.config.KUCOIN_API_KEY,
            api_secret=self.config.KUCOIN_API_SECRET,
            api_passphrase=self.config.KUCOIN_API_PASSPHRASE,
        )
        self.ws_client = WSClient()
        self.db = Database(url=self.config.POSTGRES_URL, echo=self.config.APP_DEBUG)
        self.bot = TGBot(token=self.config.TELEGRAM_BOT_TOKEN, admin_chat_id=self.config.TELEGRAM_ADMIN_CHAT_ID)

        self.db_triggers = None

        super().__init__(
            title=self.config.APP_TITLE,
            description=self.config.APP_DESCRIPTION,
            docs_url=self.docs_url,
        )
        self.add_event_handler("startup", self.mount_routers)
        self.add_event_handler("startup", self.ping_db)
        self.add_event_handler("startup", self.ping_cache)
        self.add_event_handler("startup", self.ping_bot)
        self.add_event_handler("startup", self.process_ws_messages)

        self.add_middleware(
            middleware_class=SessionMiddleware,
            secret_key=self.config.APP_SECRET_KEY,
            max_age=self.config.APP_EXPIRE_TOKEN,
        )
        self.add_middleware(
            middleware_class=CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def ping_db(self) -> None:
        if not await self.db.ping():
            self.db = None
            return
        self.db_triggers = KucoinTriggersManager(db=self.db)

    async def ping_bot(self) -> None:
        if not self.config.TELEGRAM_BOT_ENABLED:
            self.bot = None
            return
        LOGGER.debug("[BOT] Ping...")
        await self.bot.send_notification(text="WOAAA, HELLO DUDE!!1")
        LOGGER.debug("[BOT] Ping... Success!")

    async def ping_cache(self) -> None:
        try:
            LOGGER.debug("[REDIS] Ping...")
            await self.cache.ping()
            LOGGER.debug("[REDIS] Ping... Success!")
        except redis.exceptions.ConnectionError:
            LOGGER.warning("[REDIS] Ping... Failed!")
            self.cache = None
            return
        object_dict = {
            "first_val": "12",
            "second_val": "32",
            "third_val": 1233322,
        }
        await self.cache.hset(name="TRIGGERS", mapping=object_dict)
        from_redis = await self.cache.hgetall(name="TRIGGERS")
        LOGGER.debug(f"[REDIS] GOT: {from_redis}")

    async def process_ws_messages(self):
        ws_token = await self.api_client.get_ws_token()
        self.ws_client = WSClient(token=ws_token)
        asyncio.create_task(self.ws_client.start())

    def mount_routers(self) -> None:
        self.include_router(router=detector_router, prefix="/api/v1", tags=["Detector"])
        self.include_router(router=market_router, prefix="/api/v1", tags=["Market"])
        self.include_router(router=accounts_router, prefix="/api/v1", tags=["Accounts"])
        self.include_router(router=system_router, prefix="/api/v1", tags=["System"])


app = Application(settings=Settings())
