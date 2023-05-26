from loguru import logger as LOGGER
from rocketry import Rocketry
from rocketry.conditions.api import hourly

from app.db.crud_triggers import KucoinTriggersManager
from app.managers.triggers_manager import restart_triggers
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient


class Scheduler:
    scheduler: Rocketry
    db_triggers: KucoinTriggersManager
    ws_client: WSClient
    api_client: APIClient
    cache: Cache

    def __init__(self, cache: Cache, db_triggers: KucoinTriggersManager, ws_client: WSClient, api_client: APIClient):
        self.scheduler = Rocketry(
            config={
                "task_execution": "async",
                "silence_task_logging": False,
            }
        )
        self.db_triggers = db_triggers
        self.ws_client = ws_client
        self.api_client = api_client
        self.cache = cache

    async def start(self):
        LOGGER.debug("[SCHEDULER] Starting...")
        try:
            await self.scheduler.serve()
        except (KeyboardInterrupt, Exception):
            await self.stop()

    async def stop(self):
        LOGGER.warning("[SCHEDULER] Stopping...")
        if self.scheduler.session is not None:
            await self.scheduler.session.shut_down()

    async def restart_triggers_task(self):
        await restart_triggers(
            db_triggers=self.db_triggers,
            ws_client=self.ws_client,
            api_client=self.api_client,
            cache=self.cache,
        )

    async def add_tasks(self):
        # task to reset is_notified to False for each trigger in cache
        self.scheduler.task(
            start_cond=hourly.at("00:00"),
            name="restart_triggers",
            func=self.restart_triggers_task,
        )
