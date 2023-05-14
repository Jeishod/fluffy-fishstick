import datetime
import json

from fastapi import HTTPException, status
from httpx import AsyncClient, Response
from loguru import logger as LOGGER

from app.utils.enums import (
    CandleType,
    OrdersCount,
    OrderType,
    RequestMethod,
    Symbols,
    TradeSide,
    TradeStatus,
    TradeType,
)
from app.utils.helpers import gen_hashed_string, gen_request_id, get_sign_string


class KucoinClient:
    api_key: str
    api_secret: str
    api_passphrase: str
    api_url: str

    def __init__(self, api_key: str, api_secret: str, api_passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.api_url = "https://api.kucoin.com"

    def build_headers(self, method: RequestMethod, endpoint: str, v2: bool) -> dict:
        api_passphrase = self.api_passphrase

        timestamp, sign_string = get_sign_string(method=method, endpoint=endpoint)
        signature = gen_hashed_string(api_secret=self.api_secret, message=sign_string)
        headers = {
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": str(timestamp),
            "KC-API-KEY": self.api_key,
        }

        if v2:
            passphrase = gen_hashed_string(api_secret=self.api_secret, message=api_passphrase)
            headers.update(
                {
                    "KC-API-PASSPHRASE": passphrase,
                    "KC-API-KEY-VERSION": "2",
                }
            )
        else:
            passphrase = self.api_passphrase
            headers.update(
                {
                    "KC-API-PASSPHRASE": passphrase,
                }
            )
        return headers

    async def send_request(
        self,
        method: RequestMethod,
        endpoint: str,
        request_id: str,
        json: dict | None = None,
        params: dict | None = None,
        v2: bool = False,
    ) -> Response:
        headers = self.build_headers(method=method, endpoint=endpoint, v2=v2)
        url = self.api_url + endpoint
        LOGGER.debug(f"[API CLIENT] request_id: {request_id} | {method} | url: {url}")
        async with AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=600,
                headers=headers,
            )
            if response.status_code != status.HTTP_200_OK:
                LOGGER.error(f"request_id {request_id} failed | status code: {response.status_code}")
                LOGGER.error(f"Response: {response.json()}")
                raise HTTPException(status_code=response.status_code, detail=response.json())
            LOGGER.debug(f"[API CLIENT] response: {response.json()}")
            return response

    async def get_accounts(self):
        request_id = gen_request_id()
        endpoint = "/api/v1/accounts"
        response = await self.send_request(method=RequestMethod.GET, endpoint=endpoint, request_id=request_id, v2=False)
        return response

    async def get_orders(
        self,
        status: TradeStatus | None = None,
        symbol: Symbols | None = None,
        side: TradeSide | None = None,
        type: OrderType | None = None,
        trade_type: TradeType | None = TradeType.MARGIN_ISOLATED_TRADE,
        current_page: int = 1,
        page_size: int = 50,
    ):
        request_id = gen_request_id()
        endpoint = "/api/v1/orders"
        params = {
            "currentPage": current_page,
            "pageSize": page_size,
            "status": status,
            "symbol": symbol,
            "side": side,
            "type": type,
            "trade_type": trade_type,
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            params=params,
            endpoint=endpoint,
            request_id=request_id,
            v2=False,
        )
        return response

    async def get_markets(self):
        request_id = gen_request_id()
        endpoint = "/api/v1/markets"
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            v2=True,
        )
        return response

    async def get_symbols(self, market: str | None = None):
        request_id = gen_request_id()
        endpoint = "/api/v2/symbols"
        params = {
            "market": market,
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )
        return response

    async def get_stats(self, from_symbol: Symbols, to_symbol: Symbols):
        request_id = gen_request_id()
        endpoint = "/api/v1/market/stats"
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            params=params,
            request_id=request_id,
            v2=True,
        )
        return response

    async def get_all_tickers(self):
        request_id = gen_request_id()
        endpoint = "/api/v1/market/allTickers"
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            v2=True,
        )
        return response

    async def get_ticker(self, from_symbol: Symbols, to_symbol: Symbols):
        request_id = gen_request_id()
        endpoint = "/api/v1/market/orderbook/level1"
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )
        return response

    async def get_order_book(self, from_symbol: Symbols, to_symbol: Symbols, count: OrdersCount):
        request_id = gen_request_id()
        endpoint = f"/api/v1/market/orderbook/level2_{count}"
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )
        return response

    async def get_order_book_full(self, from_symbol: Symbols, to_symbol: Symbols):
        request_id = gen_request_id()
        endpoint = "/api/v3/market/orderbook/level2"
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )
        return response

    async def get_histories(self, from_symbol: Symbols, to_symbol: Symbols):
        request_id = gen_request_id()
        endpoint = "/api/v1/market/histories"
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
        }
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )

        content = response.content
        history_data = json.loads(content)
        for item in history_data["data"]:
            current_time_value = item.get("time")
            counted_time_value = current_time_value / 1_000_000_000
            item["time"] = datetime.datetime.fromtimestamp(counted_time_value)
        return history_data

    async def get_klines(
        self,
        from_symbol: Symbols,
        to_symbol: Symbols,
        candle_type: CandleType,
        from_time: datetime.datetime | None = None,
        to_time: datetime.datetime | None = None,
    ):
        request_id = gen_request_id()
        endpoint = "/api/v1/market/candles"
        start_ts = int(from_time.timestamp()) if from_time else 0
        end_ts = int(to_time.timestamp()) if to_time else 0
        params = {
            "symbol": f"{from_symbol}-{to_symbol}",
            "type": candle_type,
            "startAt": start_ts,
            "endAt": end_ts,
        }
        LOGGER.debug(f"PARAMS: {params}")
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
            v2=True,
        )
        content = response.content
        history_data = json.loads(content)
        result = []
        for item in history_data["data"]:
            result.append(
                {
                    "time": datetime.datetime.fromtimestamp(int(item[0])),
                    "open": item[1],
                    "close": item[2],
                    "high": item[3],
                    "low": item[4],
                    "volume": item[5],
                    "turnover": item[6],
                },
            )
        return result

    async def get_currencies(self):
        request_id = gen_request_id()
        endpoint = "/api/v1/currencies"
        response = await self.send_request(
            method=RequestMethod.GET,
            endpoint=endpoint,
            request_id=request_id,
            v2=True,
        )
        return response

    async def get_ws_token(self) -> str:
        request_id = gen_request_id()
        endpoint = "/api/v1/bullet-public"
        response = await self.send_request(
            method=RequestMethod.POST,
            endpoint=endpoint,
            request_id=request_id,
            v2=True,
        )
        response_json = response.json()
        token = response_json["data"]["token"]
        return token
