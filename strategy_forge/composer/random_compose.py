"""
random_compose.py — generate random StrategyDNA instances.

A random strategy is assembled by:
  1. Picking one entry signal at random from ENTRY_SIGNAL_REGISTRY
  2. Picking 0–2 filters at random from FILTER_REGISTRY
  3. Picking one exit method at random from EXIT_REGISTRY
  4. Sampling all required params randomly from DEFAULT_RANGES
"""
import random
from typing import List, Optional

from strategy_forge.signals.entry_signals import ENTRY_SIGNAL_REGISTRY
from strategy_forge.signals.filter_signals import FILTER_REGISTRY
from strategy_forge.signals.exit_signals   import EXIT_REGISTRY
from strategy_forge.params.ranges          import DEFAULT_RANGES, sample_params
from strategy_forge.composer.dna           import StrategyDNA


# Params needed by each module — used to sample only what's required
_ENTRY_PARAMS = {
    'rsi_reversion':   ['rsi_period', 'rsi_oversold', 'rsi_overbought'],
    'rsi_trend':       ['rsi_period', 'rsi_threshold'],
    'macd_cross':      ['macd_fast', 'macd_slow', 'macd_signal'],
    'macd_zero_cross': ['macd_fast', 'macd_slow', 'macd_signal'],
    'kdj_reversion':   ['kdj_period', 'kdj_oversold', 'kdj_overbought'],
    'wavetrend':       ['wt_n1', 'wt_n2', 'wt_oversold', 'wt_overbought'],
    'mfi_reversion':   ['mfi_period'],
    'vrsi_reversion':  ['vrsi_period', 'vrsi_oversold', 'vrsi_overbought'],
    'fisher':          ['period'],
    'aroon_cross':     ['aroon_period', 'aroon_threshold'],
    'ema_cross':       ['ema_fast', 'ema_slow'],
    'ema_price_cross': ['ema_period'],
    'supertrend':      ['st_period', 'st_multiplier'],
    'zlema_cross':     ['ema_fast', 'ema_slow'],
    'bb_reversion':    ['bb_period', 'bb_std'],
    'bb_breakout':     ['bb_period', 'bb_std'],
    'keltner_reversion':['kc_window', 'kc_multiplier'],
    'squeeze_breakout':['bb_period', 'bb_std', 'kc_window', 'kc_multiplier'],
    'zscore_reversion':['zscore_period', 'zscore_threshold'],
    'fvg':             [],
    'imbalance_zone':  ['imb_threshold'],
    'fvg_zone_touch':  ['fvg_htf_bars', 'fvg_zone_timeout', 'fvg_cooldown', 'fvg_min_pct'],
    'vwap_reversion':      ['vwap_period', 'vwap_std_mult'],
    'cvd_cross':           ['cvd_window'],
    'taker_momentum':      ['intensity_period', 'taker_threshold'],
    # New indicators
    'stoch_rsi_reversion': ['rsi_period', 'smoothing', 'rsi_oversold', 'rsi_overbought'],
    'williams_r_reversion':['period'],
    'elder_ray':           ['period', 'adx_period', 'adx_threshold'],
    'dpo_reversion':       ['period', 'lookback', 'zscore_threshold'],
    'hma_cross':           ['ema_fast', 'ema_slow'],
    'parabolic_sar':       ['psar_acceleration', 'psar_maximum'],
    'vortex_cross':        ['period'],
    # Candle patterns
    'candle_engulfing':    [],
    'candle_pin_bar':      [],
    # Order flow / structure
    'order_block':         ['atr_period', 'atr_multiplier', 'ob_lookback'],
    # Funding rate mean reversion
    'funding_rate_mr':     ['fr_long_thresh', 'fr_short_thresh'],
    # Z-score variants
    'zscore_ema':          ['ema_trend', 'zscore_period', 'zscore_threshold'],
    'zscore_htf':          ['htf_bars', 'zscore_period', 'zscore_threshold'],
}

_FILTER_PARAMS = {
    'adx_trend':        ['adx_period', 'adx_threshold'],
    'ema_trend_long':   ['ema_trend'],
    'ema_trend_short':  ['ema_trend'],
    'supertrend_dir':   ['st_period', 'st_multiplier'],
    'no_squeeze':       ['bb_period', 'bb_std', 'kc_window', 'kc_multiplier'],
    'vol_expansion':    ['vol_ma_period', 'vol_multiplier'],
    'atr_expansion':    ['atr_period', 'vol_ma_period'],
    'rsi_not_extreme':  ['rsi_period', 'rsi_oversold', 'rsi_overbought'],
    'taker_confirm':    ['intensity_period'],
    'psar_trend':       ['psar_acceleration', 'psar_maximum'],
    'vortex_trend':     ['vortex_period'],
    'hma_slope':        ['hma_period'],
    'wr_not_extreme':   ['period'],
    # MTF filters
    'htf_ema_trend':      ['htf_bars', 'htf_ema_period'],
    'htf_supertrend':     ['htf_bars', 'st_period', 'st_multiplier'],
    'obv_trend':          ['obv_period'],
    'funding_rate_bias':  ['fr_long_threshold'],
    # Dual-HTF and macro regime filters
    'dual_htf_trend':     ['htf1_bars', 'htf2_bars', 'htf_ema_period'],
    'macro_regime':       ['macro_bars', 'st_period', 'st_multiplier'],
    # Order book pressure filters (no tunable params — use defaults)
    'ob_buy_pressure':    [],
    'ob_sell_pressure':   [],
}

