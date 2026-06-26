"""
entry_signals.py — registry of entry signal generators.

Each function receives a DataFrame and a params dict.
Returns a pd.Series of int: 1=Long, -1=Short, 0=Neutral.

Register new signals by adding to ENTRY_SIGNAL_REGISTRY at the bottom.
"""
import os
import pandas as pd
import numpy as np

from strategy_forge.indicators import (
    rsi, macd, kdj, wavetrend, mfi, vrsi, fisher, aroon,
    ema, sma, supertrend, adx_dmi, zlema,
    atr, bollinger, keltner, squeeze,
    vwap, cvd, taker_ratio,
    zscore, zscore_of, fvg, imbalance_zone, fvg_zones,
    stoch_rsi, williams_r, elder_ray, dpo,
    hma, parabolic_sar, vortex,
    candle_bullish_engulfing, candle_bearish_engulfing,
    candle_hammer, candle_shooting_star, order_blocks,
)

_DATASET_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dataset')


def _sig(long_cond: pd.Series, short_cond: pd.Series) -> pd.Series:
    s = pd.Series(0, index=long_cond.index)
    s[long_cond]  =  1
    s[short_cond] = -1
    return s


# ── Momentum entries ──────────────────────────────────────────────────────────

def entry_rsi_reversion(df, p):
    r = rsi(df, p.get('rsi_period', 14))
    return _sig(r < p.get('rsi_oversold', 30), r > p.get('rsi_overbought', 70))


def entry_rsi_trend(df, p):
    """RSI above/below midline as trend signal."""
    r = rsi(df, p.get('rsi_period', 14))
    mid = p.get('rsi_threshold', 50)
    return _sig(r > mid, r < mid)


def entry_macd_cross(df, p):
    m, sig, _ = macd(df, p.get('macd_fast', 12), p.get('macd_slow', 26), p.get('macd_signal', 9))
    cross = (m - sig)
    return _sig((cross > 0) & (cross.shift(1) <= 0), (cross < 0) & (cross.shift(1) >= 0))


def entry_macd_zero_cross(df, p):
    m, _, _ = macd(df, p.get('macd_fast', 12), p.get('macd_slow', 26), p.get('macd_signal', 9))
    return _sig((m > 0) & (m.shift(1) <= 0), (m < 0) & (m.shift(1) >= 0))


def entry_kdj_reversion(df, p):
    K, D, J = kdj(df, p.get('kdj_period', 9))
    return _sig(J < p.get('kdj_oversold', 20), J > p.get('kdj_overbought', 80))


def entry_wavetrend(df, p):
    wt1, wt2 = wavetrend(df, p.get('wt_n1', 10), p.get('wt_n2', 21))
    cross = wt1 - wt2
    return _sig(
        (cross > 0) & (cross.shift(1) <= 0) & (wt1 < p.get('wt_oversold', -60)),
        (cross < 0) & (cross.shift(1) >= 0) & (wt1 > p.get('wt_overbought', 60)),
    )


def entry_mfi_reversion(df, p):
    m = mfi(df, p.get('mfi_period', 14))
    return _sig(m < 20, m > 80)


def entry_vrsi_reversion(df, p):
    v = vrsi(df, p.get('vrsi_period', 14))
    return _sig(v < p.get('vrsi_oversold', 25), v > p.get('vrsi_overbought', 75))


def entry_fisher(df, p):
    f, trigger = fisher(df, p.get('period', 10))
    return _sig(
        (f > trigger) & (f.shift(1) <= trigger.shift(1)),
        (f < trigger) & (f.shift(1) >= trigger.shift(1)),
    )


def entry_aroon_cross(df, p):
    up, down = aroon(df, p.get('aroon_period', 14))
    thr = p.get('aroon_threshold', 70)
    return _sig((up > thr) & (up > down), (down > thr) & (down > up))


# ── Trend entries ─────────────────────────────────────────────────────────────

def entry_ema_cross(df, p):
    fast = ema(df, p.get('ema_fast', 9))
    slow = ema(df, p.get('ema_slow', 21))
    cross = fast - slow
    return _sig((cross > 0) & (cross.shift(1) <= 0), (cross < 0) & (cross.shift(1) >= 0))


