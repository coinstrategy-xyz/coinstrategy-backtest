from typing import Dict, List
import pandas as pd

from backtests.backtest_model import Backtest
from strategies.strategy_model import Strategy
from helpers.trade import (
    align_trend_to_lower_tf,
    prepare_dataframe,
    simulate_trade,
    summarize_results,
)
from helpers.indicator import calculate_macd, calculate_rsi, compute_trend_4h
from klines.kline_model import Kline


async def macd_crossover_volume_spike(
    candles: List[Dict],
    symbol: str,
    interval: str,
    rr_ratios: List[float] = [1.5, 2.0, 2.5, 3.0],
    atr_multipliers: List[float] = [
        2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
) -> Dict:
    df = prepare_dataframe(candles)

    if interval in ["5m", "15m", "1h"]:
        klines_4h_docs = await Kline.find(
            Kline.symbol == symbol,
            Kline.interval == "4h"
        ).sort(-Kline.openTime).to_list()
        klines_4h = [k.model_dump(exclude={"id"}) for k in klines_4h_docs]

        df_4h = prepare_dataframe(klines_4h)
        df_4h = compute_trend_4h(df_4h, ema_period=200)
        df["trend_4h"] = align_trend_to_lower_tf(df, df_4h)
    else:
        df["trend_4h"] = True

    df = add_macd_volume_indicators(df)

    for atr_multiplier in atr_multipliers:
        for rr_ratio in rr_ratios:
            strategy = await Strategy.find_one(
                Strategy.name == "MACD-VolumeSpike",
                Strategy.symbol == symbol,
                Strategy.interval == interval,
                Strategy.rrRatio == rr_ratio,
                Strategy.atrMultiplier == atr_multiplier,
            )
            if strategy:
                print(
                    f"Strategy exists for {symbol} {interval} rr {rr_ratio} atr {atr_multiplier}")
                continue

            trades = await macd_generate_trades(df, symbol, interval, rr_ratio, atr_multiplier)
            if trades:
                await Backtest.insert_many(trades)
                result = summarize_results(trades)
                await Strategy.insert(Strategy(
                    name="MACD-VolumeSpike",
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


def add_macd_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    macd_data = calculate_macd(df)
    df["macd"] = macd_data["macd"]
    df["signal"] = macd_data["signal"]

    df["volume_ma"] = df["volume"].rolling(20).mean()
    df["volume_spike"] = df["volume"] > (1.5 * df["volume_ma"])

    df["macd_cross_up"] = (df["macd"].shift(
        1) < df["signal"].shift(1)) & (df["macd"] > df["signal"])
    df["macd_cross_down"] = (df["macd"].shift(
        1) > df["signal"].shift(1)) & (df["macd"] < df["signal"])

    df["atr"] = df["high"] - df["low"]
    df["atr_ok"] = df["atr"] > (df["close"] * 0.005)

    df["signal_long"] = df["macd_cross_up"] & df["volume_spike"] & (
        df["trend_4h"] == True)
    df["signal_short"] = df["macd_cross_down"] & df["volume_spike"] & (
        df["trend_4h"] == False)

    df["rsi"] = calculate_rsi(df, window=14)

    return df


async def macd_generate_trades(df: pd.DataFrame, symbol: str, interval: str, rr_ratio: float, atr_multiplier: float) -> List[Backtest]:
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
            trade = await simulate_trade("MACD-VolumeSpike", df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, "long", atr_multiplier)
            if trade:
                trades.append(trade)
        elif row["signal_short"]:
            trade = await simulate_trade("MACD-VolumeSpike", df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, "short", atr_multiplier)
            if trade:
                trades.append(trade)

    return trades
