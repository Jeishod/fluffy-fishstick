import asyncio
import decimal
from decimal import Decimal

from loguru import logger as LOGGER

from app.bot import TGBot
from app.cache import Cache
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.db.crud_triggers import KucoinTriggersManager
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
        return
    if parsed_message.type == "ack":
        LOGGER.debug(f"[WS CLIENT] Server confirmed {message}")
        return
    if parsed_message.type == "message":
        await process_data(cache=cache, data=parsed_message.data, bot=bot)


async def process_data(cache: Cache, data: KucoinWSMessageData, bot: TGBot) -> None:
    """
    # TODO: update
    0. use `cache` instance
    1. get symbols
    2. get cached_trigger from cache
    2. get transaction_value in USDT from cached_trigger for from_symbol
    3. compare transaction_value with trigger min_val and max_val
    4. add +1 to transactions_max_count
    """
    from_symbol, to_symbol = data.symbol.split("-")

    cached_trigger = await cache.get(data.symbol)
    summ_usdt = decimal.Decimal(cached_trigger["price_usdt"]) * data.size

    min_value_usdt = cached_trigger.get("min_value_usdt")
    max_value_usdt = cached_trigger.get("max_value_usdt")
    transactions_count = cached_trigger["transactions_count"]
    transactions_max_count = cached_trigger.get("transactions_max_count")

    if min_value_usdt < summ_usdt < max_value_usdt:
        new_count = transactions_count + 1
        cached_trigger["transactions_count"] = new_count
        if new_count == transactions_max_count:
            text = (
                f"<b>❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️ACHTUNG❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️❗️️️️️️️️️️️️️️️️️️️️️️</b>\n🤬🤬🤬MAZAFAKERS ACTIVE!!11\n"
                f"{data.symbol}: already {new_count} transactions"
            )
            await bot.send_notification(text=text)
        await cache.add(name=data.symbol, obj=cached_trigger)

        # TODO: remove logs after debug
        log_message = make_log_string(
            side=data.side,
            size=data.size,
            summ=summ_usdt,
            from_symbol=from_symbol,
            to_symbol=to_symbol,
        )
        LOGGER.debug(log_message)


def make_log_string(side: str, size: Decimal, summ: Decimal, from_symbol: str, to_symbol: str) -> str:
    operation = "BUY <<" if side == "buy" else ">> SELL"
    operation_size = round(number=size, ndigits=8)
    operation_summ = round(number=summ, ndigits=4)
    event_info = f"{operation_size: >16} {from_symbol}-{to_symbol} | {operation_summ: >12} USDT"
    log_message = f"[WS CLIENT] {operation: ^7} {event_info}"
    return log_message
