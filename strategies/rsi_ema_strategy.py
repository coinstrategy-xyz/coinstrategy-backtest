from typing import Dict, List

import pandas as pd

from backtests.backtest_model import Backtest
from helpers.indicator import compute_trend_4h
from helpers.trade import add_indicators, align_trend_to_lower_tf, prepare_dataframe, simulate_trade, summarize_results


async def rsi_ema_strategy(
    candles: List[Dict],
    symbol: str,
    interval: str,
    rsi_period: int = 14,
    ema_period: int = 200,
    atr_period: int = 14,
    rsi_threshold: float = 30,
    rr_ratio: float = 2.0,
) -> Dict:
    df = prepare_dataframe(candles)
    add_indicators(df, rsi_period, ema_period, atr_period)

    if interval in ["15m", "1h"]:
        from klines.kline_model import Kline

        klines_4h = await Kline.find(
            Kline.symbol == symbol, Kline.interval == "4h"
        ).sort(-Kline.openTime).to_list()

        df_4h = prepare_dataframe(klines_4h)
        df_4h = compute_trend_4h(df_4h, ema_period)
        df["trend_4h"] = align_trend_to_lower_tf(df, df_4h)
    else:
        df["trend_4h"] = True

    # df.to_excel(f"{symbol}_{interval}_debug.xlsx", engine='openpyxl')

    rsi_ema_add_signals(df, rsi_threshold)

    trades = rsi_ema_generate_trades(df, symbol, interval, rr_ratio)

    if trades:
        await Backtest.insert_many(trades)

    return summarize_results(trades)


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


def rsi_ema_generate_trades(df: pd.DataFrame, symbol: str, interval: str, rr_ratio: float) -> List[Backtest]:
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
            trades.append(simulate_trade("RSI-EMA",
                                         df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="long"
                                         ))
        elif row["signal_short"]:
            trades.append(simulate_trade("RSI-EMA",
                                         df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="short"
                                         ))

    return [t for t in trades if t]
