from typing import Dict, List

import pandas as pd

from backtests.backtest_model import Backtest
from helpers.indicator import calculate_atr, calculate_ema, calculate_rsi, compute_trend_4h


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

    df.to_excel(f"{symbol}_{interval}_debug.xlsx", engine='openpyxl')

    add_signals(df, rsi_threshold)

    trades = generate_trades(df, symbol, interval, rr_ratio)

    if trades:
        await Backtest.insert_many(trades)

    return summarize_results(trades)


def prepare_dataframe(candles: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame([{
        "openTime": k.openTime,
        "open": k.open,
        "high": k.high,
        "low": k.low,
        "close": k.close,
        "volume": k.volume,
        "closeTime": k.closeTime
    } for k in candles])
    df["timestamp"] = pd.to_datetime(df["openTime"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()
    return df


def add_indicators(df: pd.DataFrame, rsi_period: int, ema_period: int, atr_period: int):
    df["rsi"] = calculate_rsi(df, window=rsi_period)
    df["ema"] = calculate_ema(df, window=ema_period)
    df["atr"] = calculate_atr(df, period=atr_period)


def add_signals(df: pd.DataFrame, rsi_threshold: float):
    df["signal_long"] = (
        (df["rsi"] < rsi_threshold) &
        (df["close"] > df["ema"]) &
        (df["trend_4h"] == True)
    )

    df["signal_short"] = (
        (df["rsi"] > (100 - rsi_threshold)) &
        (df["close"] < df["ema"]) &
        (df["trend_4h"] == False)
    )


def generate_trades(df: pd.DataFrame, symbol: str, interval: str, rr_ratio: float) -> List[Backtest]:
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
            trades.append(simulate_trade(
                df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="long"
            ))
        elif row["signal_short"]:
            trades.append(simulate_trade(
                df, i, symbol, interval, entry_time, entry_price, atr, rr_ratio, side="short"
            ))

    return [t for t in trades if t]


def simulate_trade(df, start_idx, symbol, interval, entry_time, entry_price, atr, rr_ratio, side: str):
    atr_multiplier = 6
    risk = atr * atr_multiplier
    reward = risk * rr_ratio

    if side == "long":
        sl = entry_price - risk
        tp = entry_price + reward
        sl_pct = risk / entry_price
        tp_pct = reward / entry_price
    else:
        sl = entry_price + risk
        tp = entry_price - reward
        sl_pct = risk / entry_price
        tp_pct = reward / entry_price

    for j in range(start_idx + 1, len(df)):
        row = df.iloc[j]
        exit_time = row.name
        high, low = row["high"], row["low"]

        if side == "long":
            if low <= sl:
                return Backtest(
                    strategyName="RSI-EMA", symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=-sl_pct,
                    side="long", status="loss", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier
                )
            elif high >= tp:
                return Backtest(
                    strategyName="RSI-EMA", symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=tp_pct,
                    side="long", status="win", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier
                )
        else:
            if high >= sl:
                return Backtest(
                    strategyName="RSI-EMA", symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=-sl_pct,
                    side="short", status="loss", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier
                )
            elif low <= tp:
                return Backtest(
                    strategyName="RSI-EMA", symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=tp_pct,
                    side="short", status="win", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier
                )
    return None


def summarize_results(trades: List[Backtest]) -> Dict:
    total_return = sum(t.result_pct for t in trades)
    win_rate = sum(1 for t in trades if t.result_pct > 0) / \
        len(trades) if trades else 0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "total_return_pct": round(total_return * 100, 2),
    }


def align_trend_to_lower_tf(df_lower: pd.DataFrame, df_higher: pd.DataFrame) -> pd.Series:
    df_higher = df_higher[["trend"]].copy()
    df_higher.index.name = "timestamp"
    return df_lower.index.to_series().apply(
        lambda ts: df_higher[df_higher.index <= ts].iloc[-1]["trend"]
        if not df_higher[df_higher.index <= ts].empty else None
    )
