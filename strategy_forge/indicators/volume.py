"""Volume-based indicators — VWAP, CVD, VWMA, taker ratio, taker intensity."""
import pandas as pd

from strategy_backtest.library import (
    calc_vwap, calc_cvd, calc_vwma, calc_vwap_zscore, calc_taker_intensity,
    calc_orderbook_imbalance
)


def vwap(df: pd.DataFrame) -> pd.Series:
    """Daily-reset VWAP."""
    return calc_vwap(df)


def vwap_zscore(df: pd.DataFrame, period: int = 20):
    """Returns (zscore, vwap_line)."""
    return calc_vwap_zscore(df, period)


def cvd(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Cumulative Volume Delta (taker buy − sell rolling sum)."""
    return calc_cvd(df, window)


def vwma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volume-Weighted Moving Average."""
    return calc_vwma(df, period)


def taker_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Rolling taker-buy ratio: taker_buy_vol / total_vol.
    Falls back to 0.5 when taker_buy_base_vol column is absent.
    """
    if 'taker_buy_base_vol' in df.columns:
        tb = pd.to_numeric(df['taker_buy_base_vol'], errors='coerce').fillna(0)
    else:
        tb = df['Volume'] * 0.5
    ratio = tb / (df['Volume'] + 1e-10)
    return ratio.rolling(window=period).mean()


def volume_zscore(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Z-score of volume — spikes indicate unusual activity."""
    vol = df['Volume']
    return (vol - vol.rolling(period).mean()) / (vol.rolling(period).std() + 1e-10)


def taker_intensity(df: pd.DataFrame, period: int = 24, std_mult: float = 2.0):
    """
    Aggressive taker participation score (z-score of num_trades) + taker ratio.
    Returns (intensity_zscore, taker_ratio_series).
    Falls back gracefully when num_trades column is absent.
    """
    return calc_taker_intensity(df, period, std_mult)


def obv(df: pd.DataFrame) -> pd.Series:
    """
    On Balance Volume — cumulative volume weighted by price direction.
    Rising OBV = volume confirms uptrend; falling OBV = distribution.
    """
    import numpy as np
    direction = np.sign(df['Close'].diff().fillna(0))
    return (df['Volume'] * direction).cumsum()


def ob_imbalance(df: pd.DataFrame, level: float = 1.0) -> pd.Series:
    """
    Returns Order Book Imbalance ratio (Bids / (Bids + Asks)) at a specific % depth.
    """
    return calc_orderbook_imbalance(df, level=level)
