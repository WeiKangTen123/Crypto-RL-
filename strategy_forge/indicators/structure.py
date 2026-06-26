"""Market structure indicators — Z-score, FVG, pivots, candle patterns, order blocks."""
import pandas as pd
import numpy as np

from strategy_backtest.library import (
    calc_zscore, detect_fvg, detect_swing_high_low,
    detect_candle_engulfing, detect_candle_hammer,
    detect_candle_bearish_engulfing, detect_candle_shooting_star,
    detect_order_blocks,
)


def zscore(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Rolling Z-score of Close price."""
    return calc_zscore(df['Close'], period)


def zscore_of(series: pd.Series, period: int = 20) -> pd.Series:
    """Rolling Z-score of any series."""
    return calc_zscore(series, period)


def fvg(df: pd.DataFrame):
    """
    Fair Value Gaps.
    Returns (bullish_fvg, bearish_fvg) — boolean Series.
    """
    return detect_fvg(df)


def imbalance_zone(df: pd.DataFrame, threshold: float = 0.005):
    """
    Imbalance Zone (IMB) — near-gap or gap between consecutive bars.
    More frequent than FVG (bar[i] vs bar[i-1], not bar[i-2]).
    threshold: tolerance for 'near-gap' in pct (0=strict gap, 0.005=0.5% tolerance).
    Bull IMB: current low ≥ previous high × (1 - threshold).
    Bear IMB: current high ≤ previous low × (1 + threshold).
    """
    prev_high = df['High'].shift(1)
    prev_low  = df['Low'].shift(1)
    bull_imb = df['Low'] >= prev_high * (1 - threshold)
    bear_imb = df['High'] <= prev_low  * (1 + threshold)
    return bull_imb.fillna(False), bear_imb.fillna(False)


def _cooldown(mask: pd.Series, n: int) -> pd.Series:
    """After each True, suppress the next n bars. O(fires) time."""
    vals = mask.values.copy().astype(bool)
    i = 0
    while i < len(vals):
        if vals[i]:
            vals[i + 1 : i + n + 1] = False
            i += n + 1
        else:
            i += 1
    return pd.Series(vals, index=mask.index)


def fvg_zones(df: pd.DataFrame, fvg_htf_bars: int = 48,
              fvg_zone_timeout: int = 8, fvg_cooldown: int = 48,
              fvg_min_pct: float = 0.003):
    """
    Zone-based MTF FVG entry — 4H zones detected from lower-TF data.

    Resamples `df` (e.g. 5m) to HTF (fvg_htf_bars × base-TF minutes),
    finds FVG gaps, forward-fills zone boundaries, then fires when price
    first enters an active zone. Cooldown prevents re-firing for N bars.

    Bull zone [prev_high, curr_low]: gapped UP → support on retest → Long.
    Bear zone [curr_high, prev_low]: gapped DOWN → resistance on retest → Short.

    fvg_htf_bars   : base-TF bars per HTF bar (48 × 5min = 4h)
    fvg_zone_timeout: HTF bars before zone expires (8 = 32h on 4h)
    fvg_cooldown   : base-TF bars between fires (48 = 4h cooldown on 5m)
    fvg_min_pct    : minimum gap size as fraction of price (filters tiny FVGs)
    Returns (bull_touch, bear_touch) — boolean Series on base-TF index.
    """
    # ── 1. Build HTF ──────────────────────────────────────────────────────────
    try:
        base_min = int((df.index[1] - df.index[0]).total_seconds() // 60)
    except Exception:
        base_min = 5
    htf_min = base_min * int(fvg_htf_bars)

    df_htf = df[['Open', 'High', 'Low', 'Close']].resample(
        f'{htf_min}min', label='right', closed='right', origin='epoch'
    ).agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(how='all')

    if len(df_htf) < 3:
        empty = pd.Series(False, index=df.index)
        return empty, empty

    # ── 2. Detect HTF FVGs with minimum gap size filter ───────────────────────
    high2 = df_htf['High'].shift(2)
    low2  = df_htf['Low'].shift(2)

    # Raw gap condition
    bull_raw = df_htf['Low'] > high2
    bear_raw = df_htf['High'] < low2

    # Gap as fraction of price — reject tiny noise gaps
    min_gap = float(fvg_min_pct)
    bull_gap_pct = (df_htf['Low'] - high2) / df_htf['Low'].replace(0, np.nan)
    bear_gap_pct = (low2 - df_htf['High']) / low2.replace(0, np.nan)

    bull_fvg = bull_raw & (bull_gap_pct >= min_gap)
    bear_fvg = bear_raw & (bear_gap_pct >= min_gap)

    # ── 3. Zone boundaries (NaN on non-FVG bars) ──────────────────────────────
    bl  = pd.Series(np.where(bull_fvg, high2,          np.nan), index=df_htf.index)
    bu  = pd.Series(np.where(bull_fvg, df_htf['Low'],  np.nan), index=df_htf.index)
    brl = pd.Series(np.where(bear_fvg, df_htf['High'], np.nan), index=df_htf.index)
    bru = pd.Series(np.where(bear_fvg, low2,           np.nan), index=df_htf.index)

    t = int(fvg_zone_timeout)
    bl  = bl.ffill(limit=t);  bu  = bu.ffill(limit=t)
    brl = brl.ffill(limit=t); bru = bru.ffill(limit=t)

    # ── 4. Map HTF → base-TF ─────────────────────────────────────────────────
    bl5  = bl.reindex(df.index,  method='ffill')
    bu5  = bu.reindex(df.index,  method='ffill')
    brl5 = brl.reindex(df.index, method='ffill')
    bru5 = bru.reindex(df.index, method='ffill')

    close = df['Close']
    in_bull = (close >= bl5)  & (close <= bu5)  & bl5.notna()
    in_bear = (close >= brl5) & (close <= bru5) & brl5.notna()

    # ── 5. Fire on first touch (transition FROM outside TO inside zone) ───────
    raw_bull = (in_bull & ~in_bull.shift(1).fillna(False)).fillna(False)
    raw_bear = (in_bear & ~in_bear.shift(1).fillna(False)).fillna(False)

    # ── 6. Cooldown: suppress re-fires for fvg_cooldown base-TF bars ─────────
    bull_touch = _cooldown(raw_bull, int(fvg_cooldown))
    bear_touch = _cooldown(raw_bear, int(fvg_cooldown))

    return bull_touch, bear_touch


def swing_pivots(df: pd.DataFrame, lookback: int = 20):
    """
    Swing highs and lows.
    Returns (is_swing_high, is_swing_low) — boolean Series confirmed at bar i.
    """
    return detect_swing_high_low(df, lookback)


def price_vs_ema_pct(df: pd.DataFrame, period: int = 50) -> pd.Series:
    """Percentage distance of Close from EMA — positive = above."""
    import talib
    ema = pd.Series(talib.EMA(df['Close'], timeperiod=period), index=df.index)
    return (df['Close'] - ema) / (ema + 1e-10) * 100


# ── Candle patterns ───────────────────────────────────────────────────────────

def candle_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    """Boolean Series — True on bullish engulfing bar."""
    return detect_candle_engulfing(df)


def candle_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    """Boolean Series — True on bearish engulfing bar."""
    return detect_candle_bearish_engulfing(df)


def candle_hammer(df: pd.DataFrame) -> pd.Series:
    """Boolean Series — True on hammer / pin bar (bullish reversal signal)."""
    return detect_candle_hammer(df)


def candle_shooting_star(df: pd.DataFrame) -> pd.Series:
    """Boolean Series — True on shooting star (bearish reversal signal)."""
    return detect_candle_shooting_star(df)


# ── Order blocks ──────────────────────────────────────────────────────────────

def order_blocks(df: pd.DataFrame, atr_period: int = 14,
                 atr_multiplier: float = 2.0, ob_lookback: int = 3) -> pd.Series:
    """
    Institutional order block mitigation signals.
    Returns Series: 1=bullish OB touch (long), -1=bearish OB touch (short), 0=none.
    """
    return detect_order_blocks(df, atr_period, atr_multiplier, ob_lookback)
