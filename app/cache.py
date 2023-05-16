import pickle
from datetime import datetime

from loguru import logger as LOGGER
from redis.asyncio import Redis, from_url
from redis.exceptions import ConnectionError


class Cache:
    redis: Redis

    def __init__(self, url: str, decode_responses: bool):
        self.redis = from_url(url=url, decode_responses=decode_responses)

    async def ping(self) -> bool:
        try:
            LOGGER.debug("[REDIS] Ping...")
            await self.redis.ping()
            LOGGER.debug("[REDIS] Ping... Success!")

            await self.redis.set(name="SERVICE_STARTED", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            from_redis = await self.redis.get(name="SERVICE_STARTED")
            LOGGER.debug(f"[REDIS] CLIENT START TIME: {from_redis}")
            return True

        except ConnectionError:
            LOGGER.warning("[REDIS] Ping... Failed!")
            return False

    async def add(self, name: str, obj):
        pickled_obj = pickle.dumps(obj)
        await self.redis.set(name=name, value=pickled_obj)
        return True

    async def get(self, name: str):
        pickled_obj = await self.redis.get(name=name)
        return pickle.loads(pickled_obj)

    async def delete(self, name: str):
        await self.redis.delete(name)
        return True
