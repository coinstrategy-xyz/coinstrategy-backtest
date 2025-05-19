import asyncio
from fastapi import APIRouter, Query
from klines.kline_model import Kline
from strategies import bollinger_breakout_strategy, macd_crossover_volume_spike, rsi_ema_strategy
from pairs.pair_model import Pair
from strategies.strategy_model import Strategy

router = APIRouter(prefix="/back-tests", tags=["Backtests"])
semaphore = asyncio.Semaphore(1)  # Chỉ cho phép tối đa 5 task chạy cùng lúc


@router.get("/")
async def backtest_all(strategySlug: str = Query(..., description="Slug của chiến lược, ví dụ: 'rsi-ema'")):
    pairs = await Pair.find().to_list()
    # intervals = ["15m", "1h", "4h"]
    pairs = ["BTCUSDT"]
    intervals = ["1h"]

    tasks = []

    for pair in pairs:
        for interval in intervals:
            tasks.append(run_with_semaphore(
                pair, interval, strategySlug))

    results = await asyncio.gather(*tasks)
    return {"status": "completed", "count": len([r for r in results if r is not None])}


async def run_with_semaphore(symbol: str, interval: str, strategySlug: str):
    async with semaphore:
        return await run_backtest(symbol, interval, strategySlug)


async def run_backtest(symbol: str, interval: str, strategySlug: str):
    klines = await Kline.find(
        Kline.symbol == symbol,
        Kline.interval == interval,
    ).sort(-Kline.openTime).to_list()

    print(f"Fetched {len(klines)} klines for {symbol} at interval {interval}")
    if not klines:
        print(f"No klines found for {symbol} at interval {interval}")
        return None
    if strategySlug == "RSI-EMA":
        return await rsi_ema_strategy.rsi_ema_strategy(klines, symbol, interval)
    elif strategySlug == "MACD-VolumeSpike":
        return await macd_crossover_volume_spike.macd_crossover_volume_spike(klines, symbol, interval)
    elif strategySlug == "BollingerBreakout":
        return await bollinger_breakout_strategy.bollinger_breakout_strategy(klines, symbol, interval)
