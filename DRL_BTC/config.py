"""Central configuration for DRL_BTC."""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_ROOT     = ROOT / "dataset" / "BTC"
FEATURE_CACHE = ROOT / "DRL_BTC" / "data" / "features"
CKPT_DIR      = ROOT / "DRL_BTC" / "data" / "checkpoints"
MODEL_DIR     = ROOT / "DRL_BTC" / "models" / "saved"
LOG_DIR       = ROOT / "DRL_BTC" / "logs"

# ── Data ───────────────────────────────────────────────────────────────────────
TIMEFRAMES  = ["1h", "4h", "1d"]      # base + context timeframes
BASE_TF     = "1h"
SEQ_LEN     = 48                       # 48 × 1h = 2 days of history per step

TRAIN_END   = "2026-06-14"   # S27: same training window (feature cache to 2026-06-16)
VAL_START   = "2022-01-01"   # val = full 2022 bear year (tests SHORT ability; always-long scores ≈-15%)
VAL_END     = "2022-12-31"   # BTC -66% this year — a model that can't short will score poorly
TEST_START  = "2026-06-15"   # OOS starts after TRAIN_END

# ── Environment ────────────────────────────────────────────────────────────────
INITIAL_CAPITAL    = 1_000_000.0       # S27: match platform scale ($1M); agent learns at platform cost levels
FEE_RATE           = 0.0018            # S27: 0.04% fee + 0.14% avg slippage = 0.18% round-trip per leg
                                       # Forces agent to be selective — high-frequency churn is now unprofitable
FUNDING_PER_BAR    = 0.0001 / 8.0     # ~0.01% per 8h → per 1h bar
MAX_LEVERAGE       = 2.0
MIN_LEVERAGE       = 1.0
MAX_POS_FRACTION   = 0.50
MIN_POS_FRACTION   = 0.05
CONFIDENCE_GATE    = 0.0               # disabled
DIR_THRESHOLD      = 0.15             # S27: action[0] dead zone ±0.15 → FLAT; outside → LONG/SHORT
ENTRY_THRESHOLD    = 0.15             # kept for legacy compat (no longer used in env)
FLAT_PENALTY       = 0.010            # kept for legacy compat
MAX_DRAWDOWN_KILL  = 0.50              # auto-close if DD > 50%

# ── Model ──────────────────────────────────────────────────────────────────────
LSTM_HIDDEN    = 256
LSTM_LAYERS    = 2
LSTM_DROPOUT   = 0.1
FC_HIDDEN      = 256
ACTION_DIM     = 5      # [pos_size, sl_atr_mult, tp_atr_mult, trail_on, hold_target]

# ── SAC Training ───────────────────────────────────────────────────────────────
BUFFER_SIZE    = 100_000               # 50K → 100K  (larger buffer for longer 1M-step run)
BATCH_SIZE     = 512                   # 64 → 512    (T4 Tensor Cores need ≥128; 512 fills them)
LR_ACTOR       = 3e-4
LR_CRITIC      = 3e-4
LR_ALPHA       = 0                     # SAC auto-entropy tuning DISABLED — α frozen at ALPHA_FIXED
                                       # LR=3e-4 caused mode collapse: logπ=-3.4 < target=-2.5 drove α→0
                                       # over 8+ eps; once α≈0 policy snaps deterministic (logπ→-1.8)
GAMMA          = 0.99
TAU            = 0.005                 # soft-update coefficient
TARGET_ENTROPY = -float(ACTION_DIM) / 2.0
ALPHA_FIXED    = 0.05                  # 0.10 → 0.05: halves entropy bonus; Q gradient matters 2× more → logπ converges -3.3→-2.5 faster
                                       # S23 had logπ=-3.3 (too random); with α=0.05 Q signal pulls policy toward quality actions sooner
GRAD_CLIP      = 1.0
UPDATE_EVERY_TRADES = 1                # 5 → 1  (update every closed trade; GPU does more work per env step)
G_STEPS        = 2                     # 5 → 2: key S24 fix — 5 was too aggressive with sparse buffer (1.4% full at step-30K)
                                       # caused regime rotation (catastrophic forgetting); 2 updates/trade = 60% less policy shift
WARMUP_TRADES  = 1500                  # 300 → 1500: denser buffer before first gradient; 300 was too thin (Qc=0.002 for 7 eps)
TOTAL_STEPS    = 700_000               # S30: same 700K — strategy signal features (36 cols) give richer signal

# Reward shaping coefficients
REWARD_SCALE        = 1.0
CONFIDENCE_BONUS    = 0.25             # unused in env; kept for legacy compat
CONFIDENCE_PENALTY  = 0.40            # unused in env; kept for legacy compat
DD_PENALTY_SCALE    = 3.0             # drawdown penalty multiplier
CHOP_PENALTY        = 0.02            # small penalty for trading in chop

