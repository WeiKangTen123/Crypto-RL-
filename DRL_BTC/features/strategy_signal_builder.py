"""
Extract bar-level position state from each BTC strategy's generate_signals().

Concept (same as FreqAI's populate_indicators):
  - Run each strategy on its native timeframe (1h or 4h)
  - Extract the 'signal' column (+1/-1/0), forward-fill to represent
    the current held position direction between entry signals
  - Resample/align to 1h base index
  - Add as DRL observation features: the agent sees WHICH strategies
    are currently long/short at each bar and learns when to follow them

Why forward-fill matters:
  strategy.signal fires ONLY on entry bars (sparse, e.g. 100 entries over 5y).
  Forward-filling converts "entry occurred" into "current position = last direction",
  which is what the DRL needs to know about the strategy's current stance.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy_backtest.run_backtest import load_data
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies as strat_module

# ── Strategy selection ────────────────────────────────────────────────────────
# BTC 4h and 1h strategies referenced in strategy_mapping.md that:
#   (a) operate on BTCUSDT OHLCV + funding/OI columns
#   (b) successfully run generate_signals() without extra factor data
#   (c) produce between 20 and 5000 signals over 5 years (meaningful but not noisy)
STRAT_IDS_4H = [
    "3",    # MACDKDJ_ADX_ATR — trend/momentum hybrid
    "13",   # MacroTakerFlowExhaustion — taker-driven exhaustion reversal
    "23",   # EMACrossover — classic trend
    "30",   # LiquiditySweepReversal — liquidity-grab mean-reversion
    "37",   # DMIADX — directional strength filter
    "38",   # FVGMitigationReversal — fair-value-gap fill
    "47",   # AroonRSI — momentum confluence
    "68",   # MeanReversionFundingRate — funding-rate mean reversion
    "74",   # HarmonicDivergence — harmonic pattern + divergence
    "77",   # SupertrendATRMomentum — trend + momentum filter
    "80",   # SupertrendPro — vanilla supertrend
    "83",   # RWAMomentum — real-world-asset momentum proxy
    "85",   # DonchianBreakout — channel breakout
    "92",   # OrderBlockSMC — smart-money order block
    "99",   # RSIDivergenceReversal — RSI divergence
    "134",  # KalmanFilteredMomentum — Kalman-smoothed momentum
    "135",  # ChoppinessGatedSupertrend — chop-filtered supertrend
    "136",  # AVS — adaptive volatility signal
    "139",  # DumpReversalPeakTrail — peak-reversal + trail
    "145",  # MDVB — multi-dimensional vol breakout
    "146",  # OBFC — order-block + funding confluence
    "150",  # EFRMR — extreme funding-rate mean reversion
    "162",  # Forge #162 — tuned ForgeStrategy
    "179",  # EMAStreak — EMA persistence streak
    "180",  # GridTradingBTC — grid-style mean reversion
    "182",  # SupertrendEmaFilter — supertrend + EMA confirmation
    "183",  # SupertrendProVolatility — supertrend + vol regime
    "184",  # DiamondTriangleBreakout — pattern breakout
    "185",  # RsiDivergenceMeanReversion — RSI divergence reversion
    "190",  # BarStrengthMomentum — bar-by-bar strength score
]

STRAT_IDS_1H = [
    "26",   # EnvelopeMeanReversion — envelope channel reversion
    "79",   # GoldenZoneFibBOS — fib golden-zone + BOS
    "90",   # ETHMomentumBreakout (BTC variant) — momentum breakout
    "108",  # InstitutionalMomentumConsolidationBreakout — volume consolidation
    "192",  # IntrabarEfficiencyMomentum — tick efficiency proxy
    "194",  # AmihudIlliqMr — Amihud illiquidity mean reversion
]

DATE_FROM = "2020-12-01"   # earlier than feature cache start so ffill covers warm-up

# Strategies that expose a continuous ±1 directional-state column.
# Use these INSTEAD of the sparse 'signal' column so the feature is always
# meaningful (not stuck at +1 from the last long-only entry cross).
_PREFERRED_STATE: dict[str, str] = {
    "23":  "raw_state",           # fast EMA vs slow EMA: +1 above, -1 below
    "77":  "st_dir",              # Supertrend direction: +1 bull, -1 bear
    "80":  "supertrend_direction",# SupertrendPro: continuous ±1 (was always +1 via ffill)
    "135": "st_dir",              # ChoppinessGatedSupertrend direction
    "182": "st_dir",              # SupertrendEmaFilter direction
    "183": "st_dir",              # SupertrendProVolatility direction
}

# Minimum fraction of bars each direction must appear to allow forward-fill.
# Strategies below this threshold (long-only or short-only signal entries)
# use raw entry pulses (0 between entries, ±1 only on signal bar) so the DRL
# sees "fresh setup just triggered" rather than a constant bias.
_BALANCED_THRESHOLD = 0.01   # at least 1% of bars in each direction


def _run_strategy(sid: str, df: pd.DataFrame):
    """
    Run one strategy and return a bar-level position-state series.
    Returns None if the strategy fails.

    Three modes depending on what the strategy exposes:
    1. PREFERRED_STATE column exists (e.g. supertrend_direction, raw_state):
       → use it directly as a continuous ±1 signal — always correct direction.
    2. Balanced long+short signal entries (both > _BALANCED_THRESHOLD):
       → forward-fill the sparse 'signal' column → continuous held-position state.
    3. Single-direction entries (long-only or short-only strategies):
       → keep raw 'signal' WITHOUT forward-fill → DRL sees a brief pulse when the
         pattern fires and 0 between entries ("fresh setup just triggered").
    """
    if sid not in STRATEGY_LIBRARY:
        return None
    cfg = STRATEGY_LIBRARY[sid]
    cls = getattr(strat_module, cfg["class"], None)
    if cls is None:
        return None
    try:
        df_out = cls(df.copy(), **cfg.get("params", {})).generate_signals()
    except Exception as e:
        print(f"    [strat_{sid}] SKIP ({type(e).__name__}: {str(e)[:60]})")
        return None

    # Mode 1: continuous state column
    state_col = _PREFERRED_STATE.get(sid)
    if state_col and state_col in df_out.columns:
        pos = df_out[state_col].astype(float).fillna(0.0)
        return pos.astype(np.float32)

    sig = df_out["signal"]
    n   = len(sig)
    long_frac  = (sig == 1).sum() / n
    short_frac = (sig == -1).sum() / n

    if long_frac >= _BALANCED_THRESHOLD and short_frac >= _BALANCED_THRESHOLD:
        # Mode 2: balanced entries → forward-fill to held-position state
        pos = sig.replace(0, np.nan).ffill().fillna(0.0)
    else:
        # Mode 3: single-direction → raw pulse (0 between entries)
        pos = sig.astype(float)

    return pos.astype(np.float32)


def compute_strategy_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Build a DataFrame of strategy position-state features aligned to base_index (1h).

    Each column `strat_{id}_pos` holds the forward-filled position (+1/-1/0)
    of that strategy at every 1h bar.  4h strategies are upsampled by forward-fill.

    Parameters
    ----------
    base_index : pd.DatetimeIndex
        The 1h index of the DRL feature cache (tz-naive or tz-aware).

    Returns
    -------
    pd.DataFrame  shape (len(base_index), n_strategies)
    """
    idx_tz = base_index.tz
    start  = DATE_FROM
    end_dt = base_index[-1]
    end    = str(end_dt.date() if hasattr(end_dt, "date") else end_dt)[:10]

    print(f"  Loading BTC OHLCV for strategy signals ({start} → {end})…")
    df4h = load_data("BTC", "4h", start, end, mode="per_coin")
    df1h = load_data("BTC", "1h", start, end, mode="per_coin")

    columns: dict[str, pd.Series] = {}

    for sid in STRAT_IDS_4H:
        pos = _run_strategy(sid, df4h)
        if pos is None:
            continue
        # Match tz
        if idx_tz is None and pos.index.tz is not None:
            pos = pos.tz_localize(None)
        elif idx_tz is not None and pos.index.tz is None:
            pos = pos.tz_localize(idx_tz)
        # Upsample 4h → 1h by forward-fill
        pos_1h = pos.reindex(base_index, method="ffill").fillna(0.0)
        columns[f"strat_{sid}_pos"] = pos_1h.astype(np.float32)

    for sid in STRAT_IDS_1H:
        pos = _run_strategy(sid, df1h)
        if pos is None:
            continue
        if idx_tz is None and pos.index.tz is not None:
            pos = pos.tz_localize(None)
        elif idx_tz is not None and pos.index.tz is None:
            pos = pos.tz_localize(idx_tz)
        pos_1h = pos.reindex(base_index, method="ffill").fillna(0.0)
        columns[f"strat_{sid}_pos"] = pos_1h.astype(np.float32)

    result = pd.DataFrame(columns, index=base_index)
    n_ok = len(result.columns)
    n_long = (result > 0).any().sum()
    n_short = (result < 0).any().sum()
    print(f"  Strategy signal features: {n_ok} strategies "
          f"({n_long} ever-long, {n_short} ever-short)")
    return result
