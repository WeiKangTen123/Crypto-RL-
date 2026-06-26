"""Trend-following indicators."""
import pandas as pd
import talib

from strategy_backtest.library import (
    calc_ema, calc_adx_dmi, calc_supertrend, calc_zlema, calc_t3,
    calc_ichimoku, calc_donchian_channels,
)


def ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return calc_ema(df, period)


def sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return pd.Series(talib.SMA(df['Close'], timeperiod=period), index=df.index)


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """Returns (supertrend_line, direction) where direction: 1=up, -1=down."""
    return calc_supertrend(df, period, multiplier)


def adx_dmi(df: pd.DataFrame, period: int = 14):
    """Returns (adx, di_plus, di_minus)."""
    return calc_adx_dmi(df, period)


def zlema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return calc_zlema(df['Close'], period)


def t3(df: pd.DataFrame, length: int = 5, vf: float = 0.7) -> pd.Series:
    return calc_t3(df['Close'], length, vf)


def dema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Double EMA — reduces lag versus standard EMA."""
    e1 = pd.Series(talib.EMA(df['Close'], timeperiod=period), index=df.index)
    e2 = pd.Series(talib.EMA(e1, timeperiod=period), index=df.index)
    return 2 * e1 - e2


def ema_ribbon(df: pd.DataFrame, periods=(9, 21, 55, 200)) -> dict:
    """Returns dict of {period: Series}."""
    return {p: pd.Series(talib.EMA(df['Close'], timeperiod=p), index=df.index) for p in periods}


def ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26,
             senkou_b: int = 52, displacement: int = 26) -> pd.DataFrame:
    """
    Ichimoku Cloud components.
    Returns DataFrame with columns: tenkan, kijun, senkou_a, senkou_b, cloud_top, cloud_bottom.
    """
    return calc_ichimoku(df, tenkan, kijun, senkou_b, displacement)


def donchian(df: pd.DataFrame, period: int = 20):
    """
    Donchian Channels (Turtle Trader breakout levels).
    Returns (upper, mid, lower).
    """
    return calc_donchian_channels(df, period)


def _wma(series: pd.Series, period: int) -> pd.Series:
    """Vectorised WMA using conv — O(n) not O(n²)."""
    import numpy as np
    weights = np.arange(1, period + 1, dtype=float)
    weights /= weights.sum()
    vals = np.convolve(series.values, weights[::-1], mode='full')[:len(series)]
    result = pd.Series(vals, index=series.index)
    result.iloc[:period - 1] = float('nan')
    return result


def hma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Hull Moving Average — ultra-smooth, low-lag MA.
    HMA(n) = WMA(2×WMA(n/2) − WMA(n), sqrt(n))
    """
    half  = max(2, period // 2)
    sqrt_ = max(2, int(period ** 0.5))
    raw = 2 * _wma(df['Close'], half) - _wma(df['Close'], period)
    return _wma(raw.dropna().reindex(df.index), sqrt_)


def parabolic_sar(df: pd.DataFrame, acceleration: float = 0.02,
                  maximum: float = 0.2) -> pd.Series:
    """
    Parabolic SAR — trailing stop / trend direction indicator.
    Returns direction Series: +1 when price > SAR (uptrend), -1 when below (downtrend).
    Used as an exit (flip direction) or trend filter.
    Params: acceleration 0.01–0.05, maximum 0.1–0.3.
    """
    sar_vals = talib.SAR(df['High'], df['Low'],
                         acceleration=acceleration, maximum=maximum)
    direction = pd.Series(0, index=df.index)
    direction[df['Close'] > sar_vals] =  1
    direction[df['Close'] < sar_vals] = -1
    return direction


def parabolic_sar_raw(df: pd.DataFrame, acceleration: float = 0.02,
                      maximum: float = 0.2) -> pd.Series:
    """
    Parabolic SAR — returns actual price-level SAR values (not direction).
    Used by psar_trail exit to compare Close vs SAR stop level.
    """
    return pd.Series(
        talib.SAR(df['High'], df['Low'], acceleration=acceleration, maximum=maximum),
        index=df.index,
    )


def vortex(df: pd.DataFrame, period: int = 14):
    """
    Vortex Indicator — identifies trend reversals and strength.
    VI+ > VI- and both > 1.0 → strong uptrend.
    VI- > VI+ and both > 1.0 → strong downtrend.
    Returns (vi_plus, vi_minus).
    Params range: period 10–30.
    """
    high = df['High']
    low  = df['Low']
    close_prev = df['Close'].shift(1)
    tr  = pd.concat([high - low,
                     (high - close_prev).abs(),
                     (low  - close_prev).abs()], axis=1).max(axis=1)
    vm_plus  = (high - low.shift(1)).abs()
    vm_minus = (low  - high.shift(1)).abs()
    tr_sum   = tr.rolling(period).sum()
    vi_plus  = vm_plus.rolling(period).sum()  / (tr_sum + 1e-10)
    vi_minus = vm_minus.rolling(period).sum() / (tr_sum + 1e-10)
    return vi_plus, vi_minus
