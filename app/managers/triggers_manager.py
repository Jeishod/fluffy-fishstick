from fastapi import HTTPException, status
from loguru import logger as LOGGER

from app.cache import Cache
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.db.crud_triggers import KucoinTriggersManager
from app.utils.enums import Symbols
from app.utils.schemas import AddTriggerRequestSchema, GetSingleTriggerSchema, TriggerExistsResponseSchema


async def get_all(db_triggers: KucoinTriggersManager) -> list[GetSingleTriggerSchema]:
    triggers_list = await db_triggers.get_list()
    return triggers_list


async def already_exists(
    from_symbol: Symbols, to_symbol: Symbols, db_triggers: KucoinTriggersManager
) -> TriggerExistsResponseSchema:
    exists = await db_triggers.already_exists(from_symbol=from_symbol, to_symbol=to_symbol)
    return {"exists": exists}


async def get_trigger(
    from_symbol: Symbols,
    to_symbol: Symbols,
    db_triggers: KucoinTriggersManager,
    cache: Cache,
) -> GetSingleTriggerSchema:
    response = await db_triggers.get(from_symbol=from_symbol, to_symbol=to_symbol)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger was not found for pair {from_symbol}-{to_symbol}",
        )

    # get cached trigger
    cached_trigger_key = f"{from_symbol}-{to_symbol}"
    cached_trigger = await cache.get(name=cached_trigger_key)
    LOGGER.warning(f"CACHED TRIGGER: {cached_trigger}")
    response.price_usdt = cached_trigger["price_usdt"]
    response.transactions_max_count = cached_trigger["transactions_count"]
    return response


async def add_trigger(
    data: AddTriggerRequestSchema,
    db_triggers: KucoinTriggersManager,
    ws_client: WSClient,
    api_client: APIClient,
    cache: Cache,
) -> GetSingleTriggerSchema:
    """
    Request via this endpoint to add trigger for given symbols pair.
    """
    new_trigger = await db_triggers.create(**data.dict())
    if not new_trigger:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Couldn't create a trigger for pair {data.from_symbol}-{data.to_symbol}",
        )
    # get current ticker for 'from_symbol' in USDT
    price_usdt = await api_client.get_price_in_usdt(from_symbol=data.from_symbol)

    # add trigger with price to cache
    cached_trigger_key = f"{data.from_symbol}-{data.to_symbol}"
    cached_trigger_data = {
        "price_usdt": price_usdt,
        "min_value_usdt": data.min_value_usdt,
        "max_value_usdt": data.max_value_usdt,
        "transactions_count": 0,
    }
    await cache.add(name=cached_trigger_key, obj=cached_trigger_data)
    new_trigger.price_usdt = price_usdt

    await ws_client.subscribe(from_symbol=data.from_symbol, to_symbol=data.to_symbol)
    return new_trigger


async def remove_trigger(
    from_symbol: Symbols,
    to_symbol: Symbols,
    db_triggers: KucoinTriggersManager,
    ws_client: WSClient,
    cache: Cache,
) -> GetSingleTriggerSchema:
    await ws_client.unsubscribe(from_symbol=from_symbol, to_symbol=to_symbol)
    deleted_trigger = await db_triggers.remove(from_symbol=from_symbol, to_symbol=to_symbol)
    if not deleted_trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger was not found for pair {from_symbol}-{to_symbol}",
        )
    cached_trigger_key = f"{from_symbol}-{to_symbol}"

    # remove trigger from cache
    await cache.delete(cached_trigger_key)
    return deleted_trigger


async def remove_all_triggers(
    db_triggers: KucoinTriggersManager,
    ws_client: WSClient,
    cache: Cache,
) -> list[GetSingleTriggerSchema]:
    removed_triggers = []
    all_triggers = await db_triggers.get_list()
    for trigger in all_triggers:
        removed_trigger = await remove_trigger(
            from_symbol=trigger.from_symbol,
            to_symbol=trigger.to_symbol,
            db_triggers=db_triggers,
            ws_client=ws_client,
            cache=cache,
        )
        removed_triggers.append(removed_trigger)
    return removed_triggers
