"""
Build ensemble combo-signal features from top-scoring Signal Replay combo runs.

Each combo JSON stores the submitted signals (target = +1/-1/0) from a rule-based
strategy ensemble that achieved high platform scores. This module converts those
position-change signals into a bar-level 1h time series and computes ensemble
statistics the DRL can use as a "teacher signal":

    combo_vote         : average position across top combos, [-1, +1]
    combo_conviction   : fraction of combos that share the majority direction, [0, 1]
    combo_long_frac    : fraction of combos currently long, [0, 1]
    combo_short_frac   : fraction of combos currently short, [0, 1]
    combo_flat_frac    : fraction of combos currently flat, [0, 1]

The DRL observes these as features and learns WHEN to follow the ensemble, WHEN
to deviate, and HOW LARGE to size the position — a richer signal than any single
indicator in the existing feature matrix.
"""

import json
import glob
from pathlib import Path

import numpy as np
import pandas as pd

# Minimum score to include a combo in the ensemble
COMBO_SCORE_THRESHOLD = 62.0

# Repo root (two levels up from this file)
_HERE = Path(__file__).resolve().parent
SIGNAL_REPLAY_DIR = _HERE.parent.parent / "Signal_Replay"


def _load_combo_signals(min_score: float = COMBO_SCORE_THRESHOLD) -> list[pd.Series]:
    """
    Parse all combo_*.json files scoring >= min_score.
    Returns a list of pd.Series (indexed by UTC timestamp, values = ±1/0 position).
    """
    series_list: list[pd.Series] = []
    pattern = str(SIGNAL_REPLAY_DIR / "combo_*.json")

    for fpath in sorted(glob.glob(pattern)):
        try:
            score = float(Path(fpath).stem.split("_score_")[1])
        except (IndexError, ValueError):
            continue
        if score < min_score:
            continue

        try:
            data = json.loads(Path(fpath).read_text())
            resp = data.get("response", {})
            signals = resp.get("submission", [])
        except Exception:
            continue

        if not signals:
            continue

        # Build a sparse series of position changes
        records: dict[pd.Timestamp, float] = {}
        for sig in signals:
            ts_ns = sig.get("ts")
            tgt   = sig.get("target", 0)
            if ts_ns is None:
                continue
            ts = pd.Timestamp(ts_ns, unit="ns", tz="UTC")
            records[ts] = float(np.sign(tgt))   # keep only direction: +1, -1, 0
        # Strip tz AFTER building records so we can drop later if needed

        if not records:
            continue

        s = pd.Series(records, name=Path(fpath).stem).sort_index()
        series_list.append(s)

    return series_list


def compute_combo_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Build a DataFrame of combo ensemble features aligned to base_index (1h UTC).

    Columns:
        combo_vote        : mean position across all combos (forward-filled)
        combo_conviction  : fraction of non-flat combos in majority direction
        combo_long_frac   : fraction of combos long
        combo_short_frac  : fraction of combos short
        combo_flat_frac   : fraction of combos flat
    """
    combo_series = _load_combo_signals()
    n = len(combo_series)

    if n == 0:
        # No combos found — return zeros so training still runs
        cols = ["combo_vote", "combo_conviction", "combo_long_frac",
                "combo_short_frac", "combo_flat_frac"]
        return pd.DataFrame(0.0, index=base_index, columns=cols)

    # Forward-fill each sparse position series to every 1h bar
    # Match timezone of base_index so reindex doesn't fail on mixed tz/no-tz.
    idx_tz = base_index.tz
    full_idx = pd.DatetimeIndex(
        pd.date_range(start=base_index[0], end=base_index[-1], freq="1h", tz=idx_tz)
    )

    filled: list[pd.Series] = []
    for s in combo_series:
        # Match timezone of base_index before reindexing
        if idx_tz is None and s.index.tz is not None:
            s = s.tz_convert("UTC").tz_localize(None)
        elif idx_tz is not None and s.index.tz is None:
            s = s.tz_localize(idx_tz)
        aligned = s.reindex(full_idx, method="ffill").fillna(0.0)
        filled.append(aligned)

    # Stack into (n_bars × n_combos) matrix
    mat = pd.concat(filled, axis=1).values   # shape: (bars, n_combos)

    long_frac  = (mat == +1).mean(axis=1)
    short_frac = (mat == -1).mean(axis=1)
    flat_frac  = (mat ==  0).mean(axis=1)
    vote       = mat.mean(axis=1)           # avg position in [-1, +1]

    # Conviction: among non-flat combos, fraction that share the majority direction
    active_mask = mat != 0
    n_active    = active_mask.sum(axis=1).clip(min=1)
    majority    = np.where(vote >= 0, 1.0, -1.0)
    agree       = (mat == majority[:, None]).sum(axis=1)
    conviction  = agree / n_active
    # When all are flat conviction is meaningless → 0
    conviction  = np.where(active_mask.sum(axis=1) == 0, 0.0, conviction)

    result = pd.DataFrame({
        "combo_vote":       vote,
        "combo_conviction": conviction,
        "combo_long_frac":  long_frac,
        "combo_short_frac": short_frac,
        "combo_flat_frac":  flat_frac,
    }, index=full_idx)

    # Align to the caller's base_index (1h grid may differ at edges)
    result = result.reindex(base_index, method="ffill").fillna(0.0)
    print(f"  Combo signal features: {n} combos (score≥{COMBO_SCORE_THRESHOLD}), "
          f"long_frac mean={long_frac.mean():.2f}, short_frac mean={short_frac.mean():.2f}")
    return result.astype(np.float32)
