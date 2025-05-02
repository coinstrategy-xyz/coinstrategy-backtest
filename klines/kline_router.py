from fastapi import APIRouter, Query
from typing import List
from klines.kline_model import Kline

router = APIRouter(prefix="/klines", tags=["Klines"])


@router.get("/", response_model=List[Kline])
async def get_klines(
    symbol: str = Query(..., description="Symbol, e.g. BTCUSDT"),
    interval: str = Query(..., description="Interval, e.g. 1h"),
    limit: int = Query(
        100, le=1000, description="Number of data to return (max 1000)")
):
    return await Kline.find(
        Kline.symbol == symbol,
        Kline.interval == interval,
    ).sort(-Kline.openTime).limit(limit).to_list()
