from typing import Dict, List
import pandas as pd
from helpers.indicator import calculate_ema, calculate_rsi


def rsi_ema_strategy(
    candles: List[Dict],
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

    # Tạo cột signal
    df["signal"] = (df["rsi"] < rsi_threshold) & (df["close"] > df["ema"])

    trades = []

    for i in range(len(df) - 1):
        if df.iloc[i]["signal"]:
            entry_time = df.index[i]
            entry_price = df.iloc[i + 1]["open"]
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)

            print(
                f"\n[ENTRY] Time: {entry_time}, Entry Price: {entry_price:.4f}, SL: {stop_loss:.4f}, TP: {take_profit:.4f}")

            for j in range(i + 1, len(df)):
                low = df.iloc[j]["low"]
                high = df.iloc[j]["high"]
                time_j = df.index[j]

                if low <= stop_loss:
                    print(
                        f"[STOP LOSS] Time: {time_j}, Low: {low:.4f} → Hit SL ({-sl_pct*100:.2f}%)")
                    trades.append(-sl_pct)
                    break
                elif high >= take_profit:
                    print(
                        f"[TAKE PROFIT] Time: {time_j}, High: {high:.4f} → Hit TP ({tp_pct*100:.2f}%)")
                    trades.append(tp_pct)
                    break

    total_return = sum(trades)
    win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0

    print(
        f"\n[SUMMARY] Total Trades: {len(trades)}, Win Rate: {win_rate*100:.2f}%, Total Return: {total_return*100:.2f}%")

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "total_return_pct": round(total_return * 100, 2),
    }
