"""Central configuration for DRL_BTC."""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT     = ROOT / "dataset" / "BTC"
FEATURE_CACHE = ROOT / "DRL_BTC" / "data" / "features"
CKPT_DIR      = ROOT / "DRL_BTC" / "data" / "checkpoints"
MODEL_DIR     = ROOT / "DRL_BTC" / "models" / "saved"
LOG_DIR       = ROOT / "DRL_BTC" / "logs"

# ── Data ───────────────────────────────────────────────────────────────────────
TIMEFRAMES  = ["1h", "4h", "1d"]      # base + context timeframes
BASE_TF     = "1h"
SEQ_LEN     = 48                       # 48 × 1h = 2 days of history per step

TRAIN_END   = "2024-12-31"   # train on full 2021-2024
VAL_START   = "2022-01-01"   # val = full 2022 bear year (tests SHORT ability; always-long scores ≈-15%)
VAL_END     = "2022-12-31"   # BTC -66% this year — a model that can't short will score poorly
TEST_START  = "2025-01-01"   # true OOS = 18 months of 2025-2026

# ── Environment ────────────────────────────────────────────────────────────────
INITIAL_CAPITAL    = 100_000.0         # USD starting capital
FEE_RATE           = 0.0004            # 0.04% taker fee (Binance futures)
FUNDING_PER_BAR    = 0.0001 / 8.0     # ~0.01% per 8h → per 1h bar
MAX_LEVERAGE       = 2.0               # reduced from 5× — prevents guaranteed ruin during early learning
MIN_LEVERAGE       = 1.0
MAX_POS_FRACTION   = 0.50              # reduced from 95% — limits exposure so agent survives long enough to learn
MIN_POS_FRACTION   = 0.05
CONFIDENCE_GATE    = 0.0               # disabled
DIR_THRESHOLD      = 0.02             # kept for legacy decode (action[0] unused in env now)
ENTRY_THRESHOLD    = 0.10             # composite signal threshold for rule-based entry (new)
FLAT_PENALTY       = 0.010            # kept in config but not applied in env (direction is rule-based)
MAX_DRAWDOWN_KILL  = 0.50              # auto-close if DD > 50%

# ── Model ──────────────────────────────────────────────────────────────────────
LSTM_HIDDEN    = 256
LSTM_LAYERS    = 2
LSTM_DROPOUT   = 0.1
FC_HIDDEN      = 256
ACTION_DIM     = 4      # [pos_size, sl_atr_mult, tp_atr_mult, trail_on]  — exit_signal removed (Session 7)

# ── SAC Training ───────────────────────────────────────────────────────────────
BUFFER_SIZE    = 100_000               # 50K → 100K  (larger buffer for longer 1M-step run)
BATCH_SIZE     = 512                   # 64 → 512    (T4 Tensor Cores need ≥128; 512 fills them)
LR_ACTOR       = 3e-4
LR_CRITIC      = 3e-4
LR_ALPHA       = 0.0                   # alpha is frozen (ALPHA_FIXED); auto-tuning disabled
GAMMA          = 0.99
TAU            = 0.005                 # soft-update coefficient
TARGET_ENTROPY = -float(ACTION_DIM) / 2.0
ALPHA_FIXED    = 0.3                   # fixed entropy temperature; replaces auto-tuned alpha
GRAD_CLIP      = 1.0
UPDATE_EVERY_TRADES = 1                # 5 → 1  (update every closed trade; GPU does more work per env step)
G_STEPS        = 10                    # 1 → 10 (10 gradient steps per update event; 80× vs Session 7)
WARMUP_TRADES  = 500                   # 300 → 500  (bigger buffer needs more warmup trades)
TOTAL_STEPS    = 600_000               # 500K → 600K  (sufficient for supervised-pretrained model)

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
# Exit is now rule-based only: SL/TP/direction_change/96-bar timeout
POS_SIZE_MIN     = 0.00   # 0% — actor can output pos_size=0 to soft-skip a trade (Session 9)
POS_SIZE_MAX     = 0.25   # 25% of equity maximum position
SL_ATR_MULT_MIN  = 0.5    # 0.5× ATR minimum stop distance
SL_ATR_MULT_MAX  = 3.0    # 3.0× ATR maximum stop distance
TP_ATR_MULT_MIN  = 1.0    # 1.0× ATR minimum profit target
TP_ATR_MULT_MAX  = 6.0    # 6.0× ATR maximum profit target
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
    ("2022-01-01", "2022-12-31"),   # bear year        (BTC -66%)
    ("2023-07-01", "2023-12-31"),   # recovery/bull     (+100% in H2 2023)
    ("2024-01-01", "2024-06-30"),   # ETF euphoria+peak (+75% then -22%)
]

# ── TIA v2: Regularisation ─────────────────────────────────────────────────────
WEIGHT_DECAY = 1e-4   # L2 weight decay in Actor + Critic Adam optimisers

# ── TIA v2: Market Diagnostics (OOD detection via z-space EMA) ────────────────
OOD_EMA_ALPHA   = 0.01    # EMA smoothing for z-space running statistics (slow update)
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
OOD_BLOCK_THRESH  = 0.9       # ood_score above this → DecisionFusionLayer forced to SKIP
                               # (applied as soft gate: size_mult ×= (1 - ood_block_weight))

# ── TIA v3: Knowledge Memory ──────────────────────────────────────────────────
KNOWLEDGE_MEMORY_SIZE = 5_000  # max stored trade experiences (ring buffer)
KNOWLEDGE_MEMORY_K    = 20     # top-K nearest neighbours (OOD-gated down to 10/5/0)

# 10-dim memory context vector fed to DecisionFusion + policy net:
#   avg_return, win_rate, avg_mfe, avg_mae, avg_hold, tp_rate,
#   sample_count, avg_similarity, memory_confidence, regime_match
MEMORY_FEAT_DIM = 10
