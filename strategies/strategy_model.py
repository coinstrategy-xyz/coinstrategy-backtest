from beanie import Document
from pydantic import Field

from klines.kline_model import KlineInterval


class Strategy(Document):
    name: str = Field(..., description="Name of the strategy")
    symbol: str = Field(..., description="Symbol name")
    interval: KlineInterval = Field(..., description="Interval of the Kline")
    totalTrades: int = Field(..., description="Total number of trades")
    winRate: float = Field(..., description="Win rate of the strategy")
    totalReturnPct: float = Field(..., description="Total return percentage")
    maxDrawdownPct: float = Field(...,
                                  description="Maximum drawdown percentage")
    finalBalance: float = Field(...,
                                description="Final balance after all trades")
    avgHoursPerTrade: float = Field(...,
                                    description="Average hours per trade")
    rrRatio: float = Field(..., description="Risk-reward ratio")
    atrMultiplier: float = Field(
        ..., description="ATR multiplier used in the strategy")
    expectancy: float = Field(
        ..., description="Expectancy of the strategy based on win rate and risk-reward ratio")
    recoveryFactor: float = Field(
        ..., description="Recovery factor of the strategy based on drawdown and return")

    class Settings:
        name = "strategies"
        use_state_management = True
        validate_on_save = True
