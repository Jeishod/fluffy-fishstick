from fastapi import Request

from app.clients.kucoin_api import KucoinClient
from app.clients.kucoin_ws import WSClient
from app.db.crud_triggers import KucoinTriggersManager


def get_kucoin_client(request: Request) -> KucoinClient:
    return request.app.client


def get_ws_client(request: Request) -> WSClient:
    return request.app.ws_client


def get_db_triggers(request: Request) -> KucoinTriggersManager:
    return request.app.db_triggers
