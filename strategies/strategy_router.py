import asyncio
from fastapi import APIRouter
from backtests.backtest_model import Backtest
from helpers.trade import summarize_results
from pairs.pair_model import Pair
from strategies.strategy_model import Strategy


router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("/")
async def create_strategies():
    pairs = await Pair.find().to_list()

    atr_multipliers = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    rr_ratios = [1.5, 2.0, 2.5, 3.0]
    strategies = ["RSI-EMA", "MACD-VolumeSpike"]
    intervals = ["5m", "15m", "1h", "4h"]
    for pair in pairs:
        for strategy in strategies:
            for interval in intervals:
                for atr_multiplier in atr_multipliers:
                    for rr_ratio in rr_ratios:
                        exist_strategy = await Strategy.find_one(
                            Strategy.name == strategy,
                            Strategy.symbol == pair.symbol,
                            Strategy.interval == interval,
                            Strategy.atrMultiplier == atr_multiplier,
                            Strategy.rrRatio == rr_ratio,
                        )

                        if exist_strategy:
                            print(f"Strategy {strategy} already exists")
                            continue
                        else:
                            backTests = await Backtest.find(
                                Backtest.symbol == pair.symbol,
                                Backtest.interval == interval,
                                Backtest.atrMultiplier == atr_multiplier,
                                Backtest.rrRatio == rr_ratio,
                                Backtest.strategyName == strategy,
                            ).to_list()

                            if not backTests:
                                print(
                                    f"No backtests found for {pair.symbol} at interval {interval}")
                                continue
                            else:
                                result = summarize_results(backTests, rr_ratio)
                                new_strategy = Strategy(
                                    name=strategy,
                                    symbol=pair.symbol,
                                    interval=interval,
                                    totalTrades=len(backTests),
                                    winRate=result["win_rate"],
                                    totalReturnPct=result["total_return_pct"],
                                    maxDrawdownPct=result["max_drawdown_pct"],
                                    finalBalance=result["final_balance"],
                                    avgHoursPerTrade=result["avg_hours_per_trade"],
                                    rrRatio=rr_ratio,
                                    atrMultiplier=atr_multiplier,
                                    expectancy=result["expectancy"],
                                    recoveryFactor=result["recovery_factor"],
                                )
                                await Strategy.insert(new_strategy)
                                print(
                                    f"Inserted strategy {strategy} for {pair.symbol} at interval {interval}")
