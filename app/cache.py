from datetime import datetime, timedelta

import orjson
from loguru import logger as LOGGER
from redis.asyncio import Redis, client, from_url
from redis.exceptions import ConnectionError

from app.utils.helpers import gen_request_id


class Cache:
    redis: Redis
    notifications_channel: str
    psub: client.PubSub

    def __init__(self, url: str, decode_responses: bool = False):
        self.redis = from_url(url=url, decode_responses=decode_responses, encoding="utf-8", max_connections=10)
        self.notifications_channel = "notifications"
        self.psub = self.redis.pubsub()

    async def ping(self) -> str | None:
        try:
            LOGGER.debug("[REDIS] Ping...")
            await self.redis.ping()
            LOGGER.debug("[REDIS] Ping... Success!")

            # RESET CONNECTION ID
            connection_id = await self.get_connection_id()
            if not connection_id:
                await self.set_connection_id(connection_id=gen_request_id())
            return connection_id

        except ConnectionError:
            LOGGER.warning("[REDIS] Ping... Failed!")
            return None

    async def get_connection_id(self) -> str:
        connection_id = await self.redis.get(name="CONNECTION_ID")
        decoded_connection_id = connection_id.decode()
        LOGGER.debug(f"[REDIS] GOT CONNECTION ID: {decoded_connection_id}")
        return decoded_connection_id

    async def set_connection_id(self, connection_id: str) -> None:
        await self.redis.set(name="CONNECTION_ID", value=connection_id)
        LOGGER.debug(f"[REDIS] SET CONNECTION ID: {connection_id}")

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

    async def get(self, name: str) -> dict | None:
        json_obj = await self.redis.get(name=name)
        if json_obj is None:
            return None
        return orjson.loads(json_obj)

    async def delete(self, name: str) -> bool:
        await self.redis.delete(name)
        return True

    async def get_collections_by_pattern(self, pattern: str):
        keys = await self.redis.keys(pattern)
        return keys

    async def bulk_delete(self, names: list[str]) -> bool:
        pipeline = self.redis.pipeline()
        for name in names:
            pipeline.delete(name)
        await pipeline.execute()
        return True

    async def reset_cache(self):
        cache_to_reset = await self.get_collections_by_pattern(pattern="EVENTS-*")
        await self.bulk_delete(cache_to_reset)

    async def publish(self, data: str) -> None:
        await self.redis.publish(channel=self.notifications_channel, message=data)

    async def get_pubsub(self):
        self.psub = self.redis.pubsub()
