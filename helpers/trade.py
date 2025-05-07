from typing import Dict, List
import pandas as pd
from backtests.backtest_model import Backtest
from helpers.indicator import calculate_atr, calculate_ema, calculate_rsi


def add_indicators(df: pd.DataFrame, rsi_period: int, ema_period: int, atr_period: int):
    df["rsi"] = calculate_rsi(df, window=rsi_period)

    df["ema"] = calculate_ema(df, window=ema_period)
    df["ema50"] = calculate_ema(df, window=50)
    df["ema200"] = calculate_ema(df, window=200)

    df["atr"] = calculate_atr(df, period=atr_period)
    df["atr_ok"] = df["atr"] > (df["close"] * 0.005)

    df["volume_ma"] = df["volume"].rolling(20).mean()


def prepare_dataframe(candles):
    if not candles:
        return pd.DataFrame()

    if isinstance(candles[0], dict):
        df = pd.DataFrame(candles)
    else:
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
    df.sort_index(inplace=True)
    return df


def simulate_trade(strategy_name, df, start_idx, symbol, interval, entry_time, entry_price, atr, rr_ratio, side: str, atr_multiplier: float = 2.0):
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

        if exit_time <= entry_time:
            continue

        high, low = row["high"], row["low"]

        if side == "long":
            if low <= sl:
                return Backtest(
                    strategyName=strategy_name, symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=-sl_pct,
                    side="long", status="loss", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier, rrRatio=rr_ratio
                )
            elif high >= tp:
                return Backtest(
                    strategyName=strategy_name, symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=tp_pct,
                    side="long", status="win", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier, rrRatio=rr_ratio
                )
        else:
            if high >= sl:
                return Backtest(
                    strategyName=strategy_name, symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=-sl_pct,
                    side="short", status="loss", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier, rrRatio=rr_ratio
                )
            elif low <= tp:
                return Backtest(
                    strategyName=strategy_name, symbol=symbol, interval=interval,
                    entryPrice=entry_price, entryTime=entry_time,
                    stopLossPrice=sl, stopLossPercent=sl_pct,
                    takeProfitPrice=tp, takeProfitPercent=tp_pct,
                    exitTime=exit_time, resultPct=tp_pct,
                    side="short", status="win", atr=atr,
                    rsi=row["rsi"], atrMultiplier=atr_multiplier, rrRatio=rr_ratio
                )
    return None


def summarize_results(trades: List[Backtest]) -> dict[str, float]:
    win_rate = sum(1 for t in trades if t.resultPct > 0) / \
        len(trades) if trades else 0

    equity = [1.0]
    for t in trades:
        equity.append(equity[-1] * (1 + t.resultPct))

    drawdowns = [(e / max(equity[:i + 1]) - 1)
                 for i, e in enumerate(equity[1:])]
    max_drawdown = min(drawdowns) if drawdowns else 0

    initial_balance = 100
    final_balance = equity[-1] * initial_balance

    total_hours = 0.0
    valid_trades = 0
    for t in trades:
        if isinstance(t.entryTime, pd.Timestamp) and isinstance(t.exitTime, pd.Timestamp):
            total_hours += (t.exitTime - t.entryTime).total_seconds() / 3600.0
            valid_trades += 1

    avg_hours_per_trade = total_hours / valid_trades if valid_trades else 0.0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "total_return_pct": round((equity[-1] - 1) * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "final_balance": round(final_balance, 2),
        "avg_hours_per_trade": round(avg_hours_per_trade, 2),
    }


def align_trend_to_lower_tf(df_lower: pd.DataFrame, df_higher: pd.DataFrame) -> pd.Series:
    df_higher = df_higher[["trend"]].copy()
    df_higher.index.name = "timestamp"
    return df_lower.index.to_series().apply(
        lambda ts: df_higher[df_higher.index <= ts].iloc[-1]["trend"]
        if not df_higher[df_higher.index <= ts].empty else None
    )
