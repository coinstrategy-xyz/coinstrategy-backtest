from fastapi import APIRouter, Query
from typing import List
from klines.kline_model import Kline
from strategies import rsi_ema_strategy

router = APIRouter(prefix="/klines", tags=["Klines"])


@router.get("/")
async def get_klines(
    symbol: str = Query(..., description="Symbol, e.g. BTCUSDT"),
    interval: str = Query(..., description="Interval, e.g. 1h"),
):
    klines = await Kline.find(
        Kline.symbol == symbol,
        Kline.interval == interval,
    ).sort(-Kline.openTime).to_list()

    print(f"Fetched {len(klines)} klines for {symbol} at interval {interval}")
    return rsi_ema_strategy.rsi_ema_strategy(klines)
