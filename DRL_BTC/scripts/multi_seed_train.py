"""
Train the SAC agent with multiple random seeds, evaluate each on the OOS
test set, and print an aggregate report.

Usage:
  python DRL_BTC/scripts/multi_seed_train.py
  python DRL_BTC/scripts/multi_seed_train.py --seeds 42 123 999
  python DRL_BTC/scripts/multi_seed_train.py --seeds 42 123 --steps 100000  # quick test

Output:
  - Per-seed checkpoints : data/checkpoints/sac_best_s{seed}.pt
  - Equity curves        : logs/equity_best_s{seed}.json
  - Summary              : logs/multi_seed_summary.json
"""

import sys
import argparse
import json
import numpy as np
import torch
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.config import ACTION_DIM, INITIAL_CAPITAL, LOG_DIR
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.env.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.training.train import train
from DRL_BTC.utils import select_device, compute_metrics


def _run_oos(seed: int, feats, close, device: torch.device) -> dict:
    """Load best checkpoint for this seed and evaluate deterministically on OOS."""
    market_cols = list(feats.columns)
    tag         = f"best_s{seed}"

    env   = BTCEnv(feats, close, mode="test")
    agent = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, device)
    agent.load(tag)

    obs, _ = env.reset()
    done   = False

    equity_curve = [INITIAL_CAPITAL]
    conf_vals    = []
    longs = shorts = flats = 0

    while not done:
        action = agent.select_action(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        equity_curve.append(info["equity"])
        conf_vals.append(info["confidence"])
        pos = info["position"]
        if   pos ==  1: longs  += 1
        elif pos == -1: shorts += 1
        else:           flats  += 1

    m      = compute_metrics(equity_curve)
    n_bars = max(m["n_bars"], 1)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOG_DIR / f"equity_{tag}.json"
    with open(out_path, "w") as f:
        json.dump({"equity": equity_curve, "seed": seed}, f)

    return {
        "seed":       seed,
        "total_ret":  m["total_ret"],
        "cagr":       m["cagr"],
        "max_dd":     m["max_dd"],
        "sharpe":     m["sharpe"],
        "calmar":     m["calmar"],
        "avg_conf":   float(np.mean(conf_vals)),
        "pct_long":   longs  / n_bars * 100,
        "pct_short":  shorts / n_bars * 100,
        "pct_flat":   flats  / n_bars * 100,
        "final_eq":   float(equity_curve[-1]),
    }


def _print_seed_row(r: dict):
    print(
        f"  seed={r['seed']:>4}  "
        f"ret={r['total_ret']:+7.2f}%  "
        f"CAGR={r['cagr']:+6.2f}%  "
        f"MDD={r['max_dd']:5.2f}%  "
        f"Sharpe={r['sharpe']:+5.2f}  "
        f"Calmar={r['calmar']:+5.2f}  "
        f"conf={r['avg_conf']:.3f}  "
        f"L/S/F={r['pct_long']:.0f}/{r['pct_short']:.0f}/{r['pct_flat']:.0f}%"
    )


def main(seeds: list[int], total_steps: int):
    device = select_device()
    print(f"Device: {device}  |  Seeds: {seeds}  |  Steps: {total_steps:,}")

    print("Loading features…")
    feats, close = load_features()
    feats = feats.fillna(0.0)

    results = []

    for seed in seeds:
        print(f"\n{'='*60}")
        print(f"  Training seed={seed}")
        print(f"{'='*60}")
        train(seed=seed, total_steps=total_steps)

        print(f"\n  Evaluating OOS for seed={seed}…")
        r = _run_oos(seed, feats, close, device)
        results.append(r)
        _print_seed_row(r)

    # ── Per-seed report ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  Per-seed OOS results  ({len(seeds)} seeds)")
    print(f"{'='*70}")
    for r in results:
        _print_seed_row(r)

    # ── Aggregate ──────────────────────────────────────────────────────────────
    keys = ["total_ret", "cagr", "max_dd", "sharpe", "calmar"]
    agg  = {k: np.array([r[k] for r in results]) for k in keys}

    print(f"\n{'='*70}")
    print(f"  Aggregate (n={len(seeds)} seeds)")
    print(f"{'='*70}")
    print(f"  Total return : {agg['total_ret'].mean():+.2f}% ± {agg['total_ret'].std():.2f}%")
    print(f"  CAGR         : {agg['cagr'].mean():+.2f}% ± {agg['cagr'].std():.2f}%")
    print(f"  Max drawdown : {agg['max_dd'].mean():.2f}% ± {agg['max_dd'].std():.2f}%")
    print(f"  Sharpe       : {agg['sharpe'].mean():+.2f} ± {agg['sharpe'].std():.2f}")
    print(f"  Calmar       : {agg['calmar'].mean():+.2f} ± {agg['calmar'].std():.2f}")

    all_pos = all(r["total_ret"] > 0 for r in results)
    n_pos   = sum(r["total_ret"] > 0 for r in results)
    verdict = "ALL seeds profitable" if all_pos else f"{n_pos}/{len(results)} seeds profitable"
    print(f"\n  Verdict: {verdict}")
    if agg["sharpe"].mean() > 1.0 and all_pos:
        print("  → System looks robust across seeds.")
    elif agg["sharpe"].mean() > 0 and all_pos:
        print("  → Consistent but Sharpe is modest — consider more TOTAL_STEPS.")
    else:
        print("  → High variance or losses detected — review reward shaping.")
    print()

    summary_path = LOG_DIR / "multi_seed_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"seeds": seeds, "total_steps": total_steps, "results": results}, f, indent=2)
    print(f"Summary saved → {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[42, 123, 999],
        help="Random seeds to train (default: 42 123 999)",
    )
    parser.add_argument(
        "--steps", type=int, default=None,
        help="Training steps per seed (default: TOTAL_STEPS from config)",
    )
    args = parser.parse_args()

    # Import TOTAL_STEPS here so --steps can override it
    from DRL_BTC.config import TOTAL_STEPS
    steps = args.steps if args.steps is not None else TOTAL_STEPS
    main(seeds=args.seeds, total_steps=steps)