# ── Session 7: Risk Action Space (4D — exit_signal removed) ───────────────────
# action[0] pos_size  : linear remap [-1,1] → [POS_SIZE_MIN, POS_SIZE_MAX]
# action[1] sl_atr    : linear remap [-1,1] → [SL_ATR_MULT_MIN, SL_ATR_MULT_MAX]
# action[2] tp_atr    : linear remap [-1,1] → [TP_ATR_MULT_MIN, TP_ATR_MULT_MAX]
# action[3] trail_on  : sigmoid(×3) > 0.5
MAX_HOLD_BARS    = 720  # 30 days — hard ceiling; agent controls per-trade target via action[4]
MIN_HOLD_BARS    = 48   # S29: 24h → 48h — combo monsters hold ~168h avg; forcing longer holds reduces overtrading
MAX_EPISODE_BARS = 1500 # ~62 days — more regime rotations per unit time
# Exit: SL/TP/direction_change(after MIN_HOLD)/per-trade hold target timeout
# action[4] hold_target decoded on log scale: HOLD_TARGET_LOG_MIN → HOLD_TARGET_LOG_MAX bars
HOLD_TARGET_LOG_MIN = 48   # S29: sync with MIN_HOLD_BARS
HOLD_TARGET_LOG_MAX = 720  # maximum choosable hold: 30 days
POS_SIZE_MIN     = 0.00   # 0% — actor can output pos_size=0 to soft-skip a trade (Session 9)
POS_SIZE_MAX     = 1.00   # S28: 0.20→1.00 — agent can go fully all-in at max conviction.
                           # Submission uses dynamic target = (env_size/POS_SIZE_MAX)*TARGET_SCALE → target=±1 at peak.
                           # FEE_RATE=0.0018 forces agent to be selective — churn is penalised even at large sizes.
SL_ATR_MULT_MIN  = 1.0    # 1.0× ATR minimum stop distance
SL_ATR_MULT_MAX  = 2.5    # S25: UNLOCKED (was fixed 1.0) — agent chooses 1–2.5×ATR; learns wide SL for trends, tight for ranges
                           # S24: fixed 1×ATR caused 67% SL rate — noise alone triggered stops before trades developed
TP_ATR_MULT_MIN  = 1.5    # R:R ≥ 1.5 enforced even at random init
TP_ATR_MULT_MAX  = 5.0    # S25: 3.0 → 5.0 — more headroom for trend trades; improves payoff ratio from 1.53
ATR_FEATURE      = "atr_pct_1h"  # normalized ATR column in feature matrix
ATR_SCALE        = 0.10          # reverse normalization: atr_pct=(ATR14/close).clip(0,.1)/.1 → ×0.10 = real fraction

# ── Session 6: BC Exit Pretraining ────────────────────────────────────────────
BC_PRETRAIN_EPOCHS = 30    # epochs over the labeled dataset
BC_PRETRAIN_LR     = 3e-4  # Adam LR for BC phase
BC_PRETRAIN_BATCH  = 256   # batch size
BC_SL_ATR_DEFAULT  = 1.5   # oracle stop: exit if loss > 1.5×ATR from entry
BC_TP_ATR_DEFAULT  = 3.0   # oracle TP:   exit if gain > 3.0×ATR from entry

# ── Session 8: Supervised Pretrain (Beta + Alpha heads via SharedModel) ────────
# Stage 1: Beta head  — regime (Bull/Bear/Range) classification + vol + trend
# Stage 2: Alpha head — multi-task trade quality prediction (return, MFE, MAE, TP, hold)
# Stage 3: Joint fine-tune — all heads together at lower LR
# After completion: encoder weights copied to RL Actor.
SUPERVISED_PRETRAIN_LR    = 3e-4   # Adam LR for both stages
SUPERVISED_PRETRAIN_BATCH = 256    # batch size (same as BC)
BETA_PRETRAIN_EPOCHS      = 30     # Stage 1 epochs
ALPHA_PRETRAIN_EPOCHS     = 30     # Stage 2 epochs
BETA_REGIME_THRESH        = 0.010  # 1% 24h fwd return → Bull/Bear; else Range

# ── TIA v2: Multi-regime validation (Phase 1 — generalisation fix) ─────────────
# Replace single 2022 bear-only val with 3 regime-diverse windows.
# Early-stop on min Sharpe across all 3 (robustness criterion — must be good everywhere).
VAL_REGIMES = [
    ("2022-01-01", "2022-12-31"),   # bear year         (BTC -66%)
    ("2023-07-01", "2023-12-31"),   # recovery/bull      (+100% in H2 2023)
    ("2021-06-01", "2021-12-31"),   # mid-cycle bull     (post-crash recovery → ATH $67K)
    ("2024-01-01", "2024-06-30"),   # consolidation      (ETF euphoria → correction → range)
    ("2025-07-01", "2025-12-31"),   # S25: was 2025H1 (always failed); now 2025H2 — the OOS regime that killed S24 platform results
]

