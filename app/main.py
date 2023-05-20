import asyncio

from fastapi import FastAPI
from loguru import logger as LOGGER
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.bot import TGBot
from app.cache import Cache
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.configs import Settings
from app.db.crud_triggers import KucoinTriggersManager
from app.db.session import Database
from app.routers.account import accounts_router
from app.routers.detector import detector_router
from app.routers.market import market_router
from app.routers.system import system_router
from app.scheduler import Scheduler
from app.utils.logger import CustomLogger, LogLevel
from app.utils.tasks import listen_websocket, update_prices


class Application(FastAPI):
    config: Settings
    api_client: APIClient
    ws_client: WSClient
    scheduler: Scheduler
    bot: TGBot | None
    cache: Cache | None
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
        self.cache = Cache(url=self.config.REDIS_URL, decode_responses=False)
        self.bot = TGBot(token=self.config.TELEGRAM_BOT_TOKEN, admin_chat_id=self.config.TELEGRAM_ADMIN_CHAT_ID)
        self.scheduler = Scheduler(cache=self.cache)

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
        self.add_event_handler("startup", self.start_ws)
        self.add_event_handler("startup", self.start_scheduler)
        self.add_event_handler("startup", self.process_ws_messages)

        self.add_event_handler("shutdown", self.close_ws)

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

    async def ping_cache(self) -> None:
        if not await self.cache.ping():
            self.cache = None
            return

    async def ping_bot(self) -> None:
        if not self.config.TELEGRAM_BOT_ENABLED:
            self.bot = None
            return
        LOGGER.debug("[BOT] Ping...")
        await self.bot.send_notification(text="WOAAA, HELLO DUDE!!1")
        LOGGER.debug("[BOT] Ping... Success!")

    async def start_ws(self) -> None:
        await self.ws_client.start()

    async def start_scheduler(self) -> None:
        # TODO: clear cache every 1 hour
        asyncio.create_task(self.scheduler.start())

    async def process_ws_messages(self) -> None:
        # TODO: add price listener for triggers, run this every 3 minutes
        asyncio.create_task(update_prices(api_client=self.api_client, cache=self.cache, db_triggers=self.db_triggers))

        # TODO: restart subscriptions for triggers in database
        # 1. get triggers from db
        # 2. add triggers to cache if cache is empty
        # 3. add subscriptions for each trigger

        # TODO: start listening and process messages
        asyncio.create_task(listen_websocket(ws_client=self.ws_client, cache=self.cache, bot=self.bot))

    async def close_ws(self) -> None:
        await self.ws_client.stop()

    def mount_routers(self) -> None:
        self.include_router(router=detector_router, prefix="/api/v1", tags=["Detector"])
        self.include_router(router=market_router, prefix="/api/v1", tags=["Market"])
        self.include_router(router=accounts_router, prefix="/api/v1", tags=["Accounts"])
        self.include_router(router=system_router, prefix="/api/v1", tags=["System"])


app = Application(settings=Settings())
