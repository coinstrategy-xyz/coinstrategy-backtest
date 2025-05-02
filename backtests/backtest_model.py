from beanie import Document
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime


class Trade(BaseModel):
    timestamp: datetime
    price: float
    side: Literal["buy", "sell"]
    quantity: float


class Backtest(Document):
    strategy_name: str = Field(...,
                               description="Name of the strategy, e.g. EMA-Crossover")
    symbol: str = Field(..., description="Trading pair symbol, e.g. BTCUSDT")
    interval: str = Field(..., description="Interval, e.g. 1h")
    start_time: datetime = Field(..., description="Backtest start time")
    end_time: datetime = Field(..., description="Backtest end time")
    initial_balance: float = Field(..., description="Initial account balance")
    final_balance: float = Field(..., description="Final account balance")
    trades: List[Trade] = Field(
        default_factory=list, description="List of executed trades")

    class Settings:
        name = "backtests"
