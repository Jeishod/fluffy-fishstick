from fastapi import Request, WebSocket

from app.db.crud_triggers import KucoinTriggersManager
from app.modules.cache import Cache
from app.modules.clients.kucoin_api import APIClient
from app.modules.clients.kucoin_ws import WSClient
from app.modules.ws_server import WSServer


def get_api_client(request: Request) -> APIClient:
    return request.app.api_client


def get_ws_client(request: Request) -> WSClient:
    return request.app.ws_client


def get_ws_server(ws: WebSocket) -> WSServer:
    return ws.app.ws_server


def get_cache(request: Request) -> Cache:
    return request.app.cache


def get_db_triggers(request: Request) -> KucoinTriggersManager:
    return request.app.db_triggers