# ── TIA v2: Regularisation ─────────────────────────────────────────────────────
WEIGHT_DECAY = 1e-4   # L2 weight decay in Actor + Critic Adam optimisers

# ── TIA v2: Market Diagnostics (OOD detection via z-space EMA) ────────────────
OOD_EMA_ALPHA   = 0.15    # EMA smoothing for z-space running statistics (0.05→0.15 — faster adaptation after pretrain shift)
OOD_WARN_THRESH = 3.0     # mean |z_norm| above this → ood_score ≈ 1.0

# ── TIA v2: BetaEngine stability label ────────────────────────────────────────
BETA_STABILITY_HORIZON = 12   # bars ahead to check if regime label stays the same

# ── TIA v3: Regime embedding ───────────────────────────────────────────────────
BETA_EMBED_DIM = 32           # regime embedding dimension (latent rich representation)

# ── TIA v3: Rule Engine features ──────────────────────────────────────────────
RULE_FEAT_DIM = 3             # rule_direction(1) + rule_confidence(1) + rule_active(1)

# ── TIA v3: Risk Budget Controller ────────────────────────────────────────────
# Deterministic tiered position scaling based on portfolio drawdown.
# Applied INSIDE btc_env.py (hard cap) and as a soft feature in the policy net.
RISK_BUDGET_DD_10 = 0.70      # budget at DD >= 10%  (was 1.0)
RISK_BUDGET_DD_20 = 0.50      # budget at DD >= 20%
RISK_BUDGET_DD_30 = 0.25      # budget at DD >= 30%
RISK_BUDGET_MIN   = 0.25      # never reduce below this (always allow some exposure)

# ── TIA v3: OOD thresholds ────────────────────────────────────────────────────
OOD_BLOCK_THRESH  = 1.5       # raised from 0.9 — reduce intra-episode OOD blocking during training
                               # ood_ema saturates at 1.0, so 1.5 effectively disables the block
                               # OOD detection still runs for monitoring; block only at inference via evaluate.py

# ── TIA v3: Knowledge Memory ──────────────────────────────────────────────────
KNOWLEDGE_MEMORY_SIZE = 5_000  # max stored trade experiences (ring buffer)
KNOWLEDGE_MEMORY_K    = 20     # top-K nearest neighbours (OOD-gated down to 10/5/0)

# 10-dim memory context vector fed to DecisionFusion + policy net:
#   avg_return, win_rate, avg_mfe, avg_mae, avg_hold, tp_rate,
#   sample_count, avg_similarity, memory_confidence, regime_match
MEMORY_FEAT_DIM = 10

# ── 5-Pillar ROI Plan ──────────────────────────────────────────────────────────

# Pillar 1: Opportunity Scoring — tiered position-size thresholds from 0-100 score
OPP_SCORE_THRESH_SKIP  = 30.0    # score < 30  → skip trade entirely
OPP_SCORE_THRESH_5PCT  = 40.0    # 30–40       → 5% position
OPP_SCORE_THRESH_10PCT = 55.0    # 40–55       → 10% position
OPP_SCORE_THRESH_15PCT = 70.0    # 55–70       → 15% position
OPP_SCORE_THRESH_20PCT = 85.0    # 70–85       → 20% position
                                  # ≥ 85        → POS_SIZE_MAX (25%)

# Pillar 2: Trade Ranking — rolling-percentile filter
TRADE_RANK_WINDOW  = 200    # scores kept in deque for percentile estimation
TRADE_RANK_PCTILE  = 0      # DISABLED — rank filter removed; pos_size=0 soft-skip handles selection internally
                            # S21: pctile=40 → exec fell 68%→29% (OOD blocking); S22: pctile=20 → exec fell 91%→44%
                            # Root cause: rank filter creates selection bias (long-bias ops score higher → filter amplifies)
                            # Fix: let agent's own pos_size action decide which trades to take (POS_SIZE_MIN=0.0)
TRADE_RANK_WARMUP  = 50     # minimum recorded scores before filter activates

# Pillar 3: Safe Kelly Criterion
KELLY_FRACTION = 0.25       # quarter-Kelly safety multiplier
KELLY_CAP      = 1.0        # maximum raw Kelly ratio before fraction is applied

# Pillar 4: Adaptive TP Extension
ADAPTIVE_TP_TRIGGER  = 0.60  # extend TP when unrealised ≥ 60% of original TP distance
ADAPTIVE_TP_EXTEND   = 0.50  # extend TP by 0.5 × ATR_at_entry each time
ADAPTIVE_TP_MAX_EXT  = 3     # maximum extensions per trade

# Pillar 5: Portfolio Objective — Sortino-weighted trade-close bonus
PORTFOLIO_SORTINO_WEIGHT = 0.02   # 4× Sortino bonus — stronger Sharpe-aligned reward signal
PORTFOLIO_SHARPE_WINDOW  = 30     # rolling window (trade count) for Sortino/PF
