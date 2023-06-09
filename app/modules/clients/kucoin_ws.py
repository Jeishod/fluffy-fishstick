import json

import httpx
import websockets
from loguru import logger as LOGGER
from websockets import WebSocketClientProtocol

from app.utils.enums import ExampleSymbols
from app.utils.helpers import gen_request_id


class WSClient:
    ws_api_url: str
    ws_api_token_url: str
    token: str | None
    uri: str | None
    websocket: WebSocketClientProtocol | None

    def __init__(self):
        self.ws_api_url = "wss://ws-api-spot.kucoin.com"
        self.ws_api_token_url = "https://api.kucoin.com/api/v1/bullet-public"
        self.token = None
        self.uri = None
        self.websocket = None

    def set_ws_token(self) -> None:
        response = httpx.post(url=self.ws_api_token_url)
        response_json = response.json()
        self.token = response_json["data"]["token"]

    def set_ws_uri(self, connection_id: str) -> None:
        if not self.token:
            self.set_ws_token()
        self.uri = f"{self.ws_api_url}?token={self.token}&[connectId={connection_id}]"

    async def connect(self, connection_id: str | None = None) -> None:
        if not connection_id:
            connection_id = gen_request_id()
        if not self.uri:
            self.set_ws_uri(connection_id=connection_id)
        self.websocket = await websockets.connect(uri=self.uri)

    @staticmethod
    def get_subscription_message(from_symbol: str, to_symbol: str, subscription: bool = True) -> str:
        connection_id = gen_request_id()
        request_type = "subscribe" if subscription else "unsubscribe"
        subscription_message = {
            "id": connection_id,
            "type": request_type,
            "topic": f"/market/match:{from_symbol}-{to_symbol}",
            "privateChannel": False,
            "response": True,
        }
        return json.dumps(obj=subscription_message)

    async def subscribe(self, from_symbol: str = ExampleSymbols.GENS, to_symbol: str = ExampleSymbols.USDT) -> None:
        if not self.websocket:
            await self.connect()

        subscription_message = self.get_subscription_message(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
        )
        await self.websocket.send(message=subscription_message)
        LOGGER.debug(f"[WS CLIENT] SUBSCRIPTION COMPLETED FOR PAIR: {from_symbol}-{to_symbol}")

    async def unsubscribe(self, from_symbol: str = ExampleSymbols.GENS, to_symbol: str = ExampleSymbols.USDT) -> None:
        if not self.websocket:
            await self.connect()

        subscription_message = self.get_subscription_message(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            subscription=False,
        )
        await self.websocket.send(message=subscription_message)
        LOGGER.debug(f"[WS CLIENT] SUBSCRIPTION CANCELLED FOR PAIR: {from_symbol}-{to_symbol}")

    async def start(self, connection_id: str):
        if not self.websocket:
            await self.connect(connection_id=connection_id)

    async def stop(self):
        if not self.websocket:
            return
        LOGGER.warning("[WS CLIENT] Closing...")
        await self.websocket.close()
