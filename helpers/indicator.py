import pandas as pd
import ta
from ta.volatility import BollingerBands


def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return ta.momentum.RSIIndicator(close=df["close"], window=window).rsi()


def calculate_ema(df: pd.DataFrame, window: int = 200) -> pd.Series:
    return ta.trend.EMAIndicator(close=df["close"], window=window).ema_indicator()


def find_next_swing_high(df, start_idx, lookahead=20):
    return df.iloc[start_idx:start_idx + lookahead]["high"].max()


def find_next_swing_low(df, start_idx, lookahead=20):
    return df.iloc[start_idx:start_idx + lookahead]["low"].min()


def calculate_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    macd = ta.trend.MACD(close=df["close"], window_slow=slow_period,
                         window_fast=fast_period, window_sign=signal_period)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df["hist"] = macd.macd_diff()
    return df[["macd", "signal", "hist"]]


def add_bollinger_indicators(df: pd.DataFrame, window: int = 20, stddev: float = 2.0) -> pd.DataFrame:
    bb = BollingerBands(close=df["close"], window=window, window_dev=stddev)
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    df["volume_ma"] = df["volume"].rolling(20).mean()
    df["volume_spike"] = df["volume"] > (1.5 * df["volume_ma"])

    df["atr"] = df["high"] - df["low"]
    df["atr_ok"] = df["atr"] > (df["close"] * 0.005)

    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df['close'].shift(1)

    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr


def compute_trend_4h(df_4h: pd.DataFrame, ema_period: int = 200) -> pd.DataFrame:
    df_4h["ema"] = calculate_ema(df_4h, window=ema_period)
    # True = uptrend, False = downtrend
    df_4h["trend"] = df_4h["close"] > df_4h["ema"]
    return df_4h
