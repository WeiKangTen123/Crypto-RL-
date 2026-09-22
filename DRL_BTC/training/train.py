"""
SAC training — BTC DRL agent — Session 8

Architecture: Hierarchical Beta + Alpha + RL
────────────────────────────────────────────
  Session 7 confirmed:
    4D action, trade-level replay, no oscillation at 500K steps.

  Session 8 adds supervised pretrain before RL:
    Stage 0a: SharedModel — Beta head (regime classification)
    Stage 0b: SharedModel — Alpha head (trade quality multi-task)
    Stage 0c: SharedModel — Joint fine-tune (all heads)
    → Encoder weights copied to RL Actor
    Stage 1:  BC Risk Pretraining (actor on oracle risk labels, 4D)
    Stage 2:  Warmup (300 complete trades)
    Stage 3:  SAC RL (trade-level replay, PER)

  Why supervised pretrain first?
    The PerspectiveEncoder now learns from two complementary signals:
      Beta head: what regime is the market in right now?
      Alpha head: what trade quality can I expect if I enter here?
    These are direct supervised targets with clean credit assignment.
    The SAC then fine-tunes execution on top of a semantically rich
    encoder rather than starting from random weights.

Trade quality metrics are logged per episode and per validation:
  p10/p50/p90  return distribution across trades
  MFE p50      median maximum favorable excursion (how much we let run)
  MAE p50      median maximum adverse excursion (how much heat we took)
  TP rate      % of trades that hit TP (vs SL / direction / timeout)
  Win rate     % of trades with positive PnL
  Profit Factor avg_win / avg_loss
  TQS          Trade Quality Score = win_rate × profit_factor

Phases
──────
  0. SUPERVISED PRETRAIN : SharedModel (Beta + Alpha + joint)
  1. BC PRETRAIN         : supervised actor on oracle risk labels (4D)
  2. WARMUP              : random actions until WARMUP_TRADES trades collected
  3. LEARNING            : SAC updates from trade-level PER buffer
  4. VALIDATE            : deterministic val rollout every VAL_EVERY steps
  5. SUMMARY             : end-of-training report
"""

from __future__ import annotations

import sys
import time
import json
import copy
import logging
import argparse
import concurrent.futures
from pathlib import Path
from collections import defaultdict, deque

import random
import numpy as np
import torch

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.config import (
    LOG_DIR, MODEL_DIR, CKPT_DIR,
    WARMUP_TRADES, TOTAL_STEPS, ACTION_DIM, SEQ_LEN, INITIAL_CAPITAL,
    UPDATE_EVERY_TRADES, G_STEPS, BATCH_SIZE, TRAIN_END, VAL_START, VAL_END, TEST_START,
    LR_ACTOR, LR_CRITIC, LR_ALPHA, GAMMA, TAU, GRAD_CLIP,
    MAX_LEVERAGE, MIN_LEVERAGE, MAX_DRAWDOWN_KILL,
    VAL_REGIMES, WEIGHT_DECAY,
    POS_SIZE_MIN, POS_SIZE_MAX,
)
from DRL_BTC.models.trade_ranker import TradeRanker
from DRL_BTC.models.kelly_sizer import KellySizer
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.env.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.training.bc_exit_pretrain import pretrain_actor
from DRL_BTC.models.shared_model import SharedModel
from DRL_BTC.training.supervised_pretrain import pretrain_shared_model
from DRL_BTC.utils import select_device, set_seed, compute_metrics

MODEL_DIR.mkdir(parents=True, exist_ok=True)

VAL_EVERY   = 10_000   # 20K→10K: finer-grained early stopping catches peak before overfit
CKPT_EVERY  = 50_000
ROLL_N      = 20
RESUME_FILL = 20_000


# ── helpers ────────────────────────────────────────────────────────────────────

def _setup_logging(seed: int) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"train_s{seed}"
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler();                      ch.setFormatter(fmt); logger.addHandler(ch)
    fh = logging.FileHandler(LOG_DIR / f"{name}.log"); fh.setFormatter(fmt); logger.addHandler(fh)
    return logger


def _eta(remaining: int, sps: float) -> str:
    if sps <= 0: return "?"
    s = remaining / sps
    return f"{int(s//3600)}h{int((s%3600)//60):02d}m"


def _list_checkpoints():
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(CKPT_DIR.glob("sac_*.pt"))
    if not files:
        print("No checkpoints found in", CKPT_DIR)
        return
    print(f"\nAvailable checkpoints  ({CKPT_DIR})\n")
    print(f"  {'Tag':<30}  {'Step':>8}  {'Ep':>6}  {'Best val':>10}  Size")
    print("  " + "─" * 65)
    for f in files:
        tag = f.stem[4:]
        size_mb = f.stat().st_size / 1e6
        try:
            ckpt  = torch.load(f, map_location="cpu", weights_only=False)
            state = ckpt.get("train_state", {})
            step  = state.get("step", "?")
            ep    = state.get("ep_num", "?")
            best  = state.get("best_val_eq", None)
            best_s = f"{best:+.2f}%" if isinstance(best, float) else "?"
            step_s = f"{step:,}" if isinstance(step, int) else step
        except Exception:
            step_s = best_s = ep = "?"
        print(f"  {tag:<30}  {step_s:>8}  {ep:>6}  {best_s:>10}  {size_mb:.0f} MB")
    print()
    print("  Resume usage:")
    print("    python DRL_BTC/training/train.py --resume <tag>  [--seed N]")
    print()


