from enum import IntEnum, StrEnum


class RequestMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ExampleSymbols(StrEnum):
    PEPE = "PEPE"
    BTC = "BTC"
    USDT = "USDT"
    TON = "TON"
    GENS = "GENS"
    ETH = "ETH"


class TriggerPeriods(IntEnum):
    SET_1_MINUTE = 60
    SET_3_MINUTES = 180
    SET_5_MINUTES = 300
    SET_10_MINUTES = 600


class TradeType(StrEnum):
    # Spot Trading(TRADE as default)
    TRADE = "TRADE"
    # Cross Margin Trading
    MARGIN_TRADE = "MARGIN_TRADE"
    # Isolated Margin Trading
    MARGIN_ISOLATED_TRADE = "MARGIN_ISOLATED_TRADE"


class CandleType(StrEnum):
    GET_1_MIN = "1min"
    GET_3_MIN = "3min"
    GET_5_MIN = "5min"
    GET_15_MIN = "15min"
    GET_30_MIN = "30min"
    GET_1_HOUR = "1hour"
    GET_2_HOURS = "2hour"
    GET_4_HOURS = "4hour"
    GET_6_HOURS = "6hour"
    GET_8_HOURS = "8hour"
    GET_12_HOURS = "12hour"
    GET_1_DAY = "1day"
    GET_1_WEEK = "1week"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrdersCount(StrEnum):
    GET_20 = "20"
    GET_100 = "100"


class TradeStatus(StrEnum):
    ACTIVE = "active"
    DONE = "done"


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"
    LIMIT_STOP = "limit_stop"
    MARKET_STOP = "market_stop"
