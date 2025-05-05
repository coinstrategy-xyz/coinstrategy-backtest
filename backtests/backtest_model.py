from beanie import Document
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime


class Backtest(Document):
    strategy_name: str = Field(...,
                               description="Name of the strategy, e.g. EMA-Crossover")
    symbol: str = Field(..., description="Trading pair symbol, e.g. BTCUSDT")
    interval: str = Field(..., description="Interval, e.g. 1h")
    entry_price: float = Field(..., description="Entry price")
    entry_time: datetime = Field(...,
                                 description="Entry time in ISO format")
    stop_loss_price: float = Field(...,
                                   description="Stop loss price")
    stop_loss_percent: float = Field(...,
                                     description="Stop loss percentage")
    take_profit_price: float = Field(...,
                                     description="Take profit price")
    take_profit_percent: float = Field(...,
                                       description="Take profit percentage")
    exit_time: datetime = Field(...,
                                description="Exit time in ISO format")
    result_pct: float = Field(...,
                              description="Result percentage of the trade")

    side: Literal["long",
                  "short"] = Field(..., description="Trade side: long or short")
    status: Literal["win",
                    "loss"] = Field(..., description="Trade result status")
    atr: float = Field(...,
                       description="Average True Range (ATR) at the time of entry")
    rsi: float = Field(...,
                       description="Relative Strength Index (RSI) at the time of entry")
    atr_multiplier: float = Field(...,
                                  description="ATR multiplier used for take profit calculation")

    class Settings:
        name = "backtests"
