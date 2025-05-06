from beanie import Document
from pydantic import Field


class Pair(Document):
    symbol: str = Field(..., description="Trading pair symbol, e.g. BTCUSDT")
    exchange: str = Field(..., description="Exchange name, e.g. Binance")

    class Settings:
        name = "pairs"
        use_state_management = True
        validate_on_save = True
