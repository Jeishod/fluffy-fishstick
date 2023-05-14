import ast
import json

import httpx
import websockets
from loguru import logger as LOGGER
from websockets.client import WebSocketClientProtocol

from app.utils.enums import Symbols


class WSClient:
    token: str
    connection_id: str
    uri: str
    websocket: WebSocketClientProtocol | None

    def __init__(self, connection_id: str = "asdasd"):
        self.ws_api_url = "wss://ws-api-spot.kucoin.com"
        self.api_get_token_url = "https://api.kucoin.com/api/v1/bullet-public"
        self.connection_id = connection_id
        self.token = self.get_auth_token()
        self.uri = self.get_ws_uri()
        self.websocket = None

    def get_auth_token(self) -> str:
        response = httpx.post(url=self.api_get_token_url)
        response_json = response.json()
        token = response_json["data"]["token"]
        self.token = token
        return token

    def get_ws_uri(self) -> str:
        uri = f"{self.ws_api_url}?token={self.token}&[connectId={self.connection_id}]"
        return uri

    def get_subscription_message(self, from_symbol: str, to_symbol: str) -> str:
        subscription_message = {
            "id": self.connection_id,
            "type": "subscribe",
            "topic": f"/market/match:{from_symbol}-{to_symbol}",
            "privateChannel": False,
            "response": True,
        }
        return json.dumps(obj=subscription_message)

    async def connect(self) -> None:
        self.websocket = await websockets.connect(uri=self.uri)

    async def subscribe(self, from_symbol: Symbols = Symbols.GENS, to_symbol: Symbols = Symbols.USDT) -> None:
        if not self.websocket:
            await self.connect()

        subscription_message = self.get_subscription_message(from_symbol=from_symbol, to_symbol=to_symbol)
        LOGGER.debug(f"[WSClient] SUBSCRIPTION MESSAGE: {subscription_message}")
        await self.websocket.send(message=subscription_message)
        LOGGER.debug("[WSClient] SUBSCRIPTION COMPLETED")

    async def process_messages(self):
        try:
            if not self.websocket:
                await self.connect()

            async for message in self.websocket:
                dict_message = ast.literal_eval(message)
                _message = json.dumps(dict_message, indent=2, ensure_ascii=False)
                LOGGER.debug(f"[WSClient] Received message:\n{_message}")

        except KeyboardInterrupt:
            await self.websocket.close()
