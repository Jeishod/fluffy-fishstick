from fastapi import HTTPException, status
from loguru import logger as LOGGER

from app.db.crud_triggers import KucoinTriggersManager
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.utils.schemas import (
    AddTriggerRequestSchema,
    CachedTriggerSchema,
    GetSingleTriggerSchema,
    TriggerExistsResponseSchema,
)


async def get_all(
    db_triggers: KucoinTriggersManager,
    cache: Cache,
) -> list[GetSingleTriggerSchema]:
    triggers_list = await db_triggers.get_list()
    for trigger in triggers_list:
        cached_trigger_key = f"{trigger.from_symbol}-{trigger.to_symbol}"
        cached_transactions_count = await cache.get_count(name=f"EVENTS-{cached_trigger_key}")
        trigger.transactions_count = cached_transactions_count
        current_count = await cache.get_count_for_period(
            name=f"EVENTS-{cached_trigger_key}",
            period_seconds=trigger.period_seconds,
        )
        trigger.current_count = current_count

    return [GetSingleTriggerSchema.from_orm(trigger) for trigger in triggers_list]


async def already_exists(
    from_symbol: str,
    to_symbol: str,
    db_triggers: KucoinTriggersManager,
) -> TriggerExistsResponseSchema:
    exists = await db_triggers.already_exists(from_symbol=from_symbol, to_symbol=to_symbol)
    return TriggerExistsResponseSchema.parse_obj({"exists": exists})


async def get_trigger(
    from_symbol: str,
    to_symbol: str,
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
    response.price_usdt = cached_trigger["price_usdt"] if cached_trigger else None
    cached_transactions_count = await cache.get_count(name=f"EVENTS-{cached_trigger_key}")
    response.transactions_count = cached_transactions_count
    return GetSingleTriggerSchema.from_orm(response)


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

    cached_trigger_data = CachedTriggerSchema(
        price_usdt=price_usdt,
        min_value_usdt=data.min_value_usdt,
        max_value_usdt=data.max_value_usdt,
        transactions_max_count=data.transactions_max_count,
        period_seconds=data.period_seconds,
        side=data.side,
        is_notified=False,
    )
    await cache.add(name=cached_trigger_key, obj=cached_trigger_data.dict())
    new_trigger.price_usdt = price_usdt

    await ws_client.subscribe(from_symbol=data.from_symbol, to_symbol=data.to_symbol)
    return GetSingleTriggerSchema.from_orm(new_trigger)


async def remove_trigger(
    from_symbol: str,
    to_symbol: str,
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
    await cache.delete(f"EVENTS-{cached_trigger_key}")
    return GetSingleTriggerSchema.from_orm(deleted_trigger)


async def restart_triggers(
    db_triggers: KucoinTriggersManager,
    ws_client: WSClient,
    api_client: APIClient,
    cache: Cache,
) -> None:
    # 1. get triggers from db
    LOGGER.debug("[TASK] Restarting triggers...")
    all_triggers = await db_triggers.get_list()
    await cache.reset_cache()
    for trigger in all_triggers:
        cached_trigger_key = f"{trigger.from_symbol}-{trigger.to_symbol}"

        LOGGER.debug(f"[TASK] Restarting triggers... {cached_trigger_key}")
        price_usdt = await api_client.get_price_in_usdt(from_symbol=trigger.from_symbol)

        # 2. add triggers to cache
        cached_trigger_data = CachedTriggerSchema(
            price_usdt=price_usdt,
            min_value_usdt=trigger.min_value_usdt,
            max_value_usdt=trigger.max_value_usdt,
            transactions_max_count=trigger.transactions_max_count,
            period_seconds=trigger.period_seconds,
            side=trigger.side,
            is_notified=False,
        )
        await cache.add(name=cached_trigger_key, obj=cached_trigger_data.dict())

        # 3. add subscriptions for each trigger
        await ws_client.subscribe(from_symbol=trigger.from_symbol, to_symbol=trigger.to_symbol)
    LOGGER.debug("[TASK] Restarting triggers... Finished!")


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
    return [GetSingleTriggerSchema.from_orm(trigger) for trigger in removed_triggers]
