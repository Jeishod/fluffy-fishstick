from fastapi import Request

from app.clients.kucoin_api import KucoinClient
from app.clients.kucoin_ws import WSClient


def get_kucoin_client(request: Request) -> KucoinClient:
    return request.app.client


def get_ws_client(request: Request) -> WSClient:
    return request.app.ws_client
