from datetime import datetime, timedelta

import orjson
from loguru import logger as LOGGER
from redis.asyncio import Redis, from_url, client
from redis.exceptions import ConnectionError


class Cache:
    redis: Redis
    notifications_channel: str
    psub: client.PubSub

    def __init__(self, url: str, decode_responses: bool = False):
        self.redis = from_url(url=url, decode_responses=decode_responses, encoding="utf-8", max_connections=10)
        self.notifications_channel = "notifications"
        self.psub = self.redis.pubsub()

    async def ping(self) -> bool:
        try:
            LOGGER.debug("[REDIS] Ping...")
            await self.redis.ping()
            LOGGER.debug("[REDIS] Ping... Success!")

            await self.redis.set(name="SERVICE_STARTED", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            from_redis = await self.redis.get(name="SERVICE_STARTED")
            LOGGER.debug(f"[REDIS] CLIENT START TIME: {from_redis.decode()}")
            return True

        except ConnectionError:
            LOGGER.warning("[REDIS] Ping... Failed!")
            return False

    async def add_for_now(self, name: str) -> int:
        now = datetime.now()
        now_string = now.isoformat()
        timestamp = now.timestamp()
        result = await self.redis.zadd(name=name, mapping={now_string: timestamp}, nx=True)
        return result

    async def get_count_for_period(self, name: str, period_seconds: int) -> int:
        now = datetime.now()
        min_val = now - timedelta(seconds=period_seconds)
        count = await self.redis.zcount(name=name, min=min_val.timestamp(), max=now.timestamp())
        return count

    async def get_count(self, name: str) -> int:
        count = await self.redis.zcard(name=name)
        return count

    async def get_items_for_period(self, name: str, period_seconds: int) -> list[str]:
        now = datetime.now()
        min_val = now - timedelta(seconds=period_seconds)
        events = await self.redis.zrangebyscore(name=name, min=min_val.timestamp(), max=now.timestamp())
        return events

    async def add(self, name: str, obj) -> bool:
        json_obj = orjson.dumps(obj)
        await self.redis.set(name=name, value=json_obj)
        return True

    async def get(self, name: str) -> dict:
        json_obj = await self.redis.get(name=name)
        return orjson.loads(json_obj)

    async def delete(self, name: str) -> bool:
        await self.redis.delete(name)
        return True

    async def publish(self, data: str) -> None:
        await self.redis.publish(channel=self.notifications_channel, message=data)

    async def get_pubsub(self):
        self.psub = self.redis.pubsub()
