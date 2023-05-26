from datetime import datetime

import orjson
from aio_pika import DeliveryMode, Message, connect
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractIncomingMessage, AbstractMessage
from aio_pika.exceptions import ChannelInvalidStateError, ProbableAuthenticationError
from loguru import logger as LOGGER

from app.utils.helpers import default_decimal_serializer


class AMQPClient:
    url: str
    channel: AbstractChannel | None
    connection: AbstractConnection | None

    def __init__(self, url: str):
        self.url = url
        self.channel = None
        self.connection = None

    async def connect(self):
        """Create AMQP connection"""
        try:
            LOGGER.debug("[AMQP Client] Connection initialization...")
            self.connection = await connect(url=self.url)
            LOGGER.debug("[AMQP Client] Connection initialization... Success!")
            self.channel = await self.connection.channel()
            LOGGER.debug(f"[AMQP Client] Channel initialized #{self.channel}")

        except ProbableAuthenticationError:
            LOGGER.debug("[AMQP Client] Connection initialization... Failed!")

    async def publish(self, queue_name: str, data: dict):
        """Publish message to exchange"""
        # 1. prepare message
        message_body = orjson.dumps(data, default=default_decimal_serializer)
        # 2. create message
        message: AbstractMessage = Message(
            body=message_body,
            delivery_mode=DeliveryMode.PERSISTENT,
            timestamp=datetime.utcnow(),
        )
        # 2. send message
        await self.channel.default_exchange.publish(message=message, routing_key=queue_name)
        LOGGER.debug(f"[AMQP Client] Published message | routing key: {queue_name}, message: {data}")

    async def consume(self, queue_name: str, timeout: int | None = None):
        """Consume messages."""
        await self.channel.set_qos(prefetch_count=1)
        queue = await self.channel.declare_queue(name=queue_name, durable=True)
        LOGGER.debug(f"[AMQP Client] Queue declared: {queue_name}")
        try:
            async with queue.iterator(timeout=timeout) as q:
                message: AbstractIncomingMessage
                async for message in q:
                    LOGGER.debug("[AMQP Client] Got message")
                    yield orjson.loads(message.body)
                    await message.ack()
        except ChannelInvalidStateError:
            await self.close_connection()

    async def close_connection(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()
            LOGGER.warning("[AMQP Client] Connection closed.")
