"""
Walk-forward validation for the BTC DRL SAC agent.

Trains 3 expanding windows, evaluates each on its held-out test period,
and prints a window-by-window + aggregate report.

Expanding windows (all starting 2021-01-01):
  Window 1: Train → 2022-12-31   Test 2023-01-01 → 2023-12-31
  Window 2: Train → 2023-12-31   Test 2024-01-01 → 2024-12-31
  Window 3: Train → 2024-12-31   Test 2025-01-01 → 2026-06-30  (true OOS)

Each window trains a fresh agent from scratch (same seed for reproducibility),
then evaluates deterministically on the test split.

Usage:
  cd /Users/weikangten/Desktop/Crypto-RL
  python DRL_BTC/scripts/walk_forward.py
  python DRL_BTC/scripts/walk_forward.py --seed 42 --steps 300000
"""

import sys
import argparse
import json
import logging
import numpy as np
import torch
from pathlib import Path
from collections import defaultdict, deque

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.config import (
    LOG_DIR, ACTION_DIM, SEQ_LEN,
    INITIAL_CAPITAL, BATCH_SIZE, UPDATE_EVERY, WARMUP_STEPS,
)
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.env.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.utils import select_device, set_seed, compute_metrics

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "walk_forward.log"),
    ],
)
log = logging.getLogger(__name__)

WALK_SPLITS = [
    {
        "label":      "WF-1 (2021→2022 | test 2023)",
        "train_start": "2021-01-01",
        "train_end":   "2022-12-31",
        "val_start":   "2022-10-01",
        "val_end":     "2022-12-31",
        "test_start":  "2023-01-01",
        "test_end":    "2023-12-31",
    },
    {
        "label":      "WF-2 (2021→2023 | test 2024)",
        "train_start": "2021-01-01",
        "train_end":   "2023-12-31",
        "val_start":   "2023-10-01",
        "val_end":     "2023-12-31",
        "test_start":  "2024-01-01",
        "test_end":    "2024-12-31",
    },
    {
        "label":      "WF-3 (2021→2024 | test 2025+) ← true OOS",
        "train_start": "2021-01-01",
        "train_end":   "2024-12-31",
        "val_start":   "2024-10-01",
        "val_end":     "2024-12-31",
        "test_start":  "2025-01-01",
        "test_end":    "2026-06-30",
    },
]


def _eval_equity_pct(agent: SACAgent, env: BTCEnv) -> float:
    """Deterministic rollout over the full val window; returns equity % return."""
    obs, _ = env.reset()
    done   = False
    equity = [INITIAL_CAPITAL]
    while not done:
        action = agent.select_action(obs, deterministic=True)
        obs, _, term, trunc, info = env.step(action)
        done = term or trunc
        equity.append(info["equity"])
    return float(equity[-1] / equity[0] - 1.0) * 100.0


def train_window(
    split: dict,
    feats,
    close,
    device: torch.device,
    seed: int,
    total_steps: int,
) -> SACAgent:
    """Train a fresh SAC agent for one walk-forward window."""
    set_seed(seed)  # from DRL_BTC.utils
    label = split["label"]
    log.info(f"\n{'='*60}")
    log.info(f"  {label}")
    log.info(f"  Train: {split['train_start']} → {split['train_end']}")
    log.info(f"  Val  : {split['val_start']}  → {split['val_end']}")
    log.info(f"{'='*60}")

    train_env   = BTCEnv(feats, close, mode="train", date_range=(split["train_start"], split["train_end"]))
    val_env     = BTCEnv(feats, close, mode="val",   date_range=(split["val_start"],   split["val_end"]))
    market_cols = list(feats.columns)
    agent       = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, device)

    # tag for this window's checkpoints
    wf_idx    = WALK_SPLITS.index(split) + 1
    ckpt_tag  = f"wf{wf_idx}_s{seed}"
    best_ret  = -np.inf
    loss_win  = defaultdict(lambda: deque(maxlen=200))
    step      = 0
    ep        = 0

    obs, _ = train_env.reset(seed=seed)

    while step < total_steps:
        if step < WARMUP_STEPS:
            action = train_env.action_space.sample()
        else:
            action = agent.select_action(obs)

        next_obs, reward, terminated, truncated, info = train_env.step(action)
        done = terminated or truncated
        agent.store(obs, action, reward, next_obs, done)
        obs = next_obs
        step += 1

        if done:
            obs, _ = train_env.reset()
            ep += 1

        if step >= WARMUP_STEPS and step % UPDATE_EVERY == 0:
            losses = agent.update()
            for k, v in losses.items():
                loss_win[k].append(v)

        if step % 5_000 == 0:
            avg = {k: float(np.mean(v)) for k, v in loss_win.items() if v}
            log.info(
                f"  [{label}] step={step:>7} ep={ep:>4} "
                f"eq={info['equity']:>10.0f}  "
                f"alpha={avg.get('alpha', 0):.4f}"
            )

        if step % 10_000 == 0 and step >= WARMUP_STEPS:
            val_eq_pct = _eval_equity_pct(agent, val_env)
            if val_eq_pct > best_ret:
                best_ret = val_eq_pct
                agent.save(f"best_{ckpt_tag}")
                log.info(f"  [{label}] New best val equity: {best_ret:+.2f}% → saved best_{ckpt_tag}")

    agent.save(f"final_{ckpt_tag}")
    log.info(f"  [{label}] Training done. Best val: {best_ret:.4f}")
    return agent, ckpt_tag, best_ret


