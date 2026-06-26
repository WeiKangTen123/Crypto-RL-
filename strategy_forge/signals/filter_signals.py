"""
filter_signals.py — registry of confirmation/filter functions.

Each function receives a DataFrame and params dict.
Returns a boolean pd.Series — True = signal is ALLOWED to pass through.
Compose multiple filters with &.
"""
import os
import pandas as pd
import numpy as np

from strategy_forge.indicators import (
    rsi, adx_dmi, ema, sma, supertrend, atr, bollinger, squeeze,
    taker_ratio, volume_zscore, hma, parabolic_sar, vortex, williams_r, obv,
    ob_imbalance
)

_DATASET_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dataset')


def filter_adx_trend(df, p) -> pd.Series:
    """Only trade when trend is strong (ADX above threshold)."""
    adx, _, _ = adx_dmi(df, p.get('adx_period', 14))
    return adx > p.get('adx_threshold', 25)


def filter_ema_trend_long(df, p) -> pd.Series:
    """Only long when price is above trend EMA."""
    e = ema(df, p.get('ema_trend', 200))
    return df['Close'] > e


def filter_ema_trend_short(df, p) -> pd.Series:
    """Only short when price is below trend EMA."""
    e = ema(df, p.get('ema_trend', 200))
    return df['Close'] < e


def filter_supertrend_direction(df, p) -> pd.Series:
    """Filter: supertrend must agree with direction (1=up allowed, -1=down allowed)."""
    _, direction = supertrend(df, p.get('st_period', 10), p.get('st_multiplier', 3.0))
    return direction == 1   # caller can invert for short-only


def filter_no_squeeze(df, p) -> pd.Series:
    """Block entries during active Bollinger/Keltner squeeze."""
    sq = squeeze(df, p.get('bb_period', 20), p.get('bb_std', 2.0),
                 p.get('kc_window', 20), p.get('kc_multiplier', 1.5))
    return ~sq


def filter_vol_expansion(df, p) -> pd.Series:
    """Require volume above rolling average × multiplier."""
    vol_ma = df['Volume'].rolling(p.get('vol_ma_period', 20)).mean()
    return df['Volume'] > vol_ma * p.get('vol_multiplier', 1.5)


def filter_atr_expansion(df, p) -> pd.Series:
    """Require current ATR above its own rolling average (volatility expansion)."""
    a = atr(df, p.get('atr_period', 14))
    atr_ma = a.rolling(p.get('vol_ma_period', 50)).mean()
    return a > atr_ma


def filter_rsi_not_extreme(df, p) -> pd.Series:
    """Block entries when RSI is already overbought or oversold."""
    r = rsi(df, p.get('rsi_period', 14))
    return (r > p.get('rsi_oversold', 30)) & (r < p.get('rsi_overbought', 70))


def filter_taker_confirmation(df, p) -> pd.Series:
    """Require taker buy ratio above midpoint to allow longs."""
    tr = taker_ratio(df, p.get('intensity_period', 20))
    return tr > 0.5


def filter_psar_trend(df, p) -> pd.Series:
    """Only allow longs when Parabolic SAR is bullish (price > SAR)."""
    direction = parabolic_sar(df, p.get('psar_acceleration', 0.02), p.get('psar_maximum', 0.2))
    return direction == 1


def filter_vortex_trend(df, p) -> pd.Series:
    """Allow entries only when VI+ > VI- (confirmed trend direction)."""
    vi_p, vi_m = vortex(df, p.get('vortex_period', 14))
    return vi_p > vi_m


def filter_hma_slope(df, p) -> pd.Series:
    """Only allow entries when HMA is sloping up (bullish momentum)."""
    h = hma(df, p.get('hma_period', 20))
    return h > h.shift(1)


def filter_williams_r_not_extreme(df, p) -> pd.Series:
    """Block entries when Williams %R is at extreme levels (already overbought/oversold)."""
    wr = williams_r(df, p.get('period', 14))
    return (wr > -90) & (wr < -10)


# ── MTF (Multi-Timeframe) filters — use pandas resample on DatetimeIndex ──────