# ── trade quality stats ────────────────────────────────────────────────────────

def _compute_trade_stats(pnls, mfes, maes, holds, exits) -> dict | None:
    """Compute trade-level quality metrics from per-trade lists."""
    if not pnls or len(pnls) < 2:
        return None
    pnls_a = np.array(pnls, dtype=np.float64)
    n      = len(pnls_a)
    wins   = int((pnls_a > 0).sum())
    losses = n - wins
    win_rate  = wins / n
    avg_win   = float(pnls_a[pnls_a > 0].mean()) if wins   > 0 else 0.0
    avg_loss  = float(abs(pnls_a[pnls_a < 0].mean())) if losses > 0 else 1e-8
    pf        = avg_win / avg_loss
    tp_rate   = exits.count("tp") / max(len(exits), 1) if exits else 0.0
    return {
        "n":        n,
        "win_rate": win_rate,
        "pf":       pf,
        "tp_rate":  tp_rate,
        "p10":      float(np.percentile(pnls_a, 10)) * 100,   # → %
        "p50":      float(np.percentile(pnls_a, 50)) * 100,
        "p90":      float(np.percentile(pnls_a, 90)) * 100,
        "mfe_p50":  float(np.median(mfes)) * 100 if mfes else 0.0,
        "mae_p50":  float(np.median(maes)) * 100 if maes else 0.0,
        "avg_hold": float(np.mean(holds)) if holds else 0.0,
        "tqs":      win_rate * pf,  # Trade Quality Score
    }


# ── val evaluation ─────────────────────────────────────────────────────────────

def multi_evaluate(agent: SACAgent, val_envs: list, regime_labels: list[str]) -> dict:
    """
    TIA v2 multi-regime validation: runs evaluate() on each val environment
    and returns aggregate metrics.

    Early-stop criterion: min Sharpe across all regimes (robustness, not average).
    A model that excels in one regime but fails in another is penalised.

    Returns a dict with:
        sharpe        : min Sharpe across regimes (used for early-stop / best checkpoint)
        avg_sharpe    : average Sharpe across regimes
        regime_sharpes: {label: sharpe} breakdown per regime
        ret_pct       : average return across regimes
        max_dd        : worst max-drawdown across regimes
        ... plus all keys from the first regime's evaluate() for logging compat

    Speed: runs all val envs in parallel via ThreadPoolExecutor.
      Each thread gets its own deepcopy of _actor_cpu so _last_actor_info writes
      don't race. KnowledgeMemory and DriftManager are shared read-only refs.
    """
    if agent._actor_cpu is None:
        agent._sync_actor_cpu()

    # One isolated CPU copy per regime — weights shared via deepcopy, but each
    # thread writes to its own _last_actor_info without racing other threads.
    #
    # OOD reset for val: the drift_manager._ood_ema is built from recent training
    # steps and may be saturated at 1.0 → size_mult≈0 → agent can't trade → val
    # measures fee drag not skill. Fix: zero ood_ema before val; restore after.
    #
    # Do NOT reset diagnostics (running_mean/std) on val actor copies. The deepcopy
    # already carries the correct z-space baseline from training. Resetting to (0,1)
    # means the first val trades compare against (0,1) when the encoder has shifted —
    # causing all trades to spike OOD and re-saturate ood_ema within 20 val trades.
    saved_ood_ema = agent.drift_manager._ood_ema
    agent.drift_manager._ood_ema = 0.0

    actor_copies = []
    for _ in val_envs:
        ac = copy.deepcopy(agent._actor_cpu)
        ac._knowledge_memory = agent.knowledge_memory   # restore live reference (read-only)
        ac._drift_manager    = agent.drift_manager      # shared ref with ood_ema=0 during val
        actor_copies.append(ac)

    def _eval_one(idx: int) -> dict:
        return evaluate(agent, val_envs[idx], _actor=actor_copies[idx])

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(val_envs)) as pool:
        results = list(pool.map(_eval_one, range(len(val_envs))))

    # Restore OOD state — val should not contaminate training drift tracking
    agent.drift_manager._ood_ema = saved_ood_ema

    sharpes = [r["sharpe"] for r in results]
    rets    = [r["ret_pct"] for r in results]
    dds     = [r["max_dd"] for r in results]

    # Regime breakdown dict for logging
    regime_sharpes = {label: float(s) for label, s in zip(regime_labels, sharpes)}

    combined = {
        **results[0],   # include trade_stats, L/S/F from first regime as representative
        "sharpe":         float(min(sharpes)),       # conservative: worst regime
        "avg_sharpe":     float(np.mean(sharpes)),
        "ret_pct":        float(np.mean(rets)),
        "max_dd":         float(max(dds)),            # worst drawdown across regimes
        "regime_sharpes": regime_sharpes,
    }
    return combined


