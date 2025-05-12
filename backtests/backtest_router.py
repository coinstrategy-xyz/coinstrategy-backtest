import asyncio
from fastapi import APIRouter
from klines.kline_model import Kline
from strategies import rsi_ema_strategy
from pairs.pair_model import Pair
from strategies.strategy_model import Strategy

router = APIRouter(prefix="/back-tests", tags=["Backtests"])
semaphore = asyncio.Semaphore(1)  # Chỉ cho phép tối đa 5 task chạy cùng lúc


@router.get("/")
async def backtest_all():
    pairs = await Pair.find().to_list()
    # intervals = ["15m", "1h", "4h"]
    intervals = ["5m"]

    tasks = []

    for pair in pairs:
        for interval in intervals:
            tasks.append(run_with_semaphore(pair.symbol, interval))

    results = await asyncio.gather(*tasks)
    return {"status": "completed", "count": len([r for r in results if r is not None])}


async def run_with_semaphore(symbol: str, interval: str):
    async with semaphore:
        return await run_backtest(symbol, interval)


async def run_backtest(symbol: str, interval: str):
    klines = await Kline.find(
        Kline.symbol == symbol,
        Kline.interval == interval,
    ).sort(-Kline.openTime).to_list()

    print(f"Fetched {len(klines)} klines for {symbol} at interval {interval}")
    if not klines:
        print(f"No klines found for {symbol} at interval {interval}")
        return None

    return await rsi_ema_strategy.rsi_ema_strategy(klines, symbol, interval)
