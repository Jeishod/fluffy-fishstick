from rocketry import Rocketry
from loguru import logger as LOGGER

from app.cache import Cache


class Scheduler:
    scheduler: Rocketry
    cache: Cache

    def __init__(self, cache: Cache):
        self.scheduler = Rocketry(execution="async")
        self.cache = cache

    async def start(self):
        LOGGER.debug(f"[SCHEDULER] Starting...")
        try:
            await self.scheduler.serve()
        except (KeyboardInterrupt, Exception):
            await self.stop()

    async def stop(self):
        LOGGER.warning(f"[SCHEDULER] Stopping...")
        if self.scheduler.session is not None:
            await self.scheduler.session.shutdown()

    # async def reset_cache(self):
    #     await self.scheduler.task("every 1 minute", cache.reset)

    # TODO: stop subscriptions every hour
    # TODO: reset cache every hour.
    # TODO: start subscriptions every hour
