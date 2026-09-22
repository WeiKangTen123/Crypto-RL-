"""
Evaluate a saved SAC checkpoint and print a full trading report.

Usage:
  # OOS test set (default)
  python DRL_BTC/scripts/evaluate.py --tag best_s42

  # Val window
  python DRL_BTC/scripts/evaluate.py --tag best_s42 --mode val

  # Custom date range
  python DRL_BTC/scripts/evaluate.py --tag best_s42 --start 2025-01-01 --end 2025-12-31

  # Skip OOD reset (match training-val conditions — BLOCK active from start)
  python DRL_BTC/scripts/evaluate.py --tag best_s42 --no-ood-reset
"""

import sys
import argparse
import json
import numpy as np
import torch
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.config import ACTION_DIM, INITIAL_CAPITAL, LOG_DIR, CKPT_DIR
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.env.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.utils import select_device, compute_metrics


def _auto_patch_hidden(tag: str) -> None:
    """Detect LSTM hidden size from checkpoint and patch config so make_networks matches."""
    import DRL_BTC.config as _cfg
    path = CKPT_DIR / f"sac_{tag}.pt"
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    for k, v in ckpt["actor"].items():
        if "lstm" in k and "weight_hh" in k:
            hidden = v.shape[1]
            if hidden != _cfg.LSTM_HIDDEN or hidden != _cfg.FC_HIDDEN:
                print(f"[eval] Checkpoint hidden={hidden}; patching config LSTM_HIDDEN/FC_HIDDEN {_cfg.LSTM_HIDDEN}→{hidden}")
                _cfg.LSTM_HIDDEN = hidden
                _cfg.FC_HIDDEN   = hidden
            break
    del ckpt


def _compute_trade_stats(pnls, mfes, maes, holds, exits):
    """Trade-level quality metrics from per-trade lists."""
    if not pnls or len(pnls) < 2:
        return None
    pnls_a = np.array(pnls, dtype=np.float64)
    n      = len(pnls_a)
    wins   = int((pnls_a > 0).sum())
    losses = n - wins
    win_rate = wins / n
    avg_win  = float(pnls_a[pnls_a > 0].mean()) if wins   > 0 else 0.0
    avg_loss = float(abs(pnls_a[pnls_a < 0].mean())) if losses > 0 else 1e-8
    pf       = avg_win / avg_loss
    tp_rate  = exits.count("tp") / max(len(exits), 1) if exits else 0.0
    return {
        "n":        n,
        "win_rate": win_rate,
        "pf":       pf,
        "tp_rate":  tp_rate,
        "p10":      float(np.percentile(pnls_a, 10)) * 100,
        "p50":      float(np.percentile(pnls_a, 50)) * 100,
        "p90":      float(np.percentile(pnls_a, 90)) * 100,
        "mfe_p50":  float(np.median(mfes)) * 100 if mfes else 0.0,
        "mae_p50":  float(np.median(maes)) * 100 if maes else 0.0,
        "avg_hold": float(np.mean(holds)) if holds else 0.0,
        "tqs":      win_rate * pf,
    }


