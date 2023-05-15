from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status

from app.clients.kucoin_api import APIClient
from app.utils.dependencies import get_api_client
from app.utils.enums import CandleType, OrdersCount, Symbols


market_router = APIRouter(prefix="/market")


@market_router.get("/list", status_code=status.HTTP_200_OK)
async def get_markets(
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the transaction currency for the entire trading market.
    """
    response = await client.get_markets()
    return response.json()


@market_router.get("/symbols", status_code=status.HTTP_200_OK)
async def get_symbols(
    client: APIClient = Depends(get_api_client),
    market: str | None = None,
):
    """
    Request via this endpoint to get a list of available currency pairs for trading.
    """
    response = await client.get_symbols(market=market)
    return response.json()


@market_router.get("/currencies", status_code=status.HTTP_200_OK)
async def get_currencies(
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the currency list.
    (Not all currencies currently can be used for trading)
    """
    response = await client.get_currencies()
    return response.json()


@market_router.get("/stats", status_code=status.HTTP_200_OK)
async def get_stats(
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the statistics of the specified ticker in the last 24 hours.
    """
    response = await client.get_stats(from_symbol=from_symbol, to_symbol=to_symbol)
    return response.json()


@market_router.get("/tickers", status_code=status.HTTP_200_OK)
async def get_all_tickers(
    client: APIClient = Depends(get_api_client),
):
    """
    Request market tickers for all the trading pairs in the market (including 24h volume).

    On the rare occasion that we will change the currency name, if you still want the changed symbol name,
    you can use the symbolName field instead of the symbol field via “Get all tickers” endpoint.
    """
    response = await client.get_all_tickers()
    return response.json()


@market_router.get("/ticker", status_code=status.HTTP_200_OK)
async def get_ticker(
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get Level 1 Market Data.

    The returned value includes the best bid price and size,
    the best ask price and size as well as the last traded price and the last traded size.
    """
    response = await client.get_ticker(from_symbol=from_symbol, to_symbol=to_symbol)
    return response.json()


@market_router.get("/order_book/part", status_code=status.HTTP_200_OK)
async def get_order_book_part(
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    count: OrdersCount = OrdersCount.GET_20,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get a list of open orders for a symbol.

    Level-2 order book includes all bids and asks (aggregated by price).
    This level returns only one size for each active price (as if there was only a single order for that price).
    """
    response = await client.get_order_book(from_symbol=from_symbol, to_symbol=to_symbol, count=count)
    return response.json()


@market_router.get("/order_book/full", status_code=status.HTTP_200_OK, deprecated=True)
async def get_order_book_full(
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the order book of the specified symbol.

    Level 2 order book includes all bids and asks (aggregated by price).
    This level returns only one aggregated size for each price (as if there was only one single order for that price).

    This API will return data with full depth.

    It is generally used by professional traders because it uses more server resources and traffic,
    and we have strict access frequency control.
    """
    response = await client.get_order_book_full(from_symbol=from_symbol, to_symbol=to_symbol)
    return response.json()


@market_router.get("/histories", status_code=status.HTTP_200_OK)
async def get_trade_histories(
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the trade history of the specified symbol.
    """
    response = await client.get_histories(from_symbol=from_symbol, to_symbol=to_symbol)
    return response


@market_router.get("/candles", status_code=status.HTTP_200_OK)
async def get_klines(
    from_time: datetime = (datetime.utcnow() - timedelta(hours=2)),
    to_time: datetime = datetime.utcnow(),
    from_symbol: Symbols = Symbols.GENS,
    to_symbol: Symbols = Symbols.USDT,
    candle_type: CandleType = CandleType.GET_3_MIN,
    client: APIClient = Depends(get_api_client),
):
    """
    Request via this endpoint to get the kline of the specified symbol.
    Data are returned in grouped buckets based on requested type.
    """
    response = await client.get_klines(
        from_symbol=from_symbol,
        to_symbol=to_symbol,
        candle_type=candle_type,
        from_time=from_time,
        to_time=to_time,
    )
    return response