_EXIT_PARAMS = {
    'atr_tp_sl':        ['atr_period', 'tp_atr_mult', 'sl_atr_mult'],
    'pct_tp_sl':        ['tp_pct', 'sl_pct'],
    'rr_ratio':         ['sl_pct', 'tp_rr'],
    'max_hold':         ['max_hold_bars'],
    'atr_tp_sl_hold':   ['atr_period', 'tp_atr_mult', 'sl_atr_mult', 'max_hold_bars'],
    'chandelier':       ['atr_period', 'atr_multiplier'],
    'chandelier_tp':    ['atr_period', 'atr_multiplier', 'tp_atr_mult'],
    'supertrend_trail': ['st_period', 'st_multiplier'],
    'tight_atr':        ['atr_period', 'sl_atr_mult', 'tp_atr_mult'],
    'breakeven_trail':  ['atr_period', 'sl_atr_mult', 'be_trigger_mult', 'atr_multiplier'],
    'rsi_exit':         ['rsi_period', 'rsi_threshold'],
    'trailing_tp':      ['atr_period', 'sl_atr_mult', 'tp_activation_mult', 'tp_trail_mult'],
    'psar_trail':       ['psar_acceleration', 'psar_maximum'],
    'vol_adaptive_sl':  ['atr_period', 'sl_atr_mult', 'tp_atr_mult', 'vol_ma_period'],
}


def _collect_param_names(entry: str, filters: List[str], exit_method: str) -> List[str]:
    names = set()
    names.update(_ENTRY_PARAMS.get(entry, []))
    for f in filters:
        names.update(_FILTER_PARAMS.get(f, []))
    names.update(_EXIT_PARAMS.get(exit_method, []))
    return list(names)


def random_dna(df=None, seed: int = None,
               max_filters: int = 2,
               entry: str = None,
               filters: List[str] = None,
               exit_method: str = None) -> StrategyDNA:
    """
    Generate one random StrategyDNA.

    Parameters
    ----------
    df          : DataFrame to bind (can be None — call .generate_signals() later)
    seed        : random seed for reproducibility
    max_filters : maximum number of filters to combine (0–2)
    entry / filters / exit_method : pin specific choices, rest are random
    """
    rng = random.Random(seed)

    chosen_entry  = entry       or rng.choice(list(ENTRY_SIGNAL_REGISTRY.keys()))
    chosen_exit   = exit_method or rng.choice(list(EXIT_REGISTRY.keys()))

    if filters is not None:
        chosen_filters = filters
    else:
        n_filters = rng.randint(0, max_filters)
        chosen_filters = rng.sample(list(FILTER_REGISTRY.keys()), k=n_filters)

    param_names = _collect_param_names(chosen_entry, chosen_filters, chosen_exit)
    params = sample_params(param_names, seed=seed)

    # Validate fast < slow constraints
    for fast_k, slow_k, gap in [
        ('ema_fast', 'ema_slow', 5),
        ('macd_fast', 'macd_slow', 5),
        ('hma_fast', 'hma_slow', 5),
    ]:
        if fast_k in params and slow_k in params:
            if params[fast_k] >= params[slow_k]:
                params[fast_k] = max(3, params[slow_k] - gap)
    if 'wt_n1' in params and 'wt_n2' in params:
        if params['wt_n1'] >= params['wt_n2']:
            params['wt_n1'] = max(3, params['wt_n2'] - 3)

    return StrategyDNA(
        df if df is not None else _placeholder_df(),
        entry=chosen_entry,
        filters=chosen_filters,
        exit_method=chosen_exit,
        params=params,
    )


def random_population(df, size: int = 50, seed: int = 42,
                      max_filters: int = 2) -> List[StrategyDNA]:
    """Generate a list of `size` random StrategyDNA instances."""
    rng = random.Random(seed)
    return [random_dna(df, seed=rng.randint(0, 2**31), max_filters=max_filters)
            for _ in range(size)]


def _placeholder_df():
    import pandas as pd
    return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
