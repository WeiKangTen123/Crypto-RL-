"""
params/ranges.py — canonical parameter search space for strategy_forge.

This is the single source of truth for all tunable parameter ranges.
finetune.py imports from here; add new params here first.
"""
import random

DEFAULT_RANGES = {
    # ── Generic ──────────────────────────────────────────────────────────────
    'period':               (5,    50),
    'length':               (5,    50),
    'lookback':             (5,    50),
    'smoothing':            (2,    20),
    # ── MACD ─────────────────────────────────────────────────────────────────
    'fast':                 (3,    30),
    'slow':                 (15,  100),
    'signal':               (3,    20),
    'macd_fast':            (3,    30),
    'macd_slow':            (15,  100),
    'macd_signal':          (3,    20),
    'fast_period':          (3,    30),
    'slow_period':          (15,  100),
    # ── KDJ ──────────────────────────────────────────────────────────────────
    'kdj_period':           (5,    30),
    'kdj_oversold':         (10,   40),
    'kdj_overbought':       (60,   90),
    # ── RSI ──────────────────────────────────────────────────────────────────
    'rsi_period':           (5,    30),
    'rsi_window':           (5,    30),
    'rsi_oversold':         (20,   40),
    'rsi_overbought':       (60,   80),
    'rsi_low':              (20,   40),
    'rsi_high':             (60,   80),
    'rsi_lower':            (20,   40),
    'rsi_upper':            (60,   80),
    'rsi_threshold':        (30,   70),
    'vrsi_period':          (5,    30),
    'vrsi_oversold':        (15,   35),
    'vrsi_overbought':      (65,   85),
    # ── EMA / SMA ────────────────────────────────────────────────────────────
    'ema_fast':             (5,    30),
    'ema_slow':             (20,  200),
    'ema_med':              (10,   60),
    'ema_period':           (10,  200),
    'ema_trend':            (50,  300),
    'ema_trend_4h':         (50,  300),
    'ema_window':           (5,    50),
    'ema_speed_period':     (3,    20),
    'ema_slope_thresh':     (0.0,  2.0),
    'trend_ema_period':     (50,  300),
    'sma_period':           (5,    50),
    'sma_macro':            (50,  300),
    'sma_macro_period':     (50,  300),
    'major_period':         (10,   50),
    'minor_period':         (5,    30),
    # ── ADX ──────────────────────────────────────────────────────────────────
    'adx_period':           (7,    30),
    'adx_threshold':        (15,   40),
    'adx_threshold_1h':     (15,   40),
    'adx_threshold_4h':     (15,   40),
    # ── ATR / Multipliers ────────────────────────────────────────────────────
    'atr_period':           (5,    30),
    'atr_multiplier':       (1.0,  6.0),
    'atr_multiplier_sl':    (0.5,  3.0),
    'atr_multiplier_tp':    (1.0,  8.0),
    'multiplier':           (1.0,  6.0),
    'multiplier_l1':        (1.0, 10.0),
    'multiplier_l2':        (1.0, 15.0),
    'multiplier_l3':        (1.0, 15.0),
    'tp_atr_mult':          (1.0,  8.0),
    'sl_atr_mult':          (0.5,  3.0),
    'sl_atr_multiplier':    (0.5,  3.0),
    'sl_multiplier':        (0.5,  3.0),
    'tp_multiplier':        (1.0,  8.0),
    'kc_multiplier':        (1.0,  4.0),
    'st_multiplier':        (1.0,  5.0),
    'supertrend_multiplier':(1.0,  5.0),
    # ── Bollinger / Keltner ──────────────────────────────────────────────────
    'bb_period':            (10,   50),
    'bb_std':               (1.0,  3.5),
    'bbw_sma_period':       (10,   50),
    'kc_window':            (10,   50),
    'kc_atr_window':        (5,    30),
    # ── VWAP ─────────────────────────────────────────────────────────────────
    'vwap_period':          (10,  100),
    'vwap_std_mult':        (0.5,  3.0),
    # ── Other indicators ─────────────────────────────────────────────────────
    'st_period':            (5,    30),
    'supertrend_length':    (5,    30),
    'zlema_period':         (5,    50),
    'zscore_period':        (20,  200),
    'zscore_threshold':     (0.5,  3.0),
    'z_period':             (10,  100),
    'z_threshold':          (0.5,  3.0),
    'aroon_period':         (10,   50),
    'aroon_threshold':      (50,   80),
    'mfi_period':           (5,    30),
    'wt_n1':                (5,    20),
    'wt_n2':                (10,   50),
    'wt_oversold':          (-80, -40),
    'wt_overbought':        (40,   80),
    'pivot_window':         (5,    30),
    'cvd_window':           (5,    50),
    'divergence_lookback':  (5,    30),
    'vol_lookback':         (5,    50),
    'vol_ma_period':        (5,    50),
    'intensity_period':     (5,    30),
    'intensity_std':        (1.0,  3.0),
    'pullback_lookback':    (2,    10),
    'swing_lookback':       (5,    30),
    'low_lookback':         (5,    50),
    'taker_threshold':      (0.5,  0.7),
    'taker_ratio_threshold':(0.5,  0.7),
    'taker_high_threshold': (0.5,  0.75),
    'taker_low_threshold':  (0.3,  0.55),
    'ob_volume_mult':       (1.0,  3.0),
    'fvg_min_pct':          (0.001,0.05),
    'min_gap_pct':          (0.001,0.05),
    'imb_threshold':        (0.0,  0.015),
    'fvg_htf_bars':         (12,   96),    # 5m*48=4h, 5m*12=1h, 5m*96=8h
    'fvg_zone_timeout':     (3,    15),    # HTF bars before zone expires
    'fvg_cooldown':         (12,   96),    # base-TF bars between signals
    'fvma_period':          (3,    20),
    # ── SL / TP / Hold ───────────────────────────────────────────────────────
    'sl_pct':               (0.01, 0.20),
    'stop_loss_pct':        (0.01, 0.10),
    'take_profit_pct':      (0.02, 0.20),
    'tp_pct':               (0.01, 0.15),
    'tp_rr':                (1.0,  5.0),
    'tp_rr_ratio':          (1.0,  5.0),
    'rv_threshold':         (0.01, 0.10),
    'sl_z_threshold':       (0.5,  3.0),
    'touch_band':           (0.001,0.02),
    'peak_retrace_pct':     (0.3,  0.9),
    'retrace_depth':        (0.3,  0.9),
    'vol_threshold':        (0.5,  3.0),
    'vol_multiplier':       (1.0,  3.0),
    'vol_sma_period':       (5,    50),
    'deviation_pct':        (0.005,0.05),
    'max_hold_bars':        (12,  200),
    'entry_window':         (1,    20),
    # ── WAE ──────────────────────────────────────────────────────────────────
    'wae_sensitivity':      (50,  300),
    'wae_fast_len':         (5,    30),
    'wae_slow_len':         (20,   80),
    'wae_bb_len':           (10,   50),
    'wae_bb_mult':          (1.0,  3.0),
    'wae_deadzone':         (5,    50),
    # ── T3 / Stiff ────────────────────────────────────────────────────────────
    't3_length':            (5,    50),
    't3_vf':                (0.1,  1.0),
    'stiff_len':            (20,  100),
    'stiff_threshold':      (0.5,  1.0),
    # ── TII ──────────────────────────────────────────────────────────────────
    'tii_lower':            (20,   45),
    'tii_upper':            (55,   80),
    # ── Squeeze ──────────────────────────────────────────────────────────────
    'squeeze_period':       (10,   30),
    # ── Stochastic RSI ───────────────────────────────────────────────────────
    'stoch_rsi_period':     (5,    30),
    'stoch_smooth_k':       (2,    5),
    'stoch_smooth_d':       (2,    5),
    # ── Williams %R ──────────────────────────────────────────────────────────
    'wr_period':            (5,    30),
    # ── HMA ──────────────────────────────────────────────────────────────────
    'hma_fast':             (5,    30),
    'hma_slow':             (20,  100),
    'hma_period':           (10,   80),
    # ── Parabolic SAR ────────────────────────────────────────────────────────
    'psar_acceleration':    (0.01, 0.05),
    'psar_maximum':         (0.1,  0.4),
    # ── Vortex ───────────────────────────────────────────────────────────────
    'vortex_period':        (10,   30),
    # ── Elder Ray ────────────────────────────────────────────────────────────
    'elder_ray_period':     (8,    30),
    # ── DPO ──────────────────────────────────────────────────────────────────
    'dpo_period':           (10,   50),
    # ── Chandelier ───────────────────────────────────────────────────────────
    'chandelier_period':    (5,    30),
    'chandelier_mult':      (1.5,  5.0),
    # ── MTF (Multi-Timeframe) ────────────────────────────────────────────────
    'htf_bars':             (4,   288),   # HTF multiplier: allows 1H up to 1D scaling from 5m/15m charts
    'htf_ema_period':       (20,  200),   # EMA period on the higher timeframe
    'ema_trend_period':     (20,  200),   # alias used by Phase-12 ForgeStrategy entries
    # Dual-HTF and macro regime params
    'htf1_bars':            (4,    48),   # first  HTF level (e.g. 12×5m=1h, 4×1h=4h)
    'htf2_bars':            (12,  288),   # second HTF level (e.g. 48×5m=4h, 24×1h=1d)
    'macro_bars':           (48,  288),   # macro  HTF level (e.g. 288×5m=1d, 168×1h=1w)
    # ── OBV ──────────────────────────────────────────────────────────────────
    'obv_period':           (10,   50),
    # ── Order blocks ─────────────────────────────────────────────────────────
    'ob_lookback':          (2,    10),
    # ── Breakeven trail ──────────────────────────────────────────────────────
    'be_trigger_mult':      (0.3,  2.0),
    # ── Trailing TP ──────────────────────────────────────────────────────────
    'tp_activation_mult':   (0.5,  3.0),
    'tp_trail_mult':        (0.3,  2.0),
    # ── Funding rate ─────────────────────────────────────────────────────────
    'fr_long_thresh':       (-0.001, 0.0),
    'fr_short_thresh':      (0.0003, 0.002),
    'fr_long_threshold':    (-0.001, 0.0003),
}


def sample_params(param_names: list, seed: int = None) -> dict:
    """
    Randomly sample one value per param name from DEFAULT_RANGES.
    Integer range → int, float range → float.
    """
    rng = random.Random(seed)
    out = {}
    for name in param_names:
        if name not in DEFAULT_RANGES:
            continue
        lo, hi = DEFAULT_RANGES[name]
        if isinstance(lo, int) and isinstance(hi, int):
            out[name] = rng.randint(lo, hi)
        else:
            out[name] = round(rng.uniform(float(lo), float(hi)), 4)
    return out
