import json
from decimal import Decimal

import httpx
import websockets
from loguru import logger as LOGGER
from websockets import WebSocketClientProtocol

from app.utils.enums import Symbols
from app.utils.helpers import gen_request_id
from app.utils.schemas import KucoinWSMessage, KucoinWSMessageData


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

    def set_ws_uri(self) -> None:
        if not self.token:
            self.set_ws_token()
        connection_id = gen_request_id()
        self.uri = f"{self.ws_api_url}?token={self.token}&[connectId={connection_id}]"

    async def connect(self) -> None:
        if not self.uri:
            self.set_ws_uri()
        self.websocket = await websockets.connect(uri=self.uri)

    @staticmethod
    def get_subscription_message(from_symbol: Symbols, to_symbol: Symbols, subscription: bool = True) -> str:
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

    async def subscribe(self, from_symbol: Symbols = Symbols.GENS, to_symbol: Symbols = Symbols.USDT) -> None:
        if not self.websocket:
            await self.connect()

        subscription_message = self.get_subscription_message(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
        )
        await self.websocket.send(message=subscription_message)
        LOGGER.debug(f"[WS CLIENT] SUBSCRIPTION COMPLETED FOR PAIR: {from_symbol}-{to_symbol}")

    async def unsubscribe(self, from_symbol: Symbols = Symbols.GENS, to_symbol: Symbols = Symbols.USDT) -> None:
        if not self.websocket:
            await self.connect()

        subscription_message = self.get_subscription_message(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            subscription=False,
        )
        await self.websocket.send(message=subscription_message)
        LOGGER.debug(f"[WS CLIENT] SUBSCRIPTION CANCELLED FOR PAIR: {from_symbol}-{to_symbol}")

    async def start(self):
        try:
            if not self.websocket:
                await self.connect()

            async for message in self.websocket:
                await self.process_message(message=message)

        except (KeyboardInterrupt, Exception):
            await self.stop()

    async def stop(self):
        if not self.websocket:
            return
        LOGGER.warning("[WS CLIENT] Closing...")
        await self.websocket.close()

    async def process_message(self, message: str | bytes) -> None:
        parsed_message = KucoinWSMessage.parse_raw(message)
        if parsed_message.type == "welcome":
            LOGGER.debug(f"[WS CLIENT] Websocket accepted: {message}")
            return
        if parsed_message.type == "ack":
            LOGGER.debug(f"[WS CLIENT] Server confirmed {message}")
            return
        if parsed_message.type == "message":
            await self.process_data(data=parsed_message.data)

    async def process_data(self, data: KucoinWSMessageData) -> None:
        """
        # TODO: update
        0. use `cache` instance
        1. get symbols
        2. get cached_trigger from cache
        2. get transaction_value in USDT from cached_trigger for from_symbol
        3. compare transaction_value with trigger min_val and max_val
        4. add +1 to transactions_max_count
        """
        from_symbol, to_symbol = data.symbol.split("-")
        summ = round(number=(data.price * data.size), ndigits=4)

        min_value = 300
        max_value = 1000

        if min_value < summ < max_value:
            # ADD LOGS WHILE DEBUG
            log_message = self.make_log_string(
                side=data.side, size=data.size, summ=summ, from_symbol=from_symbol, to_symbol=to_symbol
            )
            LOGGER.debug(log_message)

    @staticmethod
    def make_log_string(side: str, size: Decimal, summ: int, from_symbol: str, to_symbol: str) -> str:
        operation = "BUY <<" if side == "buy" else ">> SELL"
        operation_size = round(number=size, ndigits=4)
        event_info = f"{operation_size: >16} {from_symbol}\tfor\t{summ: >12} {to_symbol}"
        log_message = f"[WS CLIENT] {operation: ^7} {event_info}"
        return log_message
