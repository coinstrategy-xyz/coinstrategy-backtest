from typing import Dict, List

import pandas as pd

from backtests.backtest_model import Backtest
from helpers.indicator import compute_trend_4h
from helpers.trade import add_indicators, align_trend_to_lower_tf, prepare_dataframe, simulate_trade, summarize_results
from strategies.strategy_model import Strategy
from packages.redis import redis_client
from klines.kline_model import Kline

from datetime import timedelta
import ujson as json


async def rsi_ema_strategy(
    candles: List[Dict],
    symbol: str,
    interval: str,
    rsi_period: int = 14,
    ema_period: int = 200,
    atr_period: int = 14,
    rsi_threshold: float = 30,
) -> Dict:
    df = prepare_dataframe(candles)
    add_indicators(df, rsi_period, ema_period, atr_period)

    if interval in ["5m", "15m", "1h"]:
        cache_key = f"klines_4h:{symbol}"

        # cached_klines = await redis_client.get(cache_key)
        # if cached_klines:
        #     klines_4h = json.loads(cached_klines)
        # else:

        klines_4h_docs = await Kline.find(
            Kline.symbol == symbol, Kline.interval == "4h"
        ).sort(-Kline.openTime).to_list()

        klines_4h = [k.model_dump(exclude={"id"}) for k in klines_4h_docs]

        # await redis_client.setex(cache_key, timedelta(hours=1), json.dumps(klines_4h))

        df_4h = prepare_dataframe(klines_4h)
        df_4h = compute_trend_4h(df_4h, ema_period)
        df["trend_4h"] = align_trend_to_lower_tf(df, df_4h)
    else:
        df["trend_4h"] = True

    # df.to_excel(f"{symbol}_{interval}_debug.xlsx", engine='openpyxl')

    rsi_ema_add_signals(df, rsi_threshold)
    atr_multipliers = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    rr_ratios = [1.5, 2.0, 2.5, 3.0]

    for atr_multiplier in atr_multipliers:
        for rr_ratio in rr_ratios:
            strategy = await Strategy.find_one(
                Strategy.symbol == symbol,
                Strategy.interval == interval,
                Strategy.rrRatio == rr_ratio,
                Strategy.atr_multiplier == atr_multiplier,
            )
            if strategy:
                print(
                    f"Strategy already exists for {symbol} at {interval} with rr_ratio {rr_ratio} and atr_multiplier {atr_multiplier}")
                continue
            else:
                trades = await rsi_ema_generate_trades(
                    df, symbol, interval, rr_ratio, atr_multiplier)

                if trades:
                    await Backtest.insert_many(trades)

                    result = summarize_results(trades)
                    strategy = Strategy(
                        name="RSI-EMA",
                        symbol=symbol,
                        interval=interval,
                        totalTrades=len(trades),
                        winRate=result["win_rate"],
                        totalReturnPct=result["total_return_pct"],
                        maxDrawdownPct=result["max_drawdown_pct"],
                        finalBalance=result["final_balance"],
                        avgHoursPerTrade=result["avg_hours_per_trade"],
                        rrRatio=rr_ratio,
                        atr_multiplier=atr_multiplier,
                    )
                    await Strategy.insert(strategy)


def rsi_ema_add_signals(df: pd.DataFrame, rsi_threshold: float):
    df["signal_long"] = (
        (df["rsi"] < rsi_threshold) &
        (df["close"] > df["ema"]) &
        (df["trend_4h"] == True) &
        (df["volume"] > df["volume_ma"]) &
        (df["atr_ok"]) &
        (df["ema50"] > df["ema200"])
    )

    df["signal_short"] = (
        (df["rsi"] > (100 - rsi_threshold)) &
        (df["close"] < df["ema"]) &
        (df["trend_4h"] == False) &
        (df["volume"] > df["volume_ma"]) &
        (df["atr_ok"]) &
        (df["ema50"] < df["ema200"])
    )


async def rsi_ema_generate_trades(df: pd.DataFrame, symbol: str, interval: str, rr_ratio: float, atr_multiplier: float) -> List[Backtest]:
    trades = []

    for i in range(len(df) - 1):
        if i + 1 >= len(df):
            continue

        row = df.iloc[i]
        next_row = df.iloc[i + 1]
        atr = next_row["atr"]

        if pd.isna(atr) or atr == 0:
            continue

        entry_price = next_row["open"]
        entry_time = next_row.name

        if row["signal_long"]:
            trades.append(await simulate_trade("RSI-EMA",
                                               df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="long", atr_multiplier=atr_multiplier
                                               ))
        elif row["signal_short"]:
            trades.append(await simulate_trade("RSI-EMA",
                                               df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="short", atr_multiplier=atr_multiplier
                                               ))

    return [t for t in trades if t]