def entry_ema_price_cross(df, p):
    e = ema(df, p.get('ema_period', 50))
    return _sig(
        (df['Close'] > e) & (df['Close'].shift(1) <= e.shift(1)),
        (df['Close'] < e) & (df['Close'].shift(1) >= e.shift(1)),
    )


def entry_supertrend(df, p):
    _, direction = supertrend(df, p.get('st_period', 10), p.get('st_multiplier', 3.0))
    long_flip  = (direction == 1) & (direction.shift(1) == -1)
    short_flip = (direction == -1) & (direction.shift(1) == 1)
    mode = p.get('direction', 'both')
    if mode == 'long_only':
        return _sig(long_flip, pd.Series(False, index=df.index))
    if mode == 'short_only':
        return _sig(pd.Series(False, index=df.index), short_flip)
    return _sig(long_flip, short_flip)


def entry_zlema_cross(df, p):
    fast = zlema(df, p.get('ema_fast', 9))
    slow = ema(df, p.get('ema_slow', 21))
    cross = fast - slow
    return _sig((cross > 0) & (cross.shift(1) <= 0), (cross < 0) & (cross.shift(1) >= 0))


def entry_ema_macd_cross(df, p):
    """
    Combined EMA + MACD entry.
    Long: Fast EMA > Slow EMA AND MACD > Signal.
    Short: Fast EMA < Slow EMA AND MACD < Signal.
    Fires when either of them just crossed, provided the other is already aligned.
    """
    fast = ema(df, p.get('ema_fast', 5))
    slow = ema(df, p.get('ema_slow', 20))
    m, sig, _ = macd(df, p.get('macd_fast', 12), p.get('macd_slow', 26), p.get('macd_signal', 9))
    
    ema_bull = fast > slow
    ema_bear = fast < slow
    
    macd_bull = m > sig
    macd_bear = m < sig
    
    # Needs to be a fresh cross in at least ONE of them while both conditions are met
    ema_cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    ema_cross_dn = (fast < slow) & (fast.shift(1) >= slow.shift(1))
    macd_cross_up = (m > sig) & (m.shift(1) <= sig.shift(1))
    macd_cross_dn = (m < sig) & (m.shift(1) >= sig.shift(1))
    
    bull_entry = ema_bull & macd_bull & (ema_cross_up | macd_cross_up)
    bear_entry = ema_bear & macd_bear & (ema_cross_dn | macd_cross_dn)
    
    return _sig(bull_entry, bear_entry)


# ── Volatility / structure entries ────────────────────────────────────────────

def entry_bollinger_reversion(df, p):
    upper, mid, lower = bollinger(df, p.get('bb_period', 20), p.get('bb_std', 2.0))
    return _sig(df['Close'] < lower, df['Close'] > upper)


def entry_bollinger_breakout(df, p):
    upper, _, lower = bollinger(df, p.get('bb_period', 20), p.get('bb_std', 2.0))
    return _sig(
        (df['Close'] > upper) & (df['Close'].shift(1) <= upper.shift(1)),
        (df['Close'] < lower) & (df['Close'].shift(1) >= lower.shift(1)),
    )


def entry_keltner_reversion(df, p):
    upper, mid, lower = keltner(df, p.get('kc_window', 20), p.get('kc_multiplier', 2.0))
    return _sig(df['Close'] < lower, df['Close'] > upper)


def entry_squeeze_breakout(df, p):
    """Enter on first bar out of Bollinger/Keltner squeeze."""
    sq = squeeze(df, p.get('bb_period', 20), p.get('bb_std', 2.0),
                 p.get('kc_window', 20), p.get('kc_multiplier', 1.5))
    was_squeezed = sq.shift(1).fillna(False)
    released = ~sq & was_squeezed
    return _sig(released & (df['Close'] > df['Open']),
                released & (df['Close'] < df['Open']))


def entry_zscore_reversion(df, p):
    z = zscore(df, p.get('zscore_period', 20))
    thr = p.get('zscore_threshold', 2.0)
    return _sig(z < -thr, z > thr)


def entry_fvg(df, p):
    bull_fvg, bear_fvg = fvg(df)
    return _sig(bull_fvg, bear_fvg)


def entry_imbalance_zone(df, p):
    """
    Imbalance Zone (IMB) — bar[i] near-gaps over bar[i-1].
    2-3× more frequent than FVG. imb_threshold controls near-gap tolerance.
    """
    bull, bear = imbalance_zone(df, p.get('imb_threshold', 0.005))
    return _sig(bull, bear)


