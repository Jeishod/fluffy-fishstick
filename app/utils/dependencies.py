from fastapi import Request

from app.cache import Cache
from app.clients.kucoin_api import APIClient
from app.clients.kucoin_ws import WSClient
from app.db.crud_triggers import KucoinTriggersManager


def get_api_client(request: Request) -> APIClient:
    return request.app.api_client


def get_ws_client(request: Request) -> WSClient:
    return request.app.ws_client


def get_cache(request: Request) -> Cache:
    return request.app.cache


def get_db_triggers(request: Request) -> KucoinTriggersManager:
    return request.app.db_triggers
