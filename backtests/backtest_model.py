from beanie import Document
from pydantic import Field
from typing import Literal, Optional
from datetime import datetime


class Backtest(Document):
    strategyName: str = Field(...,
                              description="Name of the strategy, e.g. EMA-Crossover")
    symbol: str = Field(..., description="Trading pair symbol, e.g. BTCUSDT")
    interval: str = Field(..., description="Interval, e.g. 1h")
    entryPrice: float = Field(..., description="Entry price")
    entryTime: datetime = Field(...,
                                description="Entry time in ISO format")
    stopLossPrice: float = Field(...,
                                 description="Stop loss price")
    stopLossPercent: float = Field(...,
                                   description="Stop loss percentage")
    takeProfitPrice: float = Field(...,
                                   description="Take profit price")
    takeProfitPercent: float = Field(...,
                                     description="Take profit percentage")
    exitTime: datetime = Field(...,
                               description="Exit time in ISO format")
    resultPct: float = Field(...,
                             description="Result percentage of the trade")

    side: Literal["long",
                  "short"] = Field(..., description="Trade side: long or short")
    status: Literal["win",
                    "loss", "breakeven"] = Field(..., description="Trade result status")
    atr: float = Field(...,
                       description="Average True Range (ATR) at the time of entry")
    rsi: Optional[float] = Field(default=None,
                                 description="Relative Strength Index (RSI) at the time of entry")
    atrMultiplier: float = Field(...,
                                 description="ATR multiplier used for take profit calculation")
    rrRatio: float = Field(...,
                           description="Risk-reward ratio used for trade")

    class Settings:
        name = "backtests"