def entry_fvg_zone_touch(df, p):
    """
    Zone-based MTF FVG entry — use 5m data for precision entry into 4H FVG zones.

    Detects 4H FVG zones by resampling df (e.g. 5m) to HTF, marks the zone
    boundaries, then fires when price first enters an active zone.

    Bull zone: gap where price jumped UP on 4H → treat as support on retest → Long.
    Bear zone: gap where price dropped DOWN on 4H → treat as resistance on retest → Short.

    fvg_htf_bars   : base-TF bars per HTF bar (48 = 5m→4h, 12 = 5m→1h, 4 = 1h→4h)
    fvg_zone_timeout: HTF bars before zone expires (8 = 32h on 4h, or 40h on 5h)
    """
    bull, bear = fvg_zones(
        df,
        fvg_htf_bars     = int(p.get('fvg_htf_bars',     48)),
        fvg_zone_timeout = int(p.get('fvg_zone_timeout',   8)),
        fvg_cooldown     = int(p.get('fvg_cooldown',      48)),
        fvg_min_pct      = float(p.get('fvg_min_pct',   0.003)),
    )
    return _sig(bull, bear)


# ── Volume / order-flow entries ───────────────────────────────────────────────

def entry_vwap_reversion(df, p):
    from strategy_forge.indicators.volume import vwap_zscore
    z, _ = vwap_zscore(df, p.get('vwap_period', 20))
    thr = p.get('vwap_std_mult', 1.5)
    return _sig(z < -thr, z > thr)


def entry_cvd_cross(df, p):
    c = cvd(df, p.get('cvd_window', 20))
    return _sig((c > 0) & (c.shift(1) <= 0), (c < 0) & (c.shift(1) >= 0))


def entry_taker_momentum(df, p):
    tr = taker_ratio(df, p.get('intensity_period', 20))
    thr = p.get('taker_threshold', 0.6)
    return _sig(tr > thr, tr < (1 - thr))


# ── New indicator entries ─────────────────────────────────────────────────────

def entry_stoch_rsi_reversion(df, p):
    """Stochastic RSI oversold/overbought reversal — more sensitive than RSI."""
    k, d = stoch_rsi(df, p.get('rsi_period', 14), p.get('rsi_period', 14),
                     p.get('smoothing', 3), p.get('smoothing', 3))
    thr_lo = p.get('rsi_oversold', 20)
    thr_hi = p.get('rsi_overbought', 80)
    return _sig(
        (k < thr_lo) & (k > d) & (k.shift(1) <= d.shift(1)),
        (k > thr_hi) & (k < d) & (k.shift(1) >= d.shift(1)),
    )


def entry_williams_r_reversion(df, p):
    """Williams %R oversold/overbought reversal — fast, catches quick turns."""
    wr = williams_r(df, p.get('period', 14))
    return _sig(
        (wr < -80) & (wr > wr.shift(1)),
        (wr > -20) & (wr < wr.shift(1)),
    )


def entry_elder_ray(df, p):
    """Elder Ray: Bull Power crosses above 0 in uptrend, Bear Power crosses below 0."""
    bull, bear = elder_ray(df, p.get('period', 13))
    adx_val, _, _ = adx_dmi(df, p.get('adx_period', 14))
    trend_ok = adx_val > p.get('adx_threshold', 20)
    return _sig(
        (bull > 0) & (bull.shift(1) <= 0) & trend_ok,
        (bear < 0) & (bear.shift(1) >= 0) & trend_ok,
    )


def entry_dpo_reversion(df, p):
    """DPO cycle reversal — when price deviates far from trend, mean-reverts."""
    d = dpo(df, p.get('period', 20))
    thr = d.rolling(p.get('lookback', 20)).std() * p.get('zscore_threshold', 1.5)
    return _sig(d < -thr, d > thr)


def entry_hma_cross(df, p):
    """HMA fast/slow crossover — ultra-low-lag trend signal."""
    fast = hma(df, p.get('ema_fast', 9))
    slow = hma(df, p.get('ema_slow', 21))
    cross = fast - slow
    return _sig((cross > 0) & (cross.shift(1) <= 0), (cross < 0) & (cross.shift(1) >= 0))


