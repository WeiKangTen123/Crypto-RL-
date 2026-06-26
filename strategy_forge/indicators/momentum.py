"""Momentum oscillator indicators — all return Series or named tuples."""
import pandas as pd
import numpy as np
import talib

from strategy_backtest.library import (
    calc_rsi, calc_macd, calc_stoch_kdj, calc_wavetrend,
    calc_mfi, calc_vrsi, calc_fisher_transform, calc_aroon,
    calc_tsi, calc_zero_lag_macd, calc_lorentzian_classification,
    detect_divergence,
)


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return calc_rsi(df['Close'], period)


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    return calc_macd(df, fast, slow, signal)


def kdj(df: pd.DataFrame, period: int = 9):
    """Returns (K, D, J)."""
    return calc_stoch_kdj(df, period)


def wavetrend(df: pd.DataFrame, n1: int = 10, n2: int = 21):
    """Returns (wt1, wt2)."""
    return calc_wavetrend(df, n1, n2)


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return calc_mfi(df, period)


def vrsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return calc_vrsi(df, period)


def fisher(df: pd.DataFrame, period: int = 10):
    """Returns (fisher_line, trigger)."""
    return calc_fisher_transform(df, period)


def aroon(df: pd.DataFrame, period: int = 14):
    """Returns (aroon_up, aroon_down)."""
    return calc_aroon(df, period)


def stoch(df: pd.DataFrame, fastk: int = 5, slowk: int = 3, slowd: int = 3):
    """Returns (slowk, slowd) — classic Stochastic oscillator."""
    slowk_s, slowd_s = talib.STOCH(
        df['High'], df['Low'], df['Close'],
        fastk_period=fastk, slowk_period=slowk, slowd_period=slowd,
    )
    return slowk_s, slowd_s


def cci(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return pd.Series(
        talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=period),
        index=df.index,
    )


def tsi(df: pd.DataFrame, fast: int = 13, slow: int = 25) -> pd.Series:
    """True Strength Index — double-smoothed momentum, range ~-100 to +100."""
    return calc_tsi(df['Close'], fast, slow)


def zero_lag_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """Zero-Lag MACD built on DEMA. Returns (zmacd, signal_line)."""
    return calc_zero_lag_macd(df, fast, slow, signal)


def divergence(df: pd.DataFrame, indicator_series: pd.Series, lookback: int = 60) -> pd.Series:
    """
    Bullish/Bearish divergence between price and any oscillator.
    Returns Series: 1=bullish divergence, -1=bearish divergence, 0=none.
    """
    return detect_divergence(df['Close'], indicator_series, lookback)


def lorentzian(df: pd.DataFrame, k: int = 5, window: int = 2000) -> pd.Series:
    """Lorentzian KNN classification score (bullish/bearish market state)."""
    return calc_lorentzian_classification(df, k_neighbors=k, history_window=window)


def stoch_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14,
              smooth_k: int = 3, smooth_d: int = 3):
    """
    Stochastic RSI — applies Stochastic oscillator to RSI values.
    More sensitive than plain RSI. Returns (stoch_k, stoch_d), both 0–100.
    stoch_k crossing above stoch_d from <20 = oversold reversal signal.
    """
    r = calc_rsi(df['Close'], rsi_period)
    r_min = r.rolling(stoch_period).min()
    r_max = r.rolling(stoch_period).max()
    raw_k = 100 * (r - r_min) / (r_max - r_min + 1e-10)
    k = raw_k.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Williams %R — momentum oscillator, range -100 to 0.
    < -80 = oversold (long signal), > -20 = overbought (short signal).
    Faster than RSI at catching reversals.
    """
    high_n = df['High'].rolling(period).max()
    low_n  = df['Low'].rolling(period).min()
    return -100 * (high_n - df['Close']) / (high_n - low_n + 1e-10)


def elder_ray(df: pd.DataFrame, period: int = 13):
    """
    Elder Ray Index — Bull Power and Bear Power.
    Bull Power = High - EMA(Close, period)
    Bear Power = Low  - EMA(Close, period)
    Entry: Bull Power crosses above 0 (uptrend strengthening).
    Returns (bull_power, bear_power).
    """
    e = pd.Series(talib.EMA(df['Close'], timeperiod=period), index=df.index)
    return df['High'] - e, df['Low'] - e


def dpo(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Detrended Price Oscillator — removes trend to isolate cycles.
    DPO > 0 → price above trend (momentum up), < 0 → below trend.
    Useful for identifying overbought/oversold without trend bias.
    """
    shift = period // 2 + 1
    sma = df['Close'].rolling(period).mean().shift(shift)
    return df['Close'] - sma
