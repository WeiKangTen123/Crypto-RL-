"""Volatility indicators — ATR, Bollinger, Keltner, Squeeze, BBW, Choppiness."""
import pandas as pd
import talib

from strategy_backtest.library import (
    calc_atr, calc_bollinger_bands, calc_keltner_channels, calc_bb_kc_squeeze,
    calc_choppiness_index,
)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return calc_atr(df, period)


def bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0):
    """Returns (upper, mid, lower)."""
    return calc_bollinger_bands(df, period, std)


def keltner(df: pd.DataFrame, period: int = 20, mult: float = 2.0):
    """Returns (upper, mid, lower)."""
    return calc_keltner_channels(df, period, mult)


def squeeze(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.0,
            kc_period: int = 20, kc_mult: float = 1.5) -> pd.Series:
    """Returns boolean Series — True when BB inside KC (squeeze active)."""
    return calc_bb_kc_squeeze(df, bb_period, bb_std, kc_period, kc_mult)


def bbw(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.Series:
    """Bollinger Band Width — normalised spread (upper-lower)/mid."""
    upper, mid, lower = calc_bollinger_bands(df, period, std)
    return (upper - lower) / (mid + 1e-10)


def historical_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Rolling standard deviation of log-returns, annualised."""
    import math
    log_ret = (df['Close'] / df['Close'].shift(1)).clip(lower=1e-10).apply(math.log)
    return log_ret.rolling(window=period).std() * (365 ** 0.5)


def choppiness(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Choppiness Index — >61.8 = consolidation, <38.2 = strong trend.
    """
    return calc_choppiness_index(df, period)