def entry_parabolic_sar(df, p):
    """Enter on Parabolic SAR direction flip (trailing stop reversal)."""
    direction = parabolic_sar(df, p.get('psar_acceleration', 0.02), p.get('psar_maximum', 0.2))
    return _sig(
        (direction == 1) & (direction.shift(1) == -1),
        (direction == -1) & (direction.shift(1) == 1),
    )


def entry_vortex_cross(df, p):
    """Vortex VI+ / VI- crossover — trend change signal."""
    vi_p, vi_m = vortex(df, p.get('period', 14))
    diff = vi_p - vi_m
    return _sig(
        (diff > 0) & (diff.shift(1) <= 0),
        (diff < 0) & (diff.shift(1) >= 0),
    )


# ── Candle pattern entries ────────────────────────────────────────────────────

def entry_candle_engulfing(df, p):
    """Bullish engulfing → Long, Bearish engulfing → Short. No params required."""
    return _sig(candle_bullish_engulfing(df), candle_bearish_engulfing(df))


def entry_candle_pin_bar(df, p):
    """Hammer → Long, Shooting Star → Short. No params required."""
    return _sig(candle_hammer(df), candle_shooting_star(df))


# ── Order block entry ─────────────────────────────────────────────────────────

def entry_order_block(df, p):
    """
    Institutional order block mitigation.
    Bullish OB touch → Long (+1), Bearish OB touch → Short (-1).
    Uses ATR to qualify blocks and lookback to find OB origin bars.
    """
    ob = order_blocks(df,
                      atr_period=p.get('atr_period', 14),
                      atr_multiplier=p.get('atr_multiplier', 2.0),
                      ob_lookback=int(p.get('ob_lookback', 3)))
    return ob.fillna(0).astype(int)


# ── Funding rate entry ────────────────────────────────────────────────────────

def _load_funding_rate_entry(df: pd.DataFrame, coin: str) -> pd.Series:
    path = os.path.join(_DATASET_DIR, coin.upper(), '4h', 'funding_rate.parquet')
    fr = pd.read_parquet(path)
    if 'open_time' in fr.columns:
        fr = fr.set_index('open_time')
    fr.index = pd.to_datetime(fr.index, utc=True).tz_localize(None)
    df_idx = pd.to_datetime(df.index).tz_localize(None) if df.index.tz is not None else pd.to_datetime(df.index)
    rate = fr['funding_rate'].reindex(df_idx, method='ffill').fillna(0)
    rate.index = df.index
    return rate


def entry_funding_rate_mr(df, p):
    """
    Funding Rate Mean Reversion entry.

    Extreme positive funding → longs are over-leveraged → fade (go short).
    Extreme negative funding → shorts are over-leveraged → fade (go long).

    Works best on 4h TF where funding rate is published every 8h.
    On lower TFs the signal forward-fills until the next settlement.

    Params
    ------
    coin            : which coin's parquet to load (default 'ETH')
    fr_long_thresh  : funding below this triggers long (default -0.0002, i.e. -0.02%/8h)
    fr_short_thresh : funding above this triggers short (default  0.0005, i.e.  0.05%/8h)
    """
    coin        = p.get('coin', 'ETH')
    long_thr    = p.get('fr_long_thresh',  -0.0001)   # 5th pct ETH = -0.000065
    short_thr   = p.get('fr_short_thresh',  0.0003)   # 95th pct ETH =  0.000462
    try:
        rate = _load_funding_rate_entry(df, coin)
        return _sig(rate < long_thr, rate > short_thr)
    except Exception:
        return pd.Series(0, index=df.index)


# ── Z-score enhanced entries ──────────────────────────────────────────────────

def entry_zscore_ema(df, p):
    """
    Z-score of (Close − EMA) mean reversion.

    Measures how far price has deviated from its EMA in standard-deviation units.
    Enter long when deviation is extreme negative (price well below EMA),
    enter short when extreme positive (price well above EMA).

    Params
    ------
    ema_trend      : EMA period (default 50)
    zscore_period  : rolling window for std calculation (default 20)
    zscore_threshold : entry trigger (default 2.0)
    """
    e   = ema(df, p.get('ema_trend', 50))
    dev = df['Close'] - e
    z   = zscore_of(dev, p.get('zscore_period', 20))
    thr = p.get('zscore_threshold', 2.0)
    return _sig(z < -thr, z > thr)


