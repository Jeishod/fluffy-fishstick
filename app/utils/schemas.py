import decimal
from datetime import datetime

import orjson
from pydantic import BaseModel

from app.utils.enums import ExampleSymbols, TradeSide, TradeStatus, TradeType, TriggerPeriods


class TimestampMixin(BaseModel):
    class Config:
        json_encoders = {
            # datetime: lambda v: int(v.timestamp()),
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }


class OrdersRequestParams(BaseModel):
    status: TradeStatus = TradeStatus.DONE
    symbol: str | None = None
    side: TradeSide | None = None
    type: TradeType | None = None
    tradeType: TradeType = TradeType.TRADE
    startAt: int | None = None
    endAt: int | None = None


class ParsedWSMessage(TimestampMixin):
    symbol: str  # "PEPE-USDT"
    side: TradeSide  # "sell"
    size: decimal.Decimal  # "53260869.5652"
    time: datetime  # "1683997968318000000"

    class Config:
        json_loads = orjson.loads
        json_dumps = orjson.dumps


class KucoinWSMessageData(TimestampMixin):
    makerOrderId: str  # "645fc50f36bfb50001b8d937"
    price: decimal.Decimal  # "0.000001834"
    sequence: int  # "1199198515234817"
    side: TradeSide  # "sell"
    size: decimal.Decimal  # "53260869.5652"
    symbol: str  # "PEPE-USDT"
    takerOrderId: str  # "645fc51038560f0001bdea9a"
    time: datetime  # "1683997968318000000"
    tradeId: int  # "1199198515234817"
    type: str  # "match"

    class Config:
        json_loads = orjson.loads
        json_dumps = orjson.dumps


class KucoinWSMessage(TimestampMixin):
    id: str | None = None  # "cc4d61b7-7cf3-407c-9b26-6d5eca2136d2", "hU5L6O8bbs"
    type: str | None = None  # "message", "ack", "welcome"
    topic: str | None = None  # "/market/match:PEPE-USDT"
    data: KucoinWSMessageData | None = None


class AddTriggerRequestSchema(BaseModel):
    from_symbol: str = ExampleSymbols.PEPE
    to_symbol: str = ExampleSymbols.USDT

    min_value_usdt: float = "0.0"
    max_value_usdt: float = "100.0"

    transactions_max_count: int = 10

    side: TradeSide = TradeSide.BOTH
    period_seconds: TriggerPeriods = TriggerPeriods.SET_3_MINUTES


class CachedTriggerSchema(TimestampMixin):
    price_usdt: str
    min_value_usdt: float
    max_value_usdt: float
    transactions_max_count: int
    period_seconds: TriggerPeriods
    side: TradeSide
    is_notified: bool = False


class SingleTriggerSchema(TimestampMixin):
    from_symbol: str
    to_symbol: str

    min_value_usdt: float
    max_value_usdt: float

    transactions_max_count: int

    side: TradeSide | None
    period_seconds: TriggerPeriods
    started_at: datetime

    class Config:
        orm_mode = True


class GetSingleTriggerSchema(SingleTriggerSchema):
    transactions_count: int | None
    price_usdt: float | None
    current_count: int | None


class TriggerExistsResponseSchema(BaseModel):
    exists: bool
