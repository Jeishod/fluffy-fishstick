import asyncio
import decimal
from decimal import Decimal

import websockets.exceptions
from loguru import logger as LOGGER

from app.db.crud_triggers import KucoinTriggersManager
from app.modules.amqp import AMQPClient
from app.modules.bot import TGBot
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.utils.enums import TradeSide
from app.utils.schemas import CachedTriggerSchema, KucoinWSMessage, ParsedWSMessage


TRIGGERING_MESSAGES_QUEUE = "triggering_messages"


async def update_prices(
    cache: Cache,
    api_client: APIClient,
    db_triggers: KucoinTriggersManager,
    update_period_sec: int = 60,
) -> None:
    """Update price in USDT for each trigger saved in database, periodically"""
    while True:
        try:
            triggers = await db_triggers.get_list()
            for trigger in triggers:
                name = f"{trigger.from_symbol}-{trigger.to_symbol}"
                trigger_price = await api_client.get_price_in_usdt(from_symbol=trigger.from_symbol)
                cached_trigger = await cache.get(name=name)
                if cached_trigger is None:
                    cached_trigger = {}
                    cached_trigger.update({"price_usdt": trigger_price})
                else:
                    if cached_trigger["price_usdt"] != trigger_price:
                        cached_trigger["price_usdt"] = trigger_price
                await cache.add(name=name, obj=cached_trigger)
                LOGGER.debug(f"[TASK] Price updated for {trigger.from_symbol}: {trigger_price}")
            await asyncio.sleep(update_period_sec)
        except Exception as e:
            LOGGER.error(f"Exception during updating tickers prices: {e}")
            break


async def listen_websocket(cache: Cache, ws_client: WSClient, amqp_client: AMQPClient) -> None:
    """1. Start listening websocket fo new messages and run function to process each message"""
    try:
        async for message in ws_client.websocket:
            await process_message(cache=cache, message=message, amqp_client=amqp_client)
    except websockets.exceptions.ConnectionClosedError:
        LOGGER.error("[TASK] Websocket connection error on Kucoin side")
        await ws_client.connect()


async def process_message(cache: Cache, message: str | bytes, amqp_client: AMQPClient) -> None:
    """2. Convert message to pydantic model and process it for each message type."""

    # 1. convert message
    kucoin_message: KucoinWSMessage = KucoinWSMessage.parse_raw(message)

    # 2. get message type and process data if needed
    if kucoin_message.type == "welcome":
        LOGGER.debug(f"[WS CLIENT] Websocket accepted: {message}")
        connection_id = kucoin_message.id
        await cache.set_connection_id(connection_id=connection_id)
        return
    if kucoin_message.type == "ack":
        LOGGER.debug(f"[WS CLIENT] Server confirmed {message}")
        return
    if kucoin_message.type == "message":
        # parse message
        parsed_message: ParsedWSMessage = ParsedWSMessage(
            symbol=kucoin_message.data.symbol,
            side=kucoin_message.data.side,
            size=kucoin_message.data.size,
            time=kucoin_message.data.time,
        )
        await process_data(cache=cache, data=parsed_message, amqp_client=amqp_client)


async def process_data(cache: Cache, data: ParsedWSMessage, amqp_client: AMQPClient) -> None:
    """3. Process websocket messages with type `message`"""

    # 1. check if transaction is triggering
    is_triggering, cached_trigger = await check_if_triggering(
        cache=cache,
        symbol=data.symbol,
        size=data.size,
        side=data.side,
    )
    if not is_triggering:
        return

    # add message to rabbitmq
    await amqp_client.publish(queue_name=TRIGGERING_MESSAGES_QUEUE, data=data.dict())


async def check_if_triggering(cache: Cache, symbol: str, size: decimal, side: TradeSide) -> tuple[bool, dict | None]:
    """Check if message data is triggering notifications by symbol and size"""
    # TODO: add WS Server

    # 1. get cached trigger
    cached_trigger = await cache.get(name=symbol)
    if cached_trigger is None:
        return False, None

    triggering_sides = []
    try:
        if cached_trigger["side"].upper() == "BOTH":
            triggering_sides = ["BUY", "SELL"]
        if cached_trigger["side"].upper() == "SELL":
            triggering_sides = ["SELL"]
        if cached_trigger["side"].upper() == "BUY":
            triggering_sides = ["BUY"]
    except (AttributeError, KeyError):
        triggering_sides = ["BUY", "SELL"]

    if side.upper() not in triggering_sides:
        return False, None

    min_value_usdt = cached_trigger.get("min_value_usdt")
    max_value_usdt = cached_trigger.get("max_value_usdt")
    cached_price = cached_trigger.get("price_usdt")

    # 2. get current transaction summ in USDT
    summ_usdt = decimal.Decimal(cached_price) * size

    # 3. compare current summ with cached trigger min\max
    is_triggering = min_value_usdt < summ_usdt < max_value_usdt

    if is_triggering:
        # TODO: remove logs after debug
        from_symbol, to_symbol = symbol.split("-")
        log_message = make_log_string(
            side=side,
            size=size,
            summ=summ_usdt,
            from_symbol=from_symbol,
            to_symbol=to_symbol,
        )
        LOGGER.debug(log_message)
        # TODO: 4. send message to websocket thru websocket server

    return is_triggering, cached_trigger


async def process_triggered_data(cache: Cache, bot: TGBot, amqp_client: AMQPClient) -> None:
    """Process consumed messages from rabbitmq"""
    async for message in amqp_client.consume(queue_name=TRIGGERING_MESSAGES_QUEUE):
        parsed_message = ParsedWSMessage(**message)
        # 1. get cached trigger

        from_symbol, to_symbol = parsed_message.symbol.split("-")

        cached_trigger_table_name = f"{from_symbol}-{to_symbol}"

        cached_trigger = await cache.get(name=cached_trigger_table_name)
        parsed_trigger = CachedTriggerSchema(**cached_trigger)

        # 2. add record for to cached events table
        cached_events_table = f"EVENTS-{cached_trigger_table_name}"
        await cache.add_for_now(name=cached_events_table, time=parsed_message.time)

        # 3. get count of cached events
        transactions_count = await cache.get_count_for_period(
            name=cached_events_table,
            period_seconds=parsed_trigger.period_seconds,
        )
        if transactions_count == parsed_trigger.transactions_max_count:
            if not parsed_trigger.is_notified:
                # 4. send telegram notification
                cached_transactions_count = await cache.get_count(name=f"EVENTS-{cached_trigger_table_name}")
                text = (
                    f"❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️<b>ACHTUNG</b>❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️\n"  # noqa
                    f"🚨<b>{cached_trigger_table_name}</b>\n"
                    f"triggering count: <b>{transactions_count}</b>\n"
                    f"period, sec: <b>{parsed_trigger.period_seconds}</b>\n"
                    f"side: <b>{parsed_trigger.side}</b>\n"
                    f"all transactions count: {cached_transactions_count}"
                )
                await bot.send_notification(text=text)
                parsed_trigger.is_notified = True
                await cache.add(name=cached_trigger_table_name, obj=parsed_trigger.dict())


def make_log_string(side: str, size: Decimal, summ: Decimal, from_symbol: str, to_symbol: str) -> str:
    """Generate log message string from given data"""
    operation = "BUY <<" if side == "buy" else ">> SELL"
    operation_size = round(number=size, ndigits=8)
    operation_summ = round(number=summ, ndigits=4)
    event_info = f"{operation_size: >16} {from_symbol}-{to_symbol} | {operation_summ: >12} USDT"
    log_message = f"[WS CLIENT] {operation: ^7} {event_info}"
    return log_message
