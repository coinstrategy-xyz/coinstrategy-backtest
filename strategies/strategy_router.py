import asyncio
from fastapi import APIRouter
from backtests.backtest_model import Backtest
from helpers.trade import summarize_results
from pairs.pair_model import Pair
from strategies.strategy_model import Strategy

router = APIRouter(prefix="/strategies", tags=["Strategies"])

semaphore = asyncio.Semaphore(3)


@router.get("/")
async def create_strategies():
    pairs = await Pair.find().to_list()
    atr_multipliers = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    rr_ratios = [1.5, 2.0, 2.5, 3.0]
    strategies = ["RSI-EMA", "MACD-VolumeSpike"]
    intervals = ["5m", "15m", "1h", "4h"]

    tasks = []

    for pair in pairs:
        for strategy_name in strategies:
            for interval in intervals:
                for atr_multiplier in atr_multipliers:
                    for rr_ratio in rr_ratios:
                        tasks.append(run_with_semaphore(
                            pair.symbol, strategy_name, interval, atr_multiplier, rr_ratio))

    results = await asyncio.gather(*tasks)
    return {"status": "completed", "inserted": sum(results)}


async def run_with_semaphore(symbol, strategy_name, interval, atr_multiplier, rr_ratio):
    async with semaphore:
        return await process_strategy(symbol, strategy_name, interval, atr_multiplier, rr_ratio)


async def process_strategy(symbol: str, strategy_name: str, interval: str, atr_multiplier: float, rr_ratio: float):
    exist_strategy = await Strategy.find_one(
        Strategy.name == strategy_name,
        Strategy.symbol == symbol,
        Strategy.interval == interval,
        Strategy.atrMultiplier == atr_multiplier,
        Strategy.rrRatio == rr_ratio,
    )

    if exist_strategy:
        print(
            f"Strategy {strategy_name} already exists for {symbol}-{interval}")
        return 0

    backTests = await Backtest.find(
        Backtest.symbol == symbol,
        Backtest.interval == interval,
        Backtest.atrMultiplier == atr_multiplier,
        Backtest.rrRatio == rr_ratio,
        Backtest.strategyName == strategy_name,
    ).to_list()

    if not backTests:
        print(f"No backtests found for {symbol} at interval {interval}")
        return 0

    result = summarize_results(backTests, rr_ratio)

    new_strategy = Strategy(
        name=strategy_name,
        symbol=symbol,
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
    print(f"Inserted strategy {strategy_name} for {symbol} at {interval}")
    return 1
