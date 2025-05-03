from typing import Dict, List
import pandas as pd
from backtests.backtest_model import Backtest
from helpers.indicator import calculate_ema, calculate_rsi


async def rsi_ema_strategy(
    candles: List[Dict],
    symbol: str,
    interval: str,
    rsi_period: int = 14,
    ema_period: int = 200,
    rsi_threshold: float = 30,
    tp_pct: float = 0.01,
    sl_pct: float = 0.01
) -> Dict:
    if len(candles) < ema_period + rsi_period:
        return {"error": "Not enough data to compute indicators"}

    candles_dict = [{
        "openTime": kline.openTime,
        "open": kline.open,
        "high": kline.high,
        "low": kline.low,
        "close": kline.close,
        "volume": kline.volume,
        "closeTime": kline.closeTime
    } for kline in candles]

    df = pd.DataFrame(candles_dict)
    df["timestamp"] = pd.to_datetime(df["openTime"], unit="ms")
    df.set_index("timestamp", inplace=True)

    df["rsi"] = calculate_rsi(df, window=rsi_period)
    df["ema"] = calculate_ema(df, window=ema_period)
    df["signal"] = (df["rsi"] < rsi_threshold) & (df["close"] > df["ema"])

    trades: List[Backtest] = []

    for i in range(len(df) - 1):
        if df.iloc[i]["signal"]:
            entry_time = df.index[i]
            entry_price = df.iloc[i + 1]["open"]
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)

            for j in range(i + 1, len(df)):
                low = df.iloc[j]["low"]
                high = df.iloc[j]["high"]
                time_j = df.index[j]

                if low <= stop_loss:
                    result_pct = -sl_pct
                    trades.append(Backtest(
                        strategy_name="RSI-EMA",
                        symbol=symbol,
                        interval=interval,
                        entry_price=entry_price,
                        entry_time=entry_time,
                        exit_price=stop_loss,
                        exit_time=time_j,
                        result_pct=result_pct,
                        side="long",
                        status="loss"
                    ))
                    break

                elif high >= take_profit:
                    result_pct = tp_pct
                    trades.append(Backtest(
                        strategy_name="RSI-EMA",
                        symbol=symbol,
                        interval=interval,
                        entry_price=entry_price,
                        entry_time=entry_time,
                        exit_price=take_profit,
                        exit_time=time_j,
                        result_pct=result_pct,
                        side="long",
                        status="win"
                    ))
                    break

    if trades:
        await Backtest.insert_many(trades)

    total_return = sum(t.result_pct for t in trades)
    win_rate = sum(1 for t in trades if t.result_pct > 0) / \
        len(trades) if trades else 0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "total_return_pct": round(total_return * 100, 2),
    }