def entry_zscore_htf(df, p):
    """
    HTF Z-score mean reversion — reversion signal derived from the higher timeframe.

    Computes z-score of Close on the HTF (e.g. 4H), then forward-fills to LTF bars.
    When the HTF is at a z-score extreme, enter on the next LTF candle.
    Combines HTF-level overbought/oversold with LTF precision timing.

    Params
    ------
    htf_bars       : number of LTF bars per HTF candle (e.g. 48 = 4H on 5m)
    zscore_period  : rolling window on HTF bars (default 20)
    zscore_threshold : entry trigger (default 2.0)
    """
    from strategy_forge.signals.filter_signals import _htf_resample_rule
    htf_bars = p.get('htf_bars', 48)
    period   = p.get('zscore_period', 20)
    thr      = p.get('zscore_threshold', 2.0)
    try:
        rule = _htf_resample_rule(df, htf_bars)
        htf_close = df['Close'].resample(rule).last().dropna()
        htf_z = zscore_of(htf_close, period)
        df_idx = pd.to_datetime(df.index).tz_localize(None) if df.index.tz is not None else df.index
        htf_z.index = pd.to_datetime(htf_z.index).tz_localize(None)
        z = htf_z.reindex(df_idx, method='ffill').fillna(0)
        z.index = df.index
    except Exception:
        z = pd.Series(0.0, index=df.index)
    return _sig(z < -thr, z > thr)


# ── Registry ──────────────────────────────────────────────────────────────────

ENTRY_SIGNAL_REGISTRY = {
    # Momentum
    'rsi_reversion':      entry_rsi_reversion,
    'rsi_trend':          entry_rsi_trend,
    'macd_cross':         entry_macd_cross,
    'macd_zero_cross':    entry_macd_zero_cross,
    'kdj_reversion':      entry_kdj_reversion,
    'wavetrend':          entry_wavetrend,
    'mfi_reversion':      entry_mfi_reversion,
    'vrsi_reversion':     entry_vrsi_reversion,
    'fisher':             entry_fisher,
    'aroon_cross':        entry_aroon_cross,
    # Trend
    'ema_cross':          entry_ema_cross,
    'ema_price_cross':    entry_ema_price_cross,
    'supertrend':         entry_supertrend,
    'zlema_cross':        entry_zlema_cross,
    'ema_macd_cross':     entry_ema_macd_cross,
    # Volatility / structure
    'bb_reversion':       entry_bollinger_reversion,
    'bb_breakout':        entry_bollinger_breakout,
    'keltner_reversion':  entry_keltner_reversion,
    'squeeze_breakout':   entry_squeeze_breakout,
    'zscore_reversion':   entry_zscore_reversion,
    'fvg':                entry_fvg,
    'imbalance_zone':     entry_imbalance_zone,
    'fvg_zone_touch':     entry_fvg_zone_touch,
    # Volume
    'vwap_reversion':         entry_vwap_reversion,
    'cvd_cross':              entry_cvd_cross,
    'taker_momentum':         entry_taker_momentum,
    # New indicators
    'stoch_rsi_reversion':    entry_stoch_rsi_reversion,
    'williams_r_reversion':   entry_williams_r_reversion,
    'elder_ray':              entry_elder_ray,
    'dpo_reversion':          entry_dpo_reversion,
    'hma_cross':              entry_hma_cross,
    'parabolic_sar':          entry_parabolic_sar,
    'vortex_cross':           entry_vortex_cross,
    # Candle patterns
    'candle_engulfing':       entry_candle_engulfing,
    'candle_pin_bar':         entry_candle_pin_bar,
    # Order flow / structure
    'order_block':            entry_order_block,
    # Funding rate
    'funding_rate_mr':        entry_funding_rate_mr,
    # Z-score variants
    'zscore_ema':             entry_zscore_ema,
    'zscore_htf':             entry_zscore_htf,
}


def compute_entry_signal(name: str, df: pd.DataFrame, params: dict) -> pd.Series:
    fn = ENTRY_SIGNAL_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown entry signal: {name}")
    try:
        return fn(df, params)
    except Exception:
        return pd.Series(0, index=df.index)
