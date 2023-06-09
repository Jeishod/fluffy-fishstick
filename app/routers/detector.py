from fastapi import APIRouter, Depends, status

from app.db.crud_triggers import KucoinTriggersManager
from app.managers import triggers_manager
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.utils.dependencies import get_api_client, get_cache, get_db_triggers, get_ws_client
from app.utils.enums import ExampleSymbols
from app.utils.schemas import (
    AddTriggerRequestSchema,
    GetSingleTriggerSchema,
    SingleTriggerSchema,
    TriggerExistsResponseSchema,
)


detector_router = APIRouter(prefix="/detector")


@detector_router.get("/triggers/all", status_code=status.HTTP_200_OK, response_model=list[GetSingleTriggerSchema])
async def get_all_triggers(
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to get list of active triggers.
    """
    response = await triggers_manager.get_all(
        db_triggers=db_triggers,
        cache=cache,
    )
    return response


@detector_router.get("/triggers/exists", status_code=status.HTTP_200_OK, response_model=TriggerExistsResponseSchema)
async def check_trigger_exists(
    from_symbol: str = ExampleSymbols.PEPE,
    to_symbol: str = ExampleSymbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to check if trigger with given symbols pair exists.
    """
    response = await triggers_manager.already_exists(
        db_triggers=db_triggers,
        from_symbol=from_symbol.upper(),
        to_symbol=to_symbol.upper(),
    )
    return response


@detector_router.get("/triggers", status_code=status.HTTP_200_OK, response_model=GetSingleTriggerSchema)
async def get_trigger(
    from_symbol: str = ExampleSymbols.PEPE,
    to_symbol: str = ExampleSymbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to get single trigger info.
    """
    response = await triggers_manager.get_trigger(
        from_symbol=from_symbol.upper(),
        to_symbol=to_symbol.upper(),
        db_triggers=db_triggers,
        cache=cache,
    )
    return response


@detector_router.post("/triggers", status_code=status.HTTP_201_CREATED, response_model=SingleTriggerSchema)
async def add_trigger(
    data: AddTriggerRequestSchema,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    ws_client: WSClient = Depends(get_ws_client),
    api_client: APIClient = Depends(get_api_client),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to add trigger for given symbols pair.
    """
    response = await triggers_manager.add_trigger(
        data=data,
        db_triggers=db_triggers,
        ws_client=ws_client,
        api_client=api_client,
        cache=cache,
    )
    return response


@detector_router.patch("/triggers", status_code=status.HTTP_201_CREATED, response_model=SingleTriggerSchema)
async def update_trigger(
    data: AddTriggerRequestSchema,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    ws_client: WSClient = Depends(get_ws_client),
    api_client: APIClient = Depends(get_api_client),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to update trigger params for given symbols pair.
    """
    await triggers_manager.remove_trigger(
        from_symbol=data.from_symbol,
        to_symbol=data.to_symbol,
        db_triggers=db_triggers,
        ws_client=ws_client,
        cache=cache,
    )
    response = await triggers_manager.add_trigger(
        data=data,
        db_triggers=db_triggers,
        ws_client=ws_client,
        api_client=api_client,
        cache=cache,
    )
    return response


@detector_router.delete("/triggers", status_code=status.HTTP_200_OK, response_model=SingleTriggerSchema)
async def remove_trigger(
    from_symbol: str = ExampleSymbols.PEPE,
    to_symbol: str = ExampleSymbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    ws_client: WSClient = Depends(get_ws_client),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to remove trigger for given symbols pair.
    """
    response = await triggers_manager.remove_trigger(
        from_symbol=from_symbol.upper(),
        to_symbol=to_symbol.upper(),
        db_triggers=db_triggers,
        ws_client=ws_client,
        cache=cache,
    )
    return response


@detector_router.delete("/triggers/all", status_code=status.HTTP_200_OK, response_model=list[SingleTriggerSchema])
async def remove_all_triggers(
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
    ws_client: WSClient = Depends(get_ws_client),
    cache: Cache = Depends(get_cache),
):
    """
    Request via this endpoint to remove all existing triggers.
    """
    response = await triggers_manager.remove_all_triggers(
        db_triggers=db_triggers,
        ws_client=ws_client,
        cache=cache,
    )
    return response
