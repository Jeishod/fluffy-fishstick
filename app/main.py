import asyncio
import signal

import uvloop
from fastapi import FastAPI
from loguru import logger as LOGGER
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.configs import Settings
from app.db.crud_triggers import KucoinTriggersManager
from app.db.session import Database
from app.managers.triggers_manager import restart_triggers
from app.modules.amqp import AMQPClient
from app.modules.bot import TGBot
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.modules.scheduler import Scheduler
from app.modules.ws_server import WSServer
from app.routers.account import accounts_router
from app.routers.dashboard import dashboard_router
from app.routers.detector import detector_router
from app.routers.market import market_router
from app.routers.system import system_router
from app.utils.logger import CustomLogger, LogLevel
from app.utils.tasks import listen_websocket, process_triggered_data, update_prices


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Application(FastAPI):
    config: Settings
    amqp_client: AMQPClient
    api_client: APIClient
    ws_client: WSClient
    ws_server: WSServer
    scheduler: Scheduler
    bot: TGBot | None
    cache: Cache | None
    db: Database | None
    db_triggers: KucoinTriggersManager | None
    connection_id: str | None
    running_tasks: list[asyncio.Task]

    def __init__(self, settings: Settings):
        CustomLogger.make_logger(level=LogLevel.DEBUG)
        self.docs_url = "/"
        self.config = settings

        self.connection_id = None
        self.running_tasks = []
        self.amqp_client = AMQPClient(url=self.config.RABBITMQ_URL)
        self.api_client = APIClient(
            api_key=self.config.KUCOIN_API_KEY,
            api_secret=self.config.KUCOIN_API_SECRET,
            api_passphrase=self.config.KUCOIN_API_PASSPHRASE,
        )
        self.ws_client = WSClient()
        self.ws_server = WSServer()
        self.db = Database(url=self.config.POSTGRES_URL, echo=self.config.APP_DEBUG)
        self.db_triggers = KucoinTriggersManager(db=self.db)
        self.cache = Cache(url=self.config.REDIS_URL, decode_responses=False)
        self.bot = TGBot(
            token=self.config.TELEGRAM_BOT_TOKEN,
            admin_chat_id=self.config.TELEGRAM_ADMIN_CHAT_ID,
            db_triggers=self.db_triggers,
            cache=self.cache,
        )
        self.scheduler = Scheduler(
            cache=self.cache,
            db_triggers=self.db_triggers,
            ws_client=self.ws_client,
            api_client=self.api_client,
        )

        super().__init__(
            title=self.config.APP_TITLE,
            description=self.config.APP_DESCRIPTION,
            docs_url=self.docs_url,
        )

        self.add_event_handler("startup", self.mount_routers)
        self.add_event_handler("startup", self.connect_amqp)
        self.add_event_handler("startup", self.ping_db)
        self.add_event_handler("startup", self.ping_cache)
        self.add_event_handler("startup", self.ping_bot)
        self.add_event_handler("startup", self.start_ws)
        self.add_event_handler("startup", self.run_tasks)

        self.add_event_handler("shutdown", self.close_ws)
        self.add_event_handler("shutdown", self.close_amqp)
        self.add_event_handler("shutdown", self.stop_bot)
        self.add_event_handler("shutdown", self.stop_tasks)

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
        self.handle_shutdown_signals()

    async def connect_amqp(self) -> None:
        await self.amqp_client.connect()

    async def ping_db(self) -> None:
        if not await self.db.ping():
            self.db = None
            return
        self.db_triggers = KucoinTriggersManager(db=self.db)

    async def ping_cache(self) -> None:
        is_connected, connection_id = await self.cache.ping()
        if not is_connected:
            self.cache = None
            return
        self.connection_id = connection_id

    async def ping_bot(self) -> None:
        if not self.config.TELEGRAM_BOT_ENABLED:
            self.bot = None
            return
        await self.bot.prestart()

    async def start_ws(self) -> None:
        await self.ws_client.start(self.connection_id)

    async def run_tasks(self) -> None:
        # restart subscriptions for triggers in database
        LOGGER.debug("1. RESTARTING TRIGGERS")
        self.running_tasks.append(
            asyncio.create_task(
                restart_triggers(
                    api_client=self.api_client,
                    ws_client=self.ws_client,
                    cache=self.cache,
                    db_triggers=self.db_triggers,
                ),
                name="restart_triggers",
            )
        )

        # add price listener for triggers, run this every 3 minutes
        LOGGER.debug("2. UPDATING PRICES")
        self.running_tasks.append(
            asyncio.create_task(
                update_prices(
                    api_client=self.api_client,
                    cache=self.cache,
                    db_triggers=self.db_triggers,
                ),
                name="update_prices",
            )
        )

        # start listening for messages
        LOGGER.debug("3. LISTENING WEBSOCKETS")
        self.running_tasks.append(
            asyncio.create_task(
                listen_websocket(
                    ws_client=self.ws_client,
                    cache=self.cache,
                    amqp_client=self.amqp_client,
                ),
                name="listen_websocket",
            )
        )

        # start processing triggered messages
        LOGGER.debug("4. PROCESSING TRIGGERED DATA")
        self.running_tasks.append(
            asyncio.create_task(
                process_triggered_data(
                    cache=self.cache,
                    bot=self.bot,
                    amqp_client=self.amqp_client,
                ),
                name="process_triggered_data",
            )
        )

        # start scheduler process
        LOGGER.debug("5. STARTING SCHEDULER")
        self.running_tasks.append(
            asyncio.create_task(
                self.scheduler.start(),
                name="start_scheduler",
            )
        )
        await self.scheduler.add_tasks()

        # start dispatcher process
        LOGGER.debug("6. STARTING BOT")
        if self.bot:
            self.running_tasks.append(
                asyncio.create_task(
                    self.bot.start(),
                    name="start_bot_polling",
                )
            )
        task_names = [task.get_name() for task in self.running_tasks]
        LOGGER.warning(f"[MAIN] RUNNING TASKS: {task_names}")

    async def stop_tasks(self) -> None:
        LOGGER.warning("[MAIN] STOPPING TASKS")

        for task in self.running_tasks:
            task_name = task.get_name()
            LOGGER.warning(f"[MAIN] STOPPING TASK: {task_name}")
            task.cancel()

        # Wait for tasks to be cancelled
        await asyncio.gather(*self.running_tasks, return_exceptions=True)

    def handle_shutdown_signals(self):
        loop = asyncio.get_event_loop()

        # Register signal handlers
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.stop_tasks()))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.stop_tasks()))

    async def stop_bot(self) -> None:
        LOGGER.debug("[MAIN] Stopping BOT")
        await self.bot.stop()

    async def close_ws(self) -> None:
        LOGGER.debug("[MAIN] Closing WS")
        await self.ws_client.stop()

    async def close_amqp(self) -> None:
        LOGGER.debug("[MAIN] Closing AMQP")
        await self.amqp_client.close_connection()

    def mount_routers(self) -> None:
        self.include_router(router=dashboard_router, prefix="/api/v1", tags=["Dashboard"])
        self.include_router(router=detector_router, prefix="/api/v1", tags=["Detector"])
        self.include_router(router=market_router, prefix="/api/v1", tags=["Market"])
        self.include_router(router=accounts_router, prefix="/api/v1", tags=["Accounts"])
        self.include_router(router=system_router, prefix="/api/v1", tags=["System"])


app = Application(settings=Settings())