def evaluate(agent: SACAgent, env: BTCEnv, _actor=None) -> dict:
    """Deterministic rollout over the full val window with trade quality tracking.

    _actor: thread-local CPU actor copy used by multi_evaluate for parallel runs.
            Falls back to agent.select_action() when None (single-threaded path).
    """
    obs, _ = env.reset()
    done = False
    eq_curve  = [INITIAL_CAPITAL]
    longs = shorts = flats = 0
    n = 0

    # Trade-level tracking for quality stats
    prev_pos    = 0
    trade_acc   = 0.0
    trade_pnls  = []
    trade_mfes  = []
    trade_maes  = []
    trade_holds = []
    trade_exits = []

    # Use thread-local actor copy when available (parallel val path)
    if _actor is not None:
        def _act(o):
            t = torch.as_tensor(o, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                return _actor.act(t, deterministic=True).numpy().squeeze(0)
    else:
        def _act(o):
            return agent.select_action(o, deterministic=True)

    while not done:
        action = _act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        done     = terminated or truncated
        cur_pos  = int(info["position"])
        eq_curve.append(info["equity"])

        pos = info["position"]
        if   pos ==  1: longs  += 1
        elif pos == -1: shorts += 1
        else:           flats  += 1
        n += 1

        # Trade state machine for quality stats
        if prev_pos == 0 and cur_pos != 0:
            trade_acc = reward
        elif prev_pos != 0 and cur_pos == prev_pos:
            trade_acc += reward
        elif prev_pos != 0:
            trade_acc += reward
            trade_pnls.append(trade_acc)
            trade_mfes.append(info.get("trade_mfe", 0.0))
            trade_maes.append(info.get("trade_mae", 0.0))
            trade_holds.append(info.get("trade_hold_bars", 0))
            ew = info.get("trade_exit_why")
            if ew:
                trade_exits.append(ew)
            if cur_pos != 0:
                trade_acc = 0.0  # direction flip: fresh start
            else:
                trade_acc = 0.0

        prev_pos = cur_pos

    m  = compute_metrics(eq_curve)
    ts = _compute_trade_stats(trade_pnls, trade_mfes, trade_maes, trade_holds, trade_exits)
    n  = max(n, 1)
    return {
        "ret_pct":    m["total_ret"],
        "equity":     float(eq_curve[-1]),
        "max_dd":     m["max_dd"],
        "sharpe":     m["sharpe"],
        "pct_long":   longs  / n * 100,
        "pct_short":  shorts / n * 100,
        "pct_flat":   flats  / n * 100,
        "trade_stats": ts,
    }


# ── episode accumulator ────────────────────────────────────────────────────────

def _reset_ep():
    return {
        "longs": 0, "shorts": 0, "flats": 0, "max_dd": 0.0, "trades": 0,
        "trade_pnls":  [],  # accumulated PnL per closed trade
        "trade_mfes":  [],  # MFE % per closed trade
        "trade_maes":  [],  # MAE % per closed trade
        "trade_holds": [],  # hold bars per closed trade
        "trade_exits": [],  # exit reason per closed trade
    }


def _update_ep(ep: dict, info: dict):
    pos = info["position"]
    if   pos ==  1: ep["longs"]  += 1
    elif pos == -1: ep["shorts"] += 1
    else:           ep["flats"]  += 1
    ep["max_dd"] = max(ep["max_dd"], info["drawdown"])


# ── trade-level buffer fill helper ─────────────────────────────────────────────

def _run_trade_steps(env, agent, n_steps, store=True, seed=None):
    """Run n_steps env steps collecting trade-level transitions."""
    obs, _ = env.reset(seed=seed) if seed is not None else (env.reset()[0], None)
    prev_position    = 0
    entry_obs        = None
    entry_action     = None
    trade_reward_acc = 0.0
    trades_stored    = 0

    for _ in range(n_steps):
        action = env.action_space.sample()
        next_obs, reward, terminated, truncated, info = env.step(action)
        done         = terminated or truncated
        cur_position = int(info["position"])

        if prev_position == 0 and cur_position != 0:
            entry_obs        = obs.copy()
            entry_action     = action.copy()
            trade_reward_acc = reward
        elif prev_position != 0 and cur_position == prev_position:
            trade_reward_acc += reward
        elif prev_position != 0:
            trade_reward_acc += reward
            if store and entry_obs is not None:
                agent.store(entry_obs, entry_action, trade_reward_acc, next_obs, done)
                trades_stored += 1
            if cur_position != 0:
                entry_obs        = obs.copy()
                entry_action     = action.copy()
                trade_reward_acc = 0.0
            else:
                entry_obs        = None
                entry_action     = None
                trade_reward_acc = 0.0

        prev_position = cur_position
        if done:
            if cur_position != 0 and store and entry_obs is not None:
                agent.store(entry_obs, entry_action, trade_reward_acc, next_obs, True)
                trades_stored += 1
            prev_position    = 0
            entry_obs        = None
            entry_action     = None
            trade_reward_acc = 0.0
            obs, _ = env.reset()
        else:
            obs = next_obs

    return trades_stored


# ── main ───────────────────────────────────────────────────────────────────────

def train(seed: int = 42, total_steps: int = TOTAL_STEPS, resume_tag: str = None):
    set_seed(seed)
    log = _setup_logging(seed)
    tag = f"s{seed}"
    dev = select_device()
    W   = 65

    feats, close = load_features()
    feats = feats.fillna(0.0)
    market_cols = list(feats.columns)
    n_feat      = len(market_cols) + N_PORTFOLIO_FEATS

    train_env = BTCEnv(feats, close, mode="train")

    # Bear regime oversampling: 25% of RL episodes start in 2022 (reduced from 40% — avoid regime seesaw)
    _tidx = train_env._features.index
    _bear_start = max(int((_tidx >= "2022-01-01").argmax()), SEQ_LEN)
    _bear_end   = max(_bear_start + 1, int((_tidx <= "2022-12-31").sum()) - 100)

    def _train_reset(env: BTCEnv) -> np.ndarray:
        if random.random() < 0.25 and _bear_end > _bear_start:
            idx = random.randint(_bear_start, _bear_end)
            obs, _ = env.reset(options={"start_idx": idx})
        else:
            obs, _ = env.reset()
        return obs

    # TIA v2: multi-regime validation (3 periods, diverse market conditions)
    _REGIME_LABELS = [f"{s[:7]}" for s, _ in VAL_REGIMES]  # auto-derive from config dates
    val_envs = [
        BTCEnv(feats, close, date_range=(start, end))
        for start, end in VAL_REGIMES
    ]

    agent = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, dev)

    # Pillar 2 + 3: Trade ranking filter and Kelly sizer (local; reset on fresh starts only)
    trade_ranker = TradeRanker()
    kelly_sizer  = KellySizer()

    step            = 0
    ep_num          = 0
    best_val_composite = -np.inf  # composite = avg_sharpe + 0.5×min_sharpe — all-regime robustness
    total_trades    = 0

    log.info("═" * W)
    log.info(f"  BTC DRL — SAC Training (Session 8)   seed={seed}   device={dev}")
    if resume_tag:
        log.info(f"  MODE: RESUME from  {resume_tag}")
    log.info("─" * W)
    log.info(f"  Data")
    log.info(f"    Train  : 2021-01-01 → {TRAIN_END}   ({len(train_env._features):,} bars)")
    for (s, e), lbl, env in zip(VAL_REGIMES, _REGIME_LABELS, val_envs):
        log.info(f"    Val [{lbl}]: {s} → {e}   ({len(env._features):,} bars)")
    log.info(f"    OOS    : {TEST_START} onward   (never touched)")
    log.info(f"  Regularisation: weight_decay={WEIGHT_DECAY}")
    log.info(f"  Model")
    log.info(f"    Obs    : {n_feat} features × {SEQ_LEN} bars")
    log.info(f"    Action : 5D  [pos_size, sl_atr_mult, tp_atr_mult, trail_on, hold_target(8h-30d)]")
    log.info(f"  Training")
    log.info(f"    Steps  : {total_steps:,}   Warmup: {WARMUP_TRADES} trades   Val every: {VAL_EVERY:,}")
    log.info(f"    Replay : trade-level (1 entry per closed trade)   batch={BATCH_SIZE}")
    log.info(f"    Update : every {UPDATE_EVERY_TRADES} trades × {G_STEPS} grad step(s)")
    log.info(f"  Hyperparams")
    log.info(f"    LR actor={LR_ACTOR}  critic={LR_CRITIC}  alpha={LR_ALPHA}")
    log.info(f"    γ={GAMMA}  τ={TAU}  DD_kill={MAX_DRAWDOWN_KILL*100:.0f}%")
    log.info("═" * W)
    log.info("")

    roll_ret  = deque(maxlen=ROLL_N)
    roll_liq  = deque(maxlen=ROLL_N)
    roll_bars = deque(maxlen=ROLL_N)
    loss_buf  = defaultdict(lambda: deque(maxlen=200))

    wu_start = time.time()

    # ══════════════════════════════════════════════════════════════════════════
    # PATH A — RESUME
    # ══════════════════════════════════════════════════════════════════════════
    if resume_tag:
        log.info(f"─── RESUMING from checkpoint: {resume_tag} " + "─" * 20)
        state           = agent.load(resume_tag)
        step            = state.get("step",            0)
        ep_num          = state.get("ep_num",          0)
        best_val_composite = state.get("best_val_composite", -np.inf)
        total_trades       = state.get("total_trades",       0)
        log.info(f"  Restored  step={step:,}  ep={ep_num}  best_val_composite={best_val_composite:+.4f}")
        log.info("")

        fill_steps = min(RESUME_FILL, step)
        log.info(f"  Pre-filling replay buffer: {fill_steps:,} steps (trade-level)…")
        trades_stored = _run_trade_steps(train_env, agent, fill_steps, store=True)
        log.info(f"  Buffer ready ({len(agent.buffer):,} trades).  Jumping to step {step:,}…")
        log.info("")

        obs      = _train_reset(train_env)
        ep       = _reset_ep()
        ep_start = step

    # ══════════════════════════════════════════════════════════════════════════
    # PATH B — FRESH START
    # ══════════════════════════════════════════════════════════════════════════
    else:
        # ── Stage 0: Supervised pretrain (Beta + Alpha heads) ──────────────
        log.info(f"─── STAGE 0: SUPERVISED PRETRAIN (SharedModel) " + "─" * 17)
        log.info("  Beta head  : regime classification (Bull/Bear/Range)")
        log.info("  Alpha head : trade quality multi-task (return, MFE, MAE, TP, hold)")
        log.info("  After pretrain: encoder weights → Actor")
        log.info("")
        shared_model = SharedModel(market_cols, N_PORTFOLIO_FEATS).to(dev)
        pretrain_shared_model(shared_model, feats, close, dev, log)
        shared_model.copy_encoder_to(agent.actor)
        del shared_model
        if dev.type == "cuda":
            torch.cuda.empty_cache()
        log.info("")

        # ── Stage 1: BC Risk Pretraining ───────────────────────────────────
        pretrain_actor(agent.actor, feats, close, dev, log)

        # Recalibrate OOD diagnostics after BC+supervised pretrain.
        # Both pretrain phases shift the encoder z-space; if diagnostics running_mean/std
        # were seeded during pretrain (or left at init zeros), the first RL batch will score
        # ood≈1.0 and DriftManager enters BLOCK permanently (n_updates>0 → EMA from wrong stats).
        # Hard-reset to force fresh calibration from the first RL training batch onward.
        agent.actor.diagnostics.n_updates.zero_()
        agent.actor.diagnostics.running_mean.zero_()
        agent.actor.diagnostics.running_std.fill_(1.0)
        agent.drift_manager._ood_ema = 0.0
        log.info("  OOD diagnostics reset — will recalibrate from first RL training batch.")
        log.info("")

        log.info(f"─── STAGE 2: WARMUP  (collecting {WARMUP_TRADES} complete trades) " + "─" * 10)
        log.info("  Random policy fills trade-level replay buffer.")
        log.info("")

        wu_obs, _ = train_env.reset(seed=seed)
        wu_prev   = 0
        wu_entry_obs = wu_entry_act = None
        wu_acc    = 0.0
        wu_trades = 0
        wu_step   = 0

        while wu_trades < WARMUP_TRADES:
            wu_act = train_env.action_space.sample()
            wu_nxt, wu_rew, wu_term, wu_trunc, wu_info = train_env.step(wu_act)
            wu_done = wu_term or wu_trunc
            wu_cur  = int(wu_info["position"])

            if wu_prev == 0 and wu_cur != 0:
                wu_entry_obs = wu_obs.copy()
                wu_entry_act = wu_act.copy()
                wu_acc = wu_rew
            elif wu_prev != 0 and wu_cur == wu_prev:
                wu_acc += wu_rew
            elif wu_prev != 0:
                wu_acc += wu_rew
                if wu_entry_obs is not None:
                    agent.store(wu_entry_obs, wu_entry_act, wu_acc, wu_nxt, wu_done)
                    agent.store_trade(wu_entry_obs, wu_entry_act, wu_acc, wu_step,
                                      mfe=wu_info.get("trade_mfe", 0.0),
                                      mae=wu_info.get("trade_mae", 0.0),
                                      hold_bars=wu_info.get("trade_hold_bars", 0.0),
                                      tp_hit=int(wu_info.get("trade_exit_why") == "tp"))
                    wu_trades += 1
                wu_entry_obs = wu_entry_act = None
                wu_acc = 0.0
                if wu_cur != 0:
                    wu_entry_obs = wu_obs.copy()
                    wu_entry_act = wu_act.copy()

            wu_prev = wu_cur
            wu_step += 1

            if wu_done:
                if wu_cur != 0 and wu_entry_obs is not None:
                    agent.store(wu_entry_obs, wu_entry_act, wu_acc, wu_nxt, True)
                    agent.store_trade(wu_entry_obs, wu_entry_act, wu_acc, wu_step)
                    wu_trades += 1
                wu_prev = 0; wu_entry_obs = wu_entry_act = None; wu_acc = 0.0
                wu_obs, _ = train_env.reset()
            else:
                wu_obs = wu_nxt

            if wu_trades % 50 == 0 and wu_trades > 0:
                log.info(f"  warmup {wu_trades}/{WARMUP_TRADES} trades  ({wu_step:,} env steps)")

        log.info(f"  Warmup done.  Buffer: {len(agent.buffer):,} trades  ({wu_step:,} env steps).")
        agent.set_drift_baseline()
        log.info(f"  {agent.km_summary()}")
        log.info("")

        obs      = _train_reset(train_env)
        ep       = _reset_ep()
        ep_start = 0

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 3: LEARNING
    # ══════════════════════════════════════════════════════════════════════════
    remaining = total_steps - step
    log.info(f"─── STAGE 3: LEARNING  (steps {step:,} → {total_steps:,}, {remaining:,} to go) " + "─" * 3)
    log.info(f"  Trade-level replay  │  Update every {UPDATE_EVERY_TRADES} trades × {G_STEPS} grad step  │  Val every {VAL_EVERY:,}")
    log.info("")

    learn_start      = time.time()
    learn_start_step = step

    prev_position    = 0
    entry_obs        = None
    entry_action     = None
    trade_reward_acc = 0.0
    trades_since_upd = 0
    losses           = {}

    while step < total_steps:
        action     = agent.select_action(obs)
        actor_info = agent.last_actor_info

        # Pillars 2 + 3: rank and Kelly-size new trade entries only
        if actor_info.get("rule_active", 0.0) > 0.5 and prev_position == 0:
            opp_score = actor_info.get("opp_score", 50.0)
            trade_ranker.record(opp_score)
            if not trade_ranker.should_execute(opp_score):
                action    = action.copy()
                action[0] = -1.0          # force pos_size → POS_SIZE_MIN → env soft-skips
            else:
                kelly_pos = kelly_sizer.compute(
                    ret_pred          = actor_info.get("ret_pred",     0.0),
                    exp_variance      = actor_info.get("exp_variance", 0.01),
                    alpha_conf        = actor_info.get("alpha_conf",   0.5),
                    ood_score         = actor_info.get("ood_score",    0.0),
                    memory_win_rate   = agent.knowledge_memory.win_rate(),
                    opportunity_score = opp_score,
                    risk_budget       = actor_info.get("risk_budget",  1.0),
                )
                rng       = max(POS_SIZE_MAX - POS_SIZE_MIN, 1e-8)
                encoded   = (kelly_pos - POS_SIZE_MIN) / rng * 2.0 - 1.0
                action    = action.copy()
                action[0] = float(np.clip(encoded, -1.0, 1.0))

        next_obs, reward, terminated, truncated, info = train_env.step(action)
        done         = terminated or truncated
        cur_position = int(info["position"])

        # ── Trade state machine ────────────────────────────────────────────────
        if prev_position == 0 and cur_position != 0:
            entry_obs        = obs.copy()
            entry_action     = action.copy()
            trade_reward_acc = reward

        elif prev_position != 0 and cur_position == prev_position:
            trade_reward_acc += reward

        elif prev_position != 0:
            trade_reward_acc += reward
            if entry_obs is not None:
                agent.store(entry_obs, entry_action, trade_reward_acc, next_obs, done)
                agent.store_trade(entry_obs, entry_action, trade_reward_acc, step,
                                  mfe=info.get("trade_mfe", 0.0),
                                  mae=info.get("trade_mae", 0.0),
                                  hold_bars=info.get("trade_hold_bars", 0.0),
                                  tp_hit=int(info.get("trade_exit_why") == "tp"))
                trades_since_upd += 1
                total_trades     += 1
                ep["trades"]     += 1
                ep["trade_pnls"].append(trade_reward_acc)
                ep["trade_mfes"].append(info.get("trade_mfe", 0.0))
                ep["trade_maes"].append(info.get("trade_mae", 0.0))
                ep["trade_holds"].append(info.get("trade_hold_bars", 0))
                ew = info.get("trade_exit_why")
                if ew: ep["trade_exits"].append(ew)
            if cur_position != 0:
                entry_obs        = obs.copy()
                entry_action     = action.copy()
                trade_reward_acc = 0.0
            else:
                entry_obs        = None
                entry_action     = None
                trade_reward_acc = 0.0

        # ── SAC update ────────────────────────────────────────────────────────
        if trades_since_upd >= UPDATE_EVERY_TRADES and len(agent.buffer) >= BATCH_SIZE:
            for _ in range(G_STEPS):
                l = agent.update()
                if l: losses = l
            for k, v in losses.items():
                loss_buf[k].append(v)
            trades_since_upd = 0

        prev_position = cur_position
        step += 1
        _update_ep(ep, info)

        # ── Episode done ───────────────────────────────────────────────────────
        if done:
            if cur_position != 0 and entry_obs is not None:
                agent.store(entry_obs, entry_action, trade_reward_acc, next_obs, True)
                agent.store_trade(entry_obs, entry_action, trade_reward_acc, step)
                trades_since_upd += 1
                total_trades     += 1
                ep["trades"]     += 1
                ep["trade_pnls"].append(trade_reward_acc)
                ew = info.get("trade_exit_why")
                if ew: ep["trade_exits"].append(ew)

            prev_position    = 0
            entry_obs        = None
            entry_action     = None
            trade_reward_acc = 0.0

            ep_num  += 1
            bars     = step - ep_start
            ret_pct  = (info["equity"] / INITIAL_CAPITAL - 1) * 100
            n_ep     = ep["longs"] + ep["shorts"] + ep["flats"] or 1
            status   = "LIQUIDATED" if truncated else "completed "
            avg      = {k: float(np.mean(v)) for k, v in loss_buf.items() if v}
            elapsed  = max(time.time() - learn_start, 1e-6)
            sps      = max(step - learn_start_step, 0) / elapsed
            eta      = _eta(total_steps - step, sps)

            log.info(
                f"  [EP {ep_num:>4}]  bars={bars:>5,}  ret={ret_pct:+6.1f}%  {status}  "
                f"L/S/F={ep['longs']/n_ep*100:.0f}/"
                f"{ep['shorts']/n_ep*100:.0f}/"
                f"{ep['flats']/n_ep*100:.0f}%  "
                f"trades={ep['trades']}  "
                f"│ logπ={avg.get('log_pi_mean',0):+.1f}  "
                f"Qc={avg.get('critic_loss',0):.3f}  "
                f"sps={sps:.0f}  ETA={eta}"
            )

            ts = _compute_trade_stats(
                ep["trade_pnls"], ep["trade_mfes"],
                ep["trade_maes"], ep["trade_holds"], ep["trade_exits"],
            )
            if ts:
                log.info(
                    f"           ├ dist p10={ts['p10']:+.2f}%  p50={ts['p50']:+.2f}%  p90={ts['p90']:+.2f}%"
                    f"  win={ts['win_rate']:.0%}  pf={ts['pf']:.1f}  TQS={ts['tqs']:.2f}"
                )
                log.info(
                    f"           └ mfe_p50={ts['mfe_p50']:.2f}%  mae_p50={ts['mae_p50']:.2f}%"
                    f"  tp_rate={ts['tp_rate']:.0%}  avg_hold={ts['avg_hold']:.0f}b"
                )
            rk = trade_ranker.stats()
            if rk["seen"] > 0:
                log.info(
                    f"           ╌ rank thr={rk['threshold']:.1f}  "
                    f"exec={rk['exec_rate']:.0%}  "
                    f"seen={rk['seen']}  skip={rk['skipped']}"
                )

            roll_ret.append(ret_pct)
            roll_liq.append(truncated)
            roll_bars.append(bars)
            ep       = _reset_ep()
            ep_start = step

            # Training OOD deadlock prevention: if ood_ema has saturated (→1.0),
            # position sizes are forced to zero and training signal disappears.
            # Reset at episode boundaries so the next episode can trade normally.
            if agent.drift_manager._ood_ema > 0.85:
                log.info(f"  OOD deadlock prevention: ood_ema={agent.drift_manager._ood_ema:.3f} → reset to 0.0")
                agent.drift_manager._ood_ema = 0.0

            obs      = _train_reset(train_env)

        else:
            obs = next_obs

        # ── Validation (TIA v2: multi-regime) ────────────────────────────────
        if step % VAL_EVERY == 0:
            vm      = multi_evaluate(agent, val_envs, _REGIME_LABELS)
            avg     = {k: float(np.mean(v)) for k, v in loss_buf.items() if v}
            elapsed = max(time.time() - learn_start, 1e-6)
            sps     = max(step - learn_start_step, 0) / elapsed
            eta     = _eta(total_steps - step, sps)

            r_ret  = float(np.mean(roll_ret))  if roll_ret  else 0.0
            r_liq  = sum(roll_liq) / max(len(roll_liq), 1) * 100
            r_bars = float(np.mean(roll_bars)) if roll_bars else 0.0

            # Best checkpoint: avg_sharpe + 0.5×min_sharpe
            # Rewards both overall quality AND worst-regime robustness.
            # Never zeroes out on slightly-negative avg_ret (unlike the old multiply-gate).
            val_composite = vm["avg_sharpe"] + 0.5 * vm["sharpe"]
            is_best = val_composite > best_val_composite
            star    = "★ NEW BEST" if is_best else "          "

            log.info("")
            log.info(f"  ┌─ VAL @ step {step:,} " + "─" * 40)
            log.info(
                f"  │  minSharpe={vm['sharpe']:+.3f}   avgSharpe={vm['avg_sharpe']:+.3f}   "
                f"avg_ret={vm['ret_pct']:+.2f}%   worstDD={vm['max_dd']:.1f}%"
            )
            # Per-regime breakdown
            for lbl, sh in vm["regime_sharpes"].items():
                log.info(f"  │    [{lbl}]  Sharpe={sh:+.3f}")
            log.info(
                f"  │  buffer={len(agent.buffer):,} trades  total_trades={total_trades:,}  "
                f"{star}  prev_best={best_val_composite:+.4f}   ETA={eta}"
            )

            ts = vm.get("trade_stats")
            if ts:
                log.info(
                    f"  │  [val trades n={ts['n']}]"
                    f"  p10={ts['p10']:+.2f}%  p50={ts['p50']:+.2f}%  p90={ts['p90']:+.2f}%"
                    f"  win={ts['win_rate']:.0%}  pf={ts['pf']:.1f}  TQS={ts['tqs']:.2f}"
                )
                log.info(
                    f"  │  mfe_p50={ts['mfe_p50']:.2f}%  mae_p50={ts['mae_p50']:.2f}%"
                    f"  tp_rate={ts['tp_rate']:.0%}  avg_hold={ts['avg_hold']:.0f}b"
                )
            log.info(
                f"  │  L/S/F={vm['pct_long']:.0f}/{vm['pct_short']:.0f}/{vm['pct_flat']:.0f}%"
                f"  [last-{ROLL_N} eps]  avg_ret={r_ret:+.1f}%  liq={r_liq:.0f}%  bars={r_bars:.0f}"
            )
            log.info(f"  │  {agent.drift_status()}")
            log.info(f"  │  {agent.km_summary()}")
            rk = trade_ranker.stats()
            log.info(
                f"  │  rank thr={rk['threshold']:.1f}  exec={rk['exec_rate']:.0%}"
                f"  seen={rk['seen']}  skip={rk['skipped']}"
            )
            log.info(f"  └" + "─" * 53)
            log.info("")

            with open(LOG_DIR / f"metrics_{tag}.jsonl", "a") as f:
                f.write(json.dumps({
                    "step": step,
                    "min_sharpe": vm["sharpe"],
                    "avg_sharpe": vm["avg_sharpe"],
                    "regime_sharpes": vm["regime_sharpes"],
                    "ret_pct": vm["ret_pct"],
                    "max_dd": vm["max_dd"],
                    **avg,
                    **(ts or {}),
                }) + "\n")

            if is_best:
                best_val_composite = val_composite
                agent.save(f"best_{tag}", train_state={
                    "step": step, "ep_num": ep_num,
                    "best_val_composite": best_val_composite, "total_trades": total_trades,
                })

            # Flush all pending CUDA ops from val (multi_evaluate runs parallel CPU inference
            # that syncs GPU actor weights; drain the stream before recalibrating stats).
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()

            # Reset drift EMA only — keep running_mean/std so training obs don't immediately
            # look OOD. Resetting to (0,1) prior caused the encoder's real z-distribution
            # to score as OOD on every training step → kelly sizer zeroed positions →
            # policy trained on near-zero-reward signal → mode collapse (logπ → -1.9).
            # The diagnostics EMA (α=0.15) self-corrects within ~20 training updates anyway.
            agent.drift_manager._ood_ema = 0.0
            log.info("  OOD drift EMA reset → training resumes with maintained z-space stats.")

        # ── Periodic checkpoint ────────────────────────────────────────────────
        if step % CKPT_EVERY == 0:
            agent.save(f"step{step}_{tag}", train_state={
                "step": step, "ep_num": ep_num,
                "best_val_composite": best_val_composite, "total_trades": total_trades,
            })

    # ══════════════════════════════════════════════════════════════════════════
    # DONE
    # ══════════════════════════════════════════════════════════════════════════
    agent.save(f"final_{tag}", train_state={
        "step": step, "ep_num": ep_num,
        "best_val_composite": best_val_composite, "total_trades": total_trades,
    })

    total_secs = time.time() - wu_start
    r_ret  = float(np.mean(roll_ret))  if roll_ret  else 0.0
    r_liq  = sum(roll_liq) / max(len(roll_liq), 1) * 100

    log.info("")
    log.info("═" * W)
    log.info(f"  TRAINING COMPLETE   seed={seed}   (TIA v2 / Session 9)")
    log.info("─" * W)
    log.info(f"  Total env steps  : {step:,}")
    log.info(f"  Total trades     : {total_trades:,}")
    log.info(f"  Total episodes   : {ep_num}")
    log.info(f"  Wall time        : {total_secs/3600:.1f}h")
    log.info(f"  Liq rate (last {ROLL_N}): {r_liq:.0f}%")
    log.info(f"  Avg ep ret (last {ROLL_N}): {r_ret:+.1f}%")
    log.info(f"  Best val composite: {best_val_composite:+.4f}  →  best_{tag}.pt")
    log.info("─" * W)
    log.info(f"  Evaluate OOS: python DRL_BTC/scripts/evaluate.py --tag best_{tag}")
    log.info(f"  Resume:       python DRL_BTC/training/train.py --resume final_{tag} --seed {seed}")
    log.info("═" * W)

    return agent


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Train BTC DRL SAC agent")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--steps",  type=int, default=TOTAL_STEPS)
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument("--list",   action="store_true")
    args = parser.parse_args()

    if args.list:
        _list_checkpoints()
    else:
        train(seed=args.seed, total_steps=args.steps, resume_tag=args.resume)