def eval_test_window(split: dict, feats, close, device, ckpt_tag: str) -> dict:
    """Evaluate the best checkpoint on the held-out test window."""
    market_cols = list(feats.columns)
    agent       = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, device)
    agent.load(f"best_{ckpt_tag}")

    env  = BTCEnv(feats, close, mode="test", date_range=(split["test_start"], split["test_end"]))
    obs, _ = env.reset()
    done = False

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
        if pos == 1:    longs  += 1
        elif pos == -1: shorts += 1
        else:           flats  += 1

    m     = compute_metrics(equity_curve)
    steps = m["n_bars"]

    out_path = ROOT / "DRL_BTC" / "logs" / f"equity_{ckpt_tag}.json"
    with open(out_path, "w") as f:
        json.dump({"equity": equity_curve, "split": split["label"]}, f)

    return {
        "label":      split["label"],
        "test_start": split["test_start"],
        "test_end":   split["test_end"],
        "total_ret":  m["total_ret"],
        "cagr":       m["cagr"],
        "max_dd":     m["max_dd"],
        "sharpe":     m["sharpe"],
        "calmar":     m["calmar"],
        "avg_conf":   float(np.mean(conf_vals)),
        "pct_long":   longs  / max(steps, 1) * 100,
        "pct_short":  shorts / max(steps, 1) * 100,
        "pct_flat":   flats  / max(steps, 1) * 100,
        "final_eq":   float(np.array(equity_curve)[-1]),
    }


def print_result(r: dict):
    print(
        f"  {r['label']:<40}  "
        f"ret={r['total_ret']:+7.2f}%  "
        f"CAGR={r['cagr']:+6.2f}%  "
        f"MDD={r['max_dd']:5.2f}%  "
        f"Sharpe={r['sharpe']:+5.2f}  "
        f"Calmar={r['calmar']:+5.2f}"
    )


def main(seed: int, total_steps: int):
    device = select_device()
    log.info(f"Device: {device}  |  Seed: {seed}  |  Steps/window: {total_steps:,}")

    feats, close = load_features()
    feats = feats.fillna(0.0)

    all_results = []

    for split in WALK_SPLITS:
        _, ckpt_tag, _ = train_window(split, feats, close, device, seed, total_steps)
        result = eval_test_window(split, feats, close, device, ckpt_tag)
        all_results.append(result)
        log.info(
            f"\n  Test result for {result['label']}:\n"
            f"    Return={result['total_ret']:+.2f}%  CAGR={result['cagr']:+.2f}%  "
            f"MDD={result['max_dd']:.2f}%  Sharpe={result['sharpe']:+.2f}"
        )

    # ── Final report ───────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  Walk-Forward Validation Report  (seed={seed}, steps/window={total_steps:,})")
    print(f"{'='*70}")
    for r in all_results:
        print_result(r)

    rets    = np.array([r["total_ret"] for r in all_results])
    sharpes = np.array([r["sharpe"]   for r in all_results])
    dds     = np.array([r["max_dd"]   for r in all_results])

    print(f"\n  Aggregate across {len(all_results)} windows:")
    print(f"    Return  : {rets.mean():+.2f}% ± {rets.std():.2f}%")
    print(f"    Sharpe  : {sharpes.mean():+.2f} ± {sharpes.std():.2f}")
    print(f"    Max DD  : {dds.mean():.2f}% ± {dds.std():.2f}%")

    n_pos = int((rets > 0).sum())
    print(f"\n  {n_pos}/{len(all_results)} windows profitable", end="")
    if n_pos == len(all_results) and sharpes.mean() > 0.5:
        print(" — consistent positive performance across all windows.")
    elif n_pos == len(all_results):
        print(" — all windows profitable but Sharpe is low.")
    else:
        print(" — mixed results; check if recent regime is out-of-distribution.")

    print()

    # Save summary
    summary_path = ROOT / "DRL_BTC" / "logs" / "walk_forward_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"seed": seed, "total_steps": total_steps, "results": all_results}, f, indent=2)
    log.info(f"Summary saved → {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed",  type=int, default=42,      help="Random seed (default: 42)")
    parser.add_argument("--steps", type=int, default=300_000, help="Training steps per window (default: 300000)")
    args = parser.parse_args()
    main(seed=args.seed, total_steps=args.steps)
