from enum import Enum
from beanie import Document
from pydantic import Field


class KlineInterval(str, Enum):
    FIVE_MINUTES = '5m'
    FIFTEEN_MINUTES = '15m'
    ONE_HOUR = '1h'
    FOUR_HOURS = '4h'
    ONE_DAY = '1d'


class Kline(Document):
    interval: KlineInterval = Field(..., description="Interval of the Kline")
    symbol: str = Field(..., description="Symbol name")
    openTime: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    closeTime: float

    class Settings:
        name = "klines"
        use_state_management = True
        validate_on_save = True
