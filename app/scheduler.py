from loguru import logger as LOGGER
from rocketry import Rocketry
from rocketry.conditions.api import hourly

from app.cache import Cache


class Scheduler:
    scheduler: Rocketry
    cache: Cache

    def __init__(self, cache: Cache):
        self.scheduler = Rocketry(
            config={
                "task_execution": "async",
                "silence_task_logging": False,
            }
        )
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

    async def add_tasks(self):
        self.scheduler.task(hourly.at("00:00"), func=self.cache.reset_cache)
