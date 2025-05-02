from enum import Enum
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KlineInterval(str, Enum):
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
        name = "klines"  # collection name
        use_state_management = True  # like aggregate root
        validate_on_save = True
