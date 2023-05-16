import asyncio
from decimal import Decimal

from loguru import logger as LOGGER

from app.cache import Cache
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.utils.schemas import KucoinWSMessage, KucoinWSMessageData


async def update_prices(cache: Cache, api_client: APIClient) -> None:
    while True:
        try:
            await asyncio.sleep(300)
        except Exception as e:
            LOGGER.error(f"Exception during updating tickers prices: {e}")
            break


async def listen_websocket(ws_client: WSClient) -> None:
    async for message in ws_client.websocket:
        await process_message(message=message)


async def process_message(message: str | bytes) -> None:
    parsed_message = KucoinWSMessage.parse_raw(message)
    if parsed_message.type == "welcome":
        LOGGER.debug(f"[WS CLIENT] Websocket accepted: {message}")
        return
    if parsed_message.type == "ack":
        LOGGER.debug(f"[WS CLIENT] Server confirmed {message}")
        return
    if parsed_message.type == "message":
        await process_data(data=parsed_message.data)


async def process_data(data: KucoinWSMessageData) -> None:
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
    summ = round(number=(data.price * data.size), ndigits=4)

    min_value = 300
    max_value = 1000

    if min_value < summ < max_value:
        # ADD LOGS WHILE DEBUG
        log_message = make_log_string(
            side=data.side, size=data.size, summ=summ, from_symbol=from_symbol, to_symbol=to_symbol
        )
        LOGGER.debug(log_message)


def make_log_string(side: str, size: Decimal, summ: int, from_symbol: str, to_symbol: str) -> str:
    operation = "BUY <<" if side == "buy" else ">> SELL"
    operation_size = round(number=size, ndigits=4)
    event_info = f"{operation_size: >16} {from_symbol}\tfor\t{summ: >12} {to_symbol}"
    log_message = f"[WS CLIENT] {operation: ^7} {event_info}"
    return log_message
