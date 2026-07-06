"""
frequency_utils.py — Detect bar frequency and map to thresholds.

Provides:
  - Auto-detection from bar timestamps
  - Frequency classification (HFT / Intraday / Swing / Position)
  - Threshold mapping per frequency band
"""

import pandas as pd
import numpy as np


def detect_frequency(timestamps):
    """
    Auto-detect frequency from median bar spacing.

    Args:
        timestamps: pd.DatetimeIndex or list of pd.Timestamp

    Returns:
        frequency_str: '5m', '15m', '30m', '1h', '4h', '1d', or '?' if unknown
    """
    if not hasattr(timestamps, '__len__') or len(timestamps) < 2:
        return '?'

    ts = pd.DatetimeIndex(timestamps)
    diffs = ts.to_series().diff().dropna()
    if len(diffs) == 0:
        return '?'

    # Median bar spacing in seconds
    median_secs = float(diffs.dt.total_seconds().median())

    # Classify by duration (with tolerance ±10%)
    freq_map = {
        300: '5m',
        900: '15m',
        1800: '30m',
        3600: '1h',
        14400: '4h',
        86400: '1d',
    }

    # Find closest match
    best_freq = '?'
    best_dist = float('inf')
    for target_secs, freq_str in freq_map.items():
        dist = abs(median_secs - target_secs)
        if dist < best_dist:
            best_dist = dist
            best_freq = freq_str

    # Only accept if within ±10% tolerance
    if best_dist < median_secs * 0.1:
        return best_freq
    return '?'


def classify_frequency(frequency):
    """
    Classify frequency into tier for threshold lookups.

    Args:
        frequency: '5m', '15m', '30m', '1h', '4h', '1d', etc.

    Returns:
        tier: 'HFT', 'Intraday', 'Swing', 'Position', or None if unknown
    """
    tier_map = {
        '5m':  'HFT',
        '15m': 'HFT',
        '30m': 'Intraday',
        '1h':  'Swing',
        '4h':  'Swing',
        '1d':  'Position',
        '1D':  'Position',
    }
    return tier_map.get(frequency, None)


# ── SignalHive Threshold Standards ──────────────────────────────────────

THRESHOLDS = {
    'HFT': {
        'worst_daily_loss':   -0.02,      # T1-04: ≤ -2%
        'sample_size_min':    1000,       # T1-07: ≥ 1000 trades
        'cost_ratio_max':     0.50,       # T1-10: ≤ 50%
        'wf_efficiency_min':  0.40,       # T2-01: ≥ 0.4
        'hit_rate_min':       0.50,       # T3-01: ≥ 50%
    },
    'Intraday': {
        'worst_daily_loss':   -0.04,      # T1-04: ≤ -4%
        'sample_size_min':    100,        # T1-07: ≥ 100 trades
        'cost_ratio_max':     0.30,       # T1-10: ≤ 30%
        'wf_efficiency_min':  0.50,       # T2-01: ≥ 0.5
        'hit_rate_min':       0.40,       # T3-01: ≥ 40%
    },
    'Swing': {
        'worst_daily_loss':   -0.06,      # T1-04: ≤ -6%
        'sample_size_min':    30,         # T1-07: ≥ 30 trades
        'cost_ratio_max':     0.15,       # T1-10: ≤ 15% (critical for 4h BTC)
        'wf_efficiency_min':  0.50,       # T2-01: ≥ 0.5
        'hit_rate_min':       0.35,       # T3-01: ≥ 35%
    },
    'Position': {
        'worst_daily_loss':   -0.08,      # T1-04: ≤ -8%
        'sample_size_min':    20,         # T1-07: ≥ 20 trades
        'cost_ratio_max':     0.05,       # T1-10: ≤ 5%
        'wf_efficiency_min':  0.60,       # T2-01: ≥ 0.6
        'hit_rate_min':       0.30,       # T3-01: ≥ 30%
    },
}


def get_threshold(frequency, rule_key, default=None):
    """
    Look up a threshold for a given frequency band.

    Args:
        frequency: '5m', '15m', '30m', '1h', '4h', '1d'
        rule_key: 'worst_daily_loss', 'cost_ratio_max', etc.
        default: fallback value if not found

    Returns:
        threshold value or default
    """
    tier = classify_frequency(frequency)
    if tier is None:
        return default
    return THRESHOLDS[tier].get(rule_key, default)
