from typing import Dict, List

import pandas as pd

from backtests.backtest_model import Backtest
from helpers.indicator import add_bollinger_indicators, compute_trend_4h
from helpers.trade import align_trend_to_lower_tf, prepare_dataframe, simulate_trade, summarize_results
from strategies.strategy_model import Strategy
from klines.kline_model import Kline


async def bollinger_breakout_strategy(
    candles: List[Dict],
    symbol: str,
    interval: str,
    atr_period: int = 14,
    bb_window: int = 20,
    stddev: float = 2.0,
) -> Dict:
    df = prepare_dataframe(candles)
    df = add_bollinger_indicators(df, window=bb_window, stddev=stddev)

    if interval in ["5m", "15m", "1h"]:
        klines_4h_docs = await Kline.find(
            Kline.symbol == symbol, Kline.interval == "4h"
        ).sort(-Kline.openTime).to_list()

        klines_4h = [k.model_dump(exclude={"id"}) for k in klines_4h_docs]
        df_4h = prepare_dataframe(klines_4h)
        df_4h = compute_trend_4h(df_4h)
        df["trend_4h"] = align_trend_to_lower_tf(df, df_4h)
    else:
        df["trend_4h"] = True

    df["signal_long"] = (
        (df["close"] > df["bb_upper"]) &
        (df["volume_spike"]) &
        (df["trend_4h"] == True) &
        (df["atr_ok"])
    )

    df["signal_short"] = (
        (df["close"] < df["bb_lower"]) &
        (df["volume_spike"]) &
        (df["trend_4h"] == False) &
        (df["atr_ok"])
    )

    rr_ratios = [1.5, 2.0, 2.5, 3.0]
    atr_multipliers = [2.0, 2.5, 3.0, 4.0]

    for rr_ratio in rr_ratios:
        for atr_multiplier in atr_multipliers:
            strategy = await Strategy.find_one(
                Strategy.name == "BollingerBreakout",
                Strategy.symbol == symbol,
                Strategy.interval == interval,
                Strategy.rrRatio == rr_ratio,
                Strategy.atrMultiplier == atr_multiplier,
            )
            if strategy:
                print(
                    f"Strategy exists for {symbol} {interval} rr {rr_ratio} atr {atr_multiplier}")
                continue

            trades = await bollinger_generate_trades(df, symbol, interval, rr_ratio, atr_multiplier)
            if trades:
                await Backtest.insert_many(trades)
                result = summarize_results(trades, rr_ratio)
                await Strategy.insert(Strategy(
                    name="BollingerBreakout",
                    symbol=symbol,
                    interval=interval,
                    totalTrades=len(trades),
                    winRate=result["win_rate"],
                    totalReturnPct=result["total_return_pct"],
                    maxDrawdownPct=result["max_drawdown_pct"],
                    finalBalance=result["final_balance"],
                    avgHoursPerTrade=result["avg_hours_per_trade"],
                    rrRatio=rr_ratio,
                    atrMultiplier=atr_multiplier,
                    expectancy=result["expectancy"],
                    recoveryFactor=result["recovery_factor"],
                ))


async def bollinger_generate_trades(df: pd.DataFrame, symbol: str, interval: str, rr_ratio: float, atr_multiplier: float) -> List[Backtest]:
    trades = []

    for i in range(len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i + 1]
        atr = next_row["atr"]

        if pd.isna(atr) or atr == 0:
            continue

        entry_price = next_row["open"]
        entry_time = next_row.name

        if row["signal_long"]:
            trade = await simulate_trade("BollingerBreakout", df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, "long", atr_multiplier)
            if trade:
                trades.append(trade)
        elif row["signal_short"]:
            trade = await simulate_trade("BollingerBreakout", df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, "short", atr_multiplier)
            if trade:
                trades.append(trade)

    return trades
