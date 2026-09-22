"""
Generate supervised training labels for BetaEngine and AlphaEngine.

Beta labels   : per-bar forward regime (Bull/Bear/Range) + vol class + trend strength
                + regime_stability + transition_prob  [TIA v3: vol_class, transition_prob]
Alpha labels  : per-entry-bar oracle trade outcomes
                (return, MFE, MAE, TP/SL probability, hold bars, sl_hit, exp_vol,
                 exp_variance, tail_risk, exp_max_dd)  [TIA v3: 3 new risk labels]

All labels use forward-looking data and are ONLY valid for supervised training
on historical data.  They are never computed at inference time.

Usage
─────
    from DRL_BTC.training.label_generator import generate_beta_labels, generate_alpha_labels

    beta_df  = generate_beta_labels(feat_train, close_train)
    alpha_df = generate_alpha_labels(feat_train, close_train)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from DRL_BTC.config import BETA_STABILITY_HORIZON

# Regime class constants (match BetaEngine.BULL / BEAR / RANGE)
BULL  = 0
BEAR  = 1
RANGE = 2

# Vol class constants (match BetaEngine.VOL_LOW / VOL_MED / VOL_HIGH)
VOL_LOW  = 0
VOL_MED  = 1
VOL_HIGH = 2

LONG_DIR  =  1
SHORT_DIR = -1

# Vol class thresholds (annualised-equivalent on 1h bars)
_VOL_MED_THRESH  = 0.005   # std(log_ret, 24h) > 0.005 = medium vol
_VOL_HIGH_THRESH = 0.012   # std(log_ret, 24h) > 0.012 = high vol
# Transition horizon for P(regime changes)
_TRANSITION_HORIZON = 24   # bars (= 24h)


def generate_beta_labels(
    features:     pd.DataFrame,
    close:        pd.Series,
    fwd_h:        int   = 24,     # forward horizon in bars (24h)
    bull_thresh:  float = 0.010,  # fwd return > +1% → BULL
    bear_thresh:  float = -0.010, # fwd return < -1% → BEAR
) -> pd.DataFrame:
    """
    Per-bar regime labels for BetaEngine supervised training.

    Returns DataFrame indexed by INTEGER position (0..len-1) with:
        regime            : int64  [0=BULL, 1=BEAR, 2=RANGE]
        vol_class         : int64  [0=LOW, 1=MED, 2=HIGH]   [TIA v3 NEW]
        fwd_vol           : float  forward realized vol over next fwd_h bars (clipped 0-0.20)
        trend_str         : float  trend strength proxy in [0, 1]
        regime_stability  : float  1.0 if regime stays same for next BETA_STABILITY_HORIZON bars
        transition_prob   : float  1.0 if regime changes within next 24 bars [TIA v3 NEW]
        valid             : bool   True where forward data exists (last fwd_h bars are False)
    """
    n = len(close)
    close_arr = close.values.astype(np.float64)

    # ── Forward return at fwd_h horizon ──────────────────────────────────────
    fwd_ret = np.zeros(n, dtype=np.float64)
    for i in range(n - fwd_h):
        fwd_ret[i] = close_arr[i + fwd_h] / close_arr[i] - 1.0

    regime = np.where(fwd_ret > bull_thresh, BULL,
             np.where(fwd_ret < bear_thresh, BEAR, RANGE)).astype(np.int64)

    # ── Forward realized vol: std of log-returns over next fwd_h bars ────────
    log_ret = np.log(np.maximum(close_arr[1:] / close_arr[:-1], 1e-10))
    fwd_vol = np.zeros(n, dtype=np.float64)
    for i in range(n - fwd_h):
        fwd_vol[i] = float(np.std(log_ret[i: i + fwd_h]))
    fwd_vol = np.clip(fwd_vol, 0.0, 0.20)

    # ── Trend strength: ADX from features (prefer 4h, fallback to 1h) ────────
    adx_col = next(
        (c for c in features.columns if "adx" in c and "4h" in c), None
    )
    if adx_col is None:
        adx_col = next((c for c in features.columns if "adx" in c), None)
    trend_str = features[adx_col].clip(0, 1).values if adx_col else np.full(n, 0.5)

    # ── Vol class: discretise forward vol into 3 bins ────────────────────────
    vol_class = np.where(
        fwd_vol >= _VOL_HIGH_THRESH, VOL_HIGH,
        np.where(fwd_vol >= _VOL_MED_THRESH, VOL_MED, VOL_LOW)
    ).astype(np.int64)

    # ── Regime stability: does regime label stay the same for next N bars? ────
    # 1.0 = stable, 0.0 = regime changes within BETA_STABILITY_HORIZON bars
    stability_horizon = BETA_STABILITY_HORIZON
    regime_stability  = np.zeros(n, dtype=np.float64)
    for i in range(n - stability_horizon):
        future_regimes = regime[i + 1: i + stability_horizon + 1]
        regime_stability[i] = 1.0 if np.all(future_regimes == regime[i]) else 0.0

    # ── Transition probability: does regime change within _TRANSITION_HORIZON? ──
    # 1.0 = regime changes (complement of stability for a shorter horizon).
    # Useful for "how likely is this regime to end soon?"
    transition_prob = np.zeros(n, dtype=np.float64)
    for i in range(n - _TRANSITION_HORIZON):
        future_regimes = regime[i + 1: i + _TRANSITION_HORIZON + 1]
        transition_prob[i] = 0.0 if np.all(future_regimes == regime[i]) else 1.0

    # ── Valid mask ─────────────────────────────────────────────────────────────
    valid = np.ones(n, dtype=bool)
    valid[n - fwd_h:] = False   # no forward data for last fwd_h bars

    return pd.DataFrame({
        "regime":           regime,
        "vol_class":        vol_class,
        "fwd_vol":          fwd_vol,
        "trend_str":        trend_str,
        "regime_stability": regime_stability,
        "transition_prob":  transition_prob,
        "valid":            valid,
    })   # integer RangeIndex: 0..n-1


def generate_alpha_labels(
    features:     pd.DataFrame,
    close:        pd.Series,
    sl_mult:      float = 1.5,    # oracle SL: 1.5× ATR from entry
    tp_mult:      float = 3.0,    # oracle TP: 3.0× ATR from entry
    max_hold:     int   = 96,     # 4-day timeout
    entry_thresh: float = 0.10,   # composite signal threshold
) -> pd.DataFrame:
    """
    Per-entry-bar oracle trade outcome labels for AlphaEngine supervised training.

    Simulates an oracle trade at each bar where the composite direction signal
    fires, using fixed SL/TP multipliers, and records the actual outcome.

    Returns DataFrame indexed by INTEGER position with:
        direction    : int    (1=LONG, -1=SHORT)
        trade_return : float  signed PnL fraction (e.g. +0.03 = +3%)
        mfe          : float  max favorable excursion (positive fraction)
        mae          : float  max adverse excursion from entry (positive fraction)
        tp_hit       : float  1.0 if TP triggered, 0.0 otherwise
        sl_hit       : float  1.0 if SL triggered, 0.0 otherwise
        exp_vol      : float  std of log-returns over hold period
        hold_bars    : float  duration in bars until exit
        exp_variance : float  variance of log-returns over hold period  [TIA v3 NEW]
        tail_risk    : float  max intraperiod drawdown from rolling peak  [TIA v3 NEW]
        exp_max_dd   : float  peak-to-trough max cumulative drawdown     [TIA v3 NEW]
    """
    # Resolve ATR column
    atr_col = next((c for c in features.columns if c == "atr_pct_1h"), None)
    if atr_col is None:
        atr_col = next(
            (c for c in features.columns if "atr_pct" in c and "1h" in c), None
        )
    if atr_col is None:
        raise ValueError("generate_alpha_labels: atr_pct_1h feature not found")

    atr_frac  = features[atr_col].values.astype(np.float64) * 0.10   # denormalize

    macro    = features.get("macro_score", pd.Series(0.0, index=features.index)).values
    swing    = features.get("swing_score", pd.Series(0.0, index=features.index)).values
    regime_s = features.get("regime_score", pd.Series(0.0, index=features.index)).values
    combined = 0.65 * macro + 0.35 * swing

    close_arr = close.values.astype(np.float64)
    log_ret   = np.log(np.maximum(close_arr[1:] / close_arr[:-1], 1e-10))
    n         = len(close_arr)

    records: list[dict] = []

    for i in range(n - max_hold - 2):
        comb = combined[i]
        reg  = regime_s[i]

        if abs(comb) <= entry_thresh or reg <= 0.0:
            continue

        direction = LONG_DIR if comb > 0.0 else SHORT_DIR
        entry_px  = close_arr[i]
        atr       = max(float(atr_frac[i]), 1e-6)

        sl_price = entry_px * (1.0 - direction * sl_mult * atr)
        tp_price = entry_px * (1.0 + direction * tp_mult * atr)

        mfe            = 0.0
        mae            = 0.0
        exit_bar       = i + max_hold  # default: timeout
        exit_reason    = "timeout"
        # TIA v3: rolling high-water mark for tail_risk computation
        rolling_peak   = entry_px   # LONG: tracks max price; SHORT: tracks min price
        max_tail_risk  = 0.0        # max drawdown from rolling peak (direction-adjusted)

        for j in range(i + 1, min(i + max_hold + 1, n)):
            px     = close_arr[j]
            unreal = (px / entry_px - 1.0) * direction
            if unreal > mfe:  mfe = unreal
            if -unreal > mae: mae = -unreal

            # TIA v3: track rolling peak and compute intraperiod peak-to-trough dd
            if direction == LONG_DIR:
                if px > rolling_peak:
                    rolling_peak = px
                dd_from_peak = (rolling_peak - px) / (rolling_peak + 1e-8)
            else:
                if px < rolling_peak:
                    rolling_peak = px   # rolling valley for short
                dd_from_peak = (px - rolling_peak) / (rolling_peak + 1e-8)
            if dd_from_peak > max_tail_risk:
                max_tail_risk = dd_from_peak

            sl_triggered = (direction == LONG_DIR  and px <= sl_price) or \
                           (direction == SHORT_DIR and px >= sl_price)
            tp_triggered = (direction == LONG_DIR  and px >= tp_price) or \
                           (direction == SHORT_DIR and px <= tp_price)

            if sl_triggered:
                exit_bar    = j
                exit_reason = "sl"
                break
            if tp_triggered:
                exit_bar    = j
                exit_reason = "tp"
                break

        if exit_reason == "sl":
            trade_return = (sl_price / entry_px - 1.0) * direction
        elif exit_reason == "tp":
            trade_return = (tp_price / entry_px - 1.0) * direction
        else:
            trade_return = (close_arr[min(exit_bar, n - 1)] / entry_px - 1.0) * direction

        # ── Risk labels from hold period log-returns ──────────────────────────
        hold_len     = max(exit_bar - i, 1)
        lr_slice     = log_ret[i: i + hold_len]
        has_slice    = len(lr_slice) > 1
        exp_vol      = float(np.std(lr_slice))  if has_slice else 0.0
        exp_variance = float(np.var(lr_slice))  if has_slice else 0.0  # TIA v3
        tail_risk    = float(max_tail_risk)                             # TIA v3
        exp_max_dd   = float(max_tail_risk)                             # TIA v3: same source; separate head learns distinct repr

        records.append({
            "bar_idx":      i,
            "direction":    direction,
            "trade_return": float(trade_return),
            "mfe":          float(mfe),
            "mae":          float(mae),
            "tp_hit":       1.0 if exit_reason == "tp" else 0.0,
            "sl_hit":       1.0 if exit_reason == "sl" else 0.0,
            "exp_vol":      float(exp_vol),
            "hold_bars":    float(exit_bar - i),
            "exp_variance": exp_variance,
            "tail_risk":    tail_risk,
            "exp_max_dd":   exp_max_dd,
        })

    if not records:
        return pd.DataFrame(
            columns=["direction", "trade_return", "mfe", "mae",
                     "tp_hit", "sl_hit", "exp_vol", "hold_bars",
                     "exp_variance", "tail_risk", "exp_max_dd"]
        )

    return pd.DataFrame(records).set_index("bar_idx")