def _htf_resample_rule(df: pd.DataFrame, htf_bars: int) -> str:
    """
    Compute the correct pandas resample rule from the base-TF DatetimeIndex.

    htf_bars is a bar-count multiplier (e.g. 48 on 5m data = 240 min = 4h).
    We derive the base-TF minutes from the index spacing so the rule is correct
    for ANY base timeframe (5m, 15m, 30m, 1h, etc.).
    Falls back to f'{htf_bars}h' on integer-indexed or malformed data, which
    remains correct when base TF is exactly 1h.
    """
    try:
        base_min = int((df.index[1] - df.index[0]).total_seconds() // 60)
        return f'{base_min * htf_bars}min'
    except Exception:
        return f'{htf_bars}h'


def filter_htf_ema_trend(df, p) -> pd.Series:
    """
    Multi-timeframe EMA trend filter.
    Resamples lower-TF data to a higher TF (htf_bars × bar size) internally.
    Only allows entries when price is above the HTF EMA — reduces counter-trend noise.
    e.g. on 1h data with htf_bars=4 → 4h EMA filter.

    Param key: 'htf_ema_period' (primary) or 'ema_trend_period' (fallback, used
    by ForgeStrategy entries registered via Phase 12 pipeline).
    """
    htf_bars = p.get('htf_bars', 4)
    # Accept both canonical key and the ForgeStrategy alias
    period   = p.get('htf_ema_period', p.get('ema_trend_period', 50))
    rule     = _htf_resample_rule(df, htf_bars)
    try:
        htf_close = df['Close'].resample(rule).last()
        htf_ema   = htf_close.ewm(span=period, adjust=False).mean()
        trend     = (htf_close > htf_ema).reindex(df.index, method='ffill').fillna(False)
    except Exception:
        trend = pd.Series(True, index=df.index)
    return trend


def filter_htf_supertrend(df, p) -> pd.Series:
    """
    Multi-timeframe Supertrend filter.
    Resamples to HTF (htf_bars × bar size) and checks Supertrend direction.
    Only allows entries when HTF Supertrend is bullish (direction = 1).
    """
    htf_bars  = p.get('htf_bars', 4)
    st_period = p.get('st_period', 10)
    st_mult   = p.get('st_multiplier', 3.0)
    rule      = _htf_resample_rule(df, htf_bars)
    try:
        htf = df[['High', 'Low', 'Close']].resample(rule).agg(
            {'High': 'max', 'Low': 'min', 'Close': 'last'}
        ).dropna()
        _, direction = supertrend(htf, st_period, st_mult)
        trend = (direction == 1).reindex(df.index, method='ffill').fillna(False)
    except Exception:
        trend = pd.Series(True, index=df.index)
    return trend


def filter_obv_trend(df, p) -> pd.Series:
    """
    OBV trend filter — only allow entries when On Balance Volume is above its SMA.
    Confirms that volume is accumulating in the direction of the trade.
    """
    o        = obv(df)
    period   = p.get('obv_period', 20)
    obv_sma  = o.rolling(period).mean()
    return o > obv_sma


def _load_funding_rate(df: pd.DataFrame, coin: str) -> pd.Series:
    """Load 4h funding rate parquet and forward-fill to df's index."""
    path = os.path.join(_DATASET_DIR, coin.upper(), '4h', 'funding_rate.parquet')
    fr = pd.read_parquet(path)
    if 'open_time' in fr.columns:
        fr = fr.set_index('open_time')
    fr.index = pd.to_datetime(fr.index, utc=True).tz_localize(None)
    df_idx = pd.to_datetime(df.index).tz_localize(None) if df.index.tz is not None else pd.to_datetime(df.index)
    rate = fr['funding_rate'].reindex(df_idx, method='ffill').fillna(0)
    rate.index = df.index
    return rate


def filter_funding_rate_bias(df, p) -> pd.Series:
    """
    Funding rate directional bias filter.

    Only allows LONG entries when funding rate < fr_long_threshold (shorts paying
    = market structurally long-friendly, squeeze potential for longs).

    Since ForgeStrategy is typically direction-restricted via 'direction' param,
    this filter acts as an additional regime gate: skip longs in funding bubbles.

    Params
    ------
    coin                : which coin's funding rate to load (default 'ETH')
    fr_long_threshold   : max funding rate to allow longs (default 0.0001 = 0.01%/8h)
    """
    coin = p.get('coin', 'ETH')
    threshold = p.get('fr_long_threshold', 0.0001)
    try:
        rate = _load_funding_rate(df, coin)
        return rate < threshold
    except Exception:
        return pd.Series(True, index=df.index)


def filter_dual_htf_trend(df, p) -> pd.Series:
    """
    Dual multi-timeframe EMA trend filter.
    Checks TWO higher timeframes simultaneously — both must agree on trend direction.

    Typical usage:
      5m base  → htf1_bars=12 (1h)  + htf2_bars=48 (4h)
      15m base → htf1_bars=4  (1h)  + htf2_bars=16 (4h)
      1h base  → htf1_bars=4  (4h)  + htf2_bars=24 (1d)
      4h base  → htf1_bars=6  (1d)  + htf2_bars omitted (single HTF)

    Returns True only when BOTH HTFs have Close above their EMA.
    """
    htf1_bars = p.get('htf1_bars', 12)
    htf2_bars = p.get('htf2_bars', 48)
    period    = p.get('htf_ema_period', p.get('ema_trend_period', 50))

    def _trend(bars):
        rule = _htf_resample_rule(df, bars)
        try:
            htf_close = df['Close'].resample(rule).last()
            htf_ema   = htf_close.ewm(span=period, adjust=False).mean()
            return (htf_close > htf_ema).reindex(df.index, method='ffill').fillna(False)
        except Exception:
            return pd.Series(True, index=df.index)

    return _trend(htf1_bars) & _trend(htf2_bars)


def filter_macro_regime(df, p) -> pd.Series:
    """
    Macro regime filter using the highest available HTF Supertrend.
    Resamples to the macro timeframe (macro_bars × base_bar_size) and checks
    Supertrend direction — only allows entries when macro trend is bullish.

    Typical: 5m × macro_bars=288 = 1d,  1h × macro_bars=168 = 7d (weekly)
    Falls back to True on any error (non-blocking on missing data).
    """
    macro_bars = p.get('macro_bars', 288)
    st_period  = p.get('st_period', 10)
    st_mult    = p.get('st_multiplier', 3.0)
    rule       = _htf_resample_rule(df, macro_bars)
    try:
        htf = df[['High', 'Low', 'Close']].resample(rule).agg(
            {'High': 'max', 'Low': 'min', 'Close': 'last'}
        ).dropna()
        if len(htf) < st_period + 5:
            return pd.Series(True, index=df.index)
        _, direction = supertrend(htf, st_period, st_mult)
        return (direction == 1).reindex(df.index, method='ffill').fillna(False)
    except Exception:
        return pd.Series(True, index=df.index)


def filter_ob_buy_pressure(df, p) -> pd.Series:
    """Only long if Order Book has strong bid pressure."""
    imb = ob_imbalance(df, level=p.get('ob_level', 1.0))
    return imb > p.get('ob_buy_threshold', 0.55)


def filter_ob_sell_pressure(df, p) -> pd.Series:
    """Only short if Order Book has strong ask pressure."""
    imb = ob_imbalance(df, level=p.get('ob_level', 1.0))
    return imb < p.get('ob_sell_threshold', 0.45)

# ── Registry ──────────────────────────────────────────────────────────────────

FILTER_REGISTRY = {
    'adx_trend':          filter_adx_trend,
    'ema_trend_long':     filter_ema_trend_long,
    'ema_trend_short':    filter_ema_trend_short,
    'supertrend_dir':     filter_supertrend_direction,
    'no_squeeze':         filter_no_squeeze,
    'vol_expansion':      filter_vol_expansion,
    'atr_expansion':      filter_atr_expansion,
    'rsi_not_extreme':    filter_rsi_not_extreme,
    'taker_confirm':      filter_taker_confirmation,
    'psar_trend':         filter_psar_trend,
    'vortex_trend':       filter_vortex_trend,
    'hma_slope':          filter_hma_slope,
    'wr_not_extreme':     filter_williams_r_not_extreme,
    # MTF filters (new — require DatetimeIndex)
    'htf_ema_trend':      filter_htf_ema_trend,
    'htf_supertrend':     filter_htf_supertrend,
    'obv_trend':          filter_obv_trend,
    'ob_buy_pressure':    filter_ob_buy_pressure,
    'ob_sell_pressure':   filter_ob_sell_pressure,
    'funding_rate_bias':  filter_funding_rate_bias,
    # Multi-TF regime filters
    'dual_htf_trend':     filter_dual_htf_trend,
    'macro_regime':       filter_macro_regime,
}


def compute_filter(name: str, df: pd.DataFrame, params: dict) -> pd.Series:
    fn = FILTER_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown filter: {name}")
    try:
        return fn(df, params).fillna(False)
    except Exception:
        return pd.Series(True, index=df.index)
