from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.kucoin_ws import WSClient
from app.db.crud_triggers import KucoinTriggersManager
from app.utils.dependencies import get_db_triggers, get_ws_client
from app.utils.enums import Symbols
from app.utils.schemas import AddTriggerRequestSchema, RetrieveTriggerResponseSchema, TriggerExistsResponseSchema

detector_router = APIRouter(prefix="/detector")


@detector_router.get(
    "/triggers/list",
    status_code=status.HTTP_200_OK,
    response_model=list[RetrieveTriggerResponseSchema],
)
async def get_triggers_list(
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to get list of active triggers.
    """
    triggers_list = await db_triggers.get_list()
    return triggers_list


@detector_router.get("/triggers/exists", status_code=status.HTTP_200_OK, response_model=TriggerExistsResponseSchema)
async def check_trigger_exists(
    from_symbol: Symbols = Symbols.PEPE,
    to_symbol: Symbols = Symbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to check if trigger with given symbols pair exists.
    """
    exists = await db_triggers.already_exists(from_symbol=from_symbol, to_symbol=to_symbol)
    return {"exists": exists}


@detector_router.get("/triggers", status_code=status.HTTP_200_OK, response_model=RetrieveTriggerResponseSchema)
async def retrieve_single_trigger(
    from_symbol: Symbols = Symbols.PEPE,
    to_symbol: Symbols = Symbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to get list of active triggers.
    """
    response = await db_triggers.get(from_symbol=from_symbol, to_symbol=to_symbol)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger was not found for pair {from_symbol}-{to_symbol}",
        )
    return response


@detector_router.post("/triggers", status_code=status.HTTP_201_CREATED, response_model=RetrieveTriggerResponseSchema)
async def add_trigger(
    data: AddTriggerRequestSchema,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to add trigger for given symbols pair.
    """
    new_trigger = await db_triggers.create(**data.dict())
    if not new_trigger:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Couldn't create a trigger for pair {data.from_symbol}-{data.to_symbol}",
        )
    return new_trigger


@detector_router.delete("/triggers", status_code=status.HTTP_200_OK, response_model=RetrieveTriggerResponseSchema)
async def remove_trigger(
    from_symbol: Symbols = Symbols.PEPE,
    to_symbol: Symbols = Symbols.USDT,
    db_triggers: KucoinTriggersManager = Depends(get_db_triggers),
):
    """
    Request via this endpoint to remove trigger for given symbols pair.
    """
    success = await db_triggers.remove(from_symbol=from_symbol, to_symbol=to_symbol)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger was not found for pair {from_symbol}-{to_symbol}",
        )
    return {"status": "Trigger removed.", "symbols_pair": f"{from_symbol}-{to_symbol}"}


@detector_router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def add_subscription(
    from_symbol: Symbols = Symbols.PEPE,
    to_symbol: Symbols = Symbols.USDT,
    ws_client: WSClient = Depends(get_ws_client),
):
    """
    Request via this endpoint to add subscription on events with specific symbols pair.
    """
    await ws_client.subscribe(from_symbol=from_symbol, to_symbol=to_symbol)
    return {"status": "Subscription added.", "symbols_pair": f"{from_symbol}-{to_symbol}"}


@detector_router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    from_symbol: Symbols = Symbols.PEPE,
    to_symbol: Symbols = Symbols.USDT,
    ws_client: WSClient = Depends(get_ws_client),
):
    """
    Request via this endpoint to add subscription on events with specific symbols pair.
    """
    await ws_client.unsubscribe(from_symbol=from_symbol, to_symbol=to_symbol)
    return {"status": "Subscription cancelled", "symbols_pair": f"{from_symbol}-{to_symbol}"}
