import asyncio
import decimal
from decimal import Decimal

from loguru import logger as LOGGER

from app.db.crud_triggers import KucoinTriggersManager
from app.modules.bot import TGBot
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.utils.schemas import KucoinWSMessage, KucoinWSMessageData


async def update_prices(
    cache: Cache,
    api_client: APIClient,
    db_triggers: KucoinTriggersManager,
    update_period_sec: int = 60,
) -> None:
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


async def listen_websocket(cache: Cache, ws_client: WSClient, bot: TGBot) -> None:
    async for message in ws_client.websocket:
        await process_message(cache=cache, message=message, bot=bot)


async def process_message(cache: Cache, message: str | bytes, bot: TGBot) -> None:
    parsed_message = KucoinWSMessage.parse_raw(message)
    if parsed_message.type == "welcome":
        LOGGER.debug(f"[WS CLIENT] Websocket accepted: {message}")
        connection_id = parsed_message.id
        await cache.set_connection_id(connection_id=connection_id)
        return
    if parsed_message.type == "ack":
        LOGGER.debug(f"[WS CLIENT] Server confirmed {message}")
        return
    if parsed_message.type == "message":
        await process_data(cache=cache, data=parsed_message.data, bot=bot)


async def check_if_triggering(cache: Cache, data: KucoinWSMessageData) -> tuple[bool, dict | None]:
    # TODO: add WS Server

    # 1. get cached trigger
    cached_trigger = await cache.get(name=data.symbol)
    if cached_trigger is None:
        return False, None

    min_value_usdt = cached_trigger.get("min_value_usdt")
    max_value_usdt = cached_trigger.get("max_value_usdt")
    cached_price = cached_trigger.get("price_usdt")

    # 2. get current transaction summ in USDT
    summ_usdt = decimal.Decimal(cached_price) * data.size

    # 3. compare current summ with cached trigger min\max
    is_triggering = min_value_usdt < summ_usdt < max_value_usdt

    if is_triggering:
        # TODO: remove logs after debug
        from_symbol, to_symbol = data.symbol.split("-")
        log_message = make_log_string(
            side=data.side,
            size=data.size,
            summ=summ_usdt,
            from_symbol=from_symbol,
            to_symbol=to_symbol,
        )
        LOGGER.debug(log_message)
        # TODO: 4. send message to websocket thru websocket server

    return is_triggering, cached_trigger


async def process_data(cache: Cache, data: KucoinWSMessageData, bot: TGBot) -> None:
    # 1. check if transaction is triggering
    is_triggering, cached_trigger = await check_if_triggering(cache=cache, data=data)
    if not is_triggering:
        return

    transactions_max_count = cached_trigger.get("transactions_max_count")
    period_seconds = cached_trigger.get("period_seconds")

    # 2. add record for to cached events table
    cached_events_table = f"EVENTS-{data.symbol}"
    await cache.add_for_now(name=cached_events_table)

    # 3. get count of cached events
    transactions_count = await cache.get_count_for_period(name=cached_events_table, period_seconds=period_seconds)
    if transactions_count == transactions_max_count:
        # 4. send telegram notification
        text = (
            f"<b>❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️ACHTUNG❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️</b>\n"  # noqa
            f"🤬🤬🤬MAZAFAKERS ACTIVE!!11\n"
            f"{data.symbol}: already {transactions_count} transactions"
        )
        await bot.send_notification(text=text)
    return


def make_log_string(side: str, size: Decimal, summ: Decimal, from_symbol: str, to_symbol: str) -> str:
    operation = "BUY <<" if side == "buy" else ">> SELL"
    operation_size = round(number=size, ndigits=8)
    operation_summ = round(number=summ, ndigits=4)
    event_info = f"{operation_size: >16} {from_symbol}-{to_symbol} | {operation_summ: >12} USDT"
    log_message = f"[WS CLIENT] {operation: ^7} {event_info}"
    return log_message
