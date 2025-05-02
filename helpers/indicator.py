import pandas as pd
import ta


def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return ta.momentum.RSIIndicator(close=df["close"], window=window).rsi()


def calculate_ema(df: pd.DataFrame, window: int = 200) -> pd.Series:
    return ta.trend.EMAIndicator(close=df["close"], window=window).ema_indicator()