def evaluate(tag: str = "best", mode: str = "test",
             date_range=None, ood_reset: bool = True) -> dict:
    _auto_patch_hidden(tag)
    device     = select_device()
    feats, close = load_features()
    feats       = feats.fillna(0.0)
    market_cols = list(feats.columns)

    env   = BTCEnv(feats, close, mode=mode, date_range=date_range)
    agent = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, device)
    agent.load(tag)

    # BUG FIX: Reset OOD diagnostics before evaluation.
    # Checkpoints save actor.diagnostics.running_mean/std calibrated to the last
    # 20K training steps. When evaluate.py runs on val/test data whose z-distribution
    # differs from those training steps, ood_score spikes immediately, ood_ema ramps
    # to 1.0 mid-evaluation → BLOCK activates mid-evaluation → inconsistent behaviour.
    # Resetting to fresh state lets the agent calibrate naturally to the eval data.
    # (Use --no-ood-reset to match the training-val condition where BLOCK is active.)
    if ood_reset:
        _actor_mod = getattr(agent.actor, "_orig_mod", agent.actor)
        _actor_mod.diagnostics.n_updates.zero_()
        _actor_mod.diagnostics.running_mean.zero_()
        _actor_mod.diagnostics.running_std.fill_(1.0)
        agent.drift_manager._ood_ema = 0.0
        # Sync CPU actor so inference uses the reset diagnostics
        agent._sync_actor_cpu()
        print(f"[eval] OOD diagnostics reset → fresh z-space baseline")

    obs, _ = env.reset()
    done   = False

    longs = shorts = flats = 0
    n_steps      = 0
    equity_curve = [INITIAL_CAPITAL]

    # OOD tracking — sampled every 500 bars and at start/end
    ood_samples: list[tuple[int, float]] = []

    # Trade-level stats
    trade_pnls:  list[float] = []
    trade_mfes:  list[float] = []
    trade_maes:  list[float] = []
    trade_holds: list[int]   = []
    trade_exits: list[str]   = []
    entry_equity = INITIAL_CAPITAL

    while not done:
        action = agent.select_action(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        cur_equity = info["equity"]
        equity_curve.append(cur_equity)
        pos = info["position"]
        if   pos ==  1: longs  += 1
        elif pos == -1: shorts += 1
        else:           flats  += 1
        n_steps += 1

        # Sample OOD state
        if n_steps == 1 or n_steps % 500 == 0 or done:
            ood_samples.append((n_steps, agent.drift_manager._ood_ema))

        # Track trade equity at entry
        if info.get("trade_closed"):
            trade_pnl_pct = (cur_equity - entry_equity) / (entry_equity + 1e-10)
            trade_pnls.append(trade_pnl_pct)
            trade_mfes.append(info.get("trade_mfe", 0.0))
            trade_maes.append(info.get("trade_mae", 0.0))
            trade_holds.append(info.get("trade_hold_bars", 0))
            ew = info.get("trade_exit_why")
            if ew:
                trade_exits.append(ew)
            entry_equity = cur_equity
        elif pos != 0 and info.get("trade_closed") is False and n_steps == 1:
            entry_equity = cur_equity  # handle edge case at episode start

    m      = compute_metrics(equity_curve)
    n_bars = max(n_steps, 1)
    eq     = np.array(equity_curve)
    ts     = _compute_trade_stats(trade_pnls, trade_mfes, trade_maes, trade_holds, trade_exits)

    ood_start = ood_samples[0][1]  if ood_samples else 0.0
    ood_end   = ood_samples[-1][1] if ood_samples else 0.0
    ood_max   = max(v for _, v in ood_samples) if ood_samples else 0.0

    # ── Report ────────────────────────────────────────────────────────────────
    W = 62
    print(f"\n{'='*W}")
    print(f"  BTC DRL Evaluation  ·  checkpoint: {tag}  ·  mode: {mode}")
    print(f"{'='*W}")
    print(f"  Bars evaluated  : {n_steps:,}")
    print(f"  Starting equity : ${INITIAL_CAPITAL:>12,.0f}")
    print(f"  Final equity    : ${eq[-1]:>12,.0f}")
    print(f"{'─'*W}")
    print(f"  Total return    : {m['total_ret']:+.2f}%")
    print(f"  CAGR            : {m['cagr']:+.2f}%")
    print(f"  Max drawdown    : {m['max_dd']:.2f}%")
    print(f"  Sharpe (hourly) : {m['sharpe']:+.2f}")
    print(f"  Calmar ratio    : {m['calmar']:+.2f}")
    print(f"{'─'*W}")
    print(f"  OOD ema (start) : {ood_start:.3f}    max: {ood_max:.3f}    end: {ood_end:.3f}")
    print(f"  OOD reset used  : {'Yes' if ood_reset else 'No (training-val mode)'}")
    print(f"{'─'*W}")
    print(f"  Bars long       : {longs:>6,}  ({longs/n_bars*100:.1f}%)")
    print(f"  Bars short      : {shorts:>6,}  ({shorts/n_bars*100:.1f}%)")
    print(f"  Bars flat       : {flats:>6,}  ({flats/n_bars*100:.1f}%)")
    if ts:
        print(f"{'─'*W}")
        print(f"  Trades          : {ts['n']}   win={ts['win_rate']:.0%}   pf={ts['pf']:.2f}   TQS={ts['tqs']:.2f}")
        print(f"  P10/P50/P90     : {ts['p10']:+.2f}% / {ts['p50']:+.2f}% / {ts['p90']:+.2f}%")
        print(f"  MFE/MAE (p50)   : {ts['mfe_p50']:+.2f}% / {ts['mae_p50']:+.2f}%")
        print(f"  TP rate         : {ts['tp_rate']:.0%}   avg hold: {ts['avg_hold']:.0f} bars")
        exit_counts = {e: trade_exits.count(e) for e in set(trade_exits)} if trade_exits else {}
        print(f"  Exit reasons    : {exit_counts}")
    print(f"{'='*W}\n")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = LOG_DIR / f"equity_{tag}.json"
    result = {
        "tag":  tag,
        "mode": mode,
        **m,
        "ood_start":  ood_start,
        "ood_end":    ood_end,
        "ood_max":    ood_max,
        "pct_long":   longs  / n_bars * 100,
        "pct_short":  shorts / n_bars * 100,
        "pct_flat":   flats  / n_bars * 100,
        "trade_stats": ts or {},
        "equity":     [float(v) for v in equity_curve],
    }
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Full report saved → {out}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag",   default="best",
                        help="Checkpoint tag (default: best)")
    parser.add_argument("--mode",  default="test", choices=["train", "val", "test"],
                        help="Date window to evaluate (default: test)")
    parser.add_argument("--start", default=None,
                        help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end",   default=None,
                        help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--no-ood-reset", action="store_true",
                        help="Skip OOD diagnostics reset (matches training-val BLOCK conditions)")
    args = parser.parse_args()

    date_range = (args.start, args.end) if args.start and args.end else None
    evaluate(tag=args.tag, mode=args.mode, date_range=date_range,
             ood_reset=not args.no_ood_reset)
