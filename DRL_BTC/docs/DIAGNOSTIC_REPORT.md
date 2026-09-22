# DRL BTC Agent — Full Diagnostic Report for External Review

> Generated: 2026-07-14
> Purpose: Complete system state for independent assessment
> Author context: This is a BTC futures DRL trading agent using SAC.
>   The core symptom is that the agent produces consistent validation results
>   that oscillate between two fixed states (~+0.70 and ~-2.80 Sharpe) regardless
>   of training progress, and training episodes never produce positive returns.

---

## 1. The Problem Statement

### Observed Symptoms

**Symptom A — Training episodes always negative, never improving:**
```
EP  1   bars=8,682    ret= -9.9%   L/S/F=28/19/53%  logπ=-3.4  Qc=0.006
EP  2   bars=12,740   ret=-16.8%   L/S/F=28/18/54%  logπ=-3.4  Qc=0.006
EP  3   bars=20,070   ret=-23.1%   L/S/F=26/19/55%  logπ=-3.4  Qc=0.005
EP  4   bars=20,270   ret=-27.7%   L/S/F=26/19/55%  logπ=-3.4  Qc=0.006
EP  5   bars=5,805    ret= -8.7%   L/S/F=29/19/52%  logπ=-3.4  Qc=0.006
```

`logπ = -3.4` is IDENTICAL across all episodes. The actor policy is not changing.
`Qc = 0.005–0.006` is tiny and not decreasing. Q-function barely updating.

**Symptom B — Validation Sharpe oscillates between two fixed states:**
```
Step 10K:  ret=+4.22%   Sharpe=+0.71  maxDD=4.5%   L/S/F=15/26/60%
Step 20K:  ret=+4.53%   Sharpe=+0.69  maxDD=4.7%   L/S/F=15/26/60%
Step 30K:  ret=-18.16%  Sharpe=-2.81  maxDD=18.4%  L/S/F=15/26/60%
Step 40K:  ret=-17.96%  Sharpe=-2.80  maxDD=18.2%  L/S/F=15/26/60%
Step 50K:  ret=+4.42%   Sharpe=+0.69  maxDD=4.5%   L/S/F=15/26/60%
Step 60K:  ret=-17.86%  Sharpe=-2.80  maxDD=18.1%  L/S/F=15/26/60%
Step 70K:  ret=-17.65%  Sharpe=-2.79  maxDD=17.9%  L/S/F=15/26/60%
```

- L/S/F (Long/Short/Flat %) = **IDENTICAL** at every val step regardless of Sharpe state
- Only maxDD changes (4.5% in good state vs 18% in bad state)
- Period of oscillation: ~20,000 steps
- This is Session 6 — BC Exit Pretraining was supposed to fix this. It did not.

**Symptom C — The same oscillation existed in Session 5:**
```
Session 5 (different action space, same direction rule):
Step 10K:  Sharpe=+0.95  L/S/F=15/26/60%
Step 20K:  Sharpe=-2.51  L/S/F=15/26/60%
Step 30K:  Sharpe=+0.95  L/S/F=15/26/60%
Step 90K:  Sharpe=-2.51  L/S/F=15/26/60%
```

The oscillation survived a complete architecture change (Session 6).
This strongly suggests the oscillation is structural, not a hyperparameter issue.

---

## 2. Full System Architecture

### 2.1 Data

```
Asset:      BTC/USDT Binance futures, 1h bars
Train:      2021-01-01 → 2024-12-31  (35,035 bars)
Val:        2022-01-01 → 2022-12-31  (8,737 bars) — BTC -66% bear year
OOS:        2025-01-01 → present     (never touched)

Timeframes: 1h (base), 4h (context), 1d (macro)
Total features: 209 (after multi-TF indicators + composite signals)
```

### 2.2 Feature Engineering (209 features)

```
Per-TF groups (×3 timeframes):
  Trend      (~18 features): EMA crosses, Supertrend, ADX, PSAR, Ichimoku, HMA
  Momentum   (~19 features): RSI, MACD, KDJ, WaveTrend, MFI, CCI, Stochastic, TSI
  Volatility  (~7 features): ATR%, Bollinger, Squeeze, HistVol, Choppiness
  Volume      (~7 features): Volume z-score, Taker ratio, VWAP-z, CVD-z, OBV
  Structure  (~10 features): Price z-score, FVG, Imbalance, Swing pivots, Order block

Auxiliary (no TF suffix):
  Funding rate (6 features): raw, z20, mom8h, ma24, cumsum8h, vol20
  Order book   (8 features): imbalance at 1/3/5%, bid/ask z-score, bid/ask slope

Composite signals (4 features, rule-derived):
  macro_score  = 0.50×ema_cross + 0.35×st_align + 0.15×(−funding_raw)
  swing_score  = 0.35×macd_hist_4h + 0.30×(rsi14_4h−0.5)×2 + 0.25×aroon_diff_4h + 0.10×(kdj_j_4h−0.5)×2
  entry_score  = 0.35×ob_ba_ratio + 0.30×taker_ratio_z + 0.25×cvd_z + 0.10×rsi14_slope
  regime_score = (0.35×anti_chop + 0.45×adx_4h + 0.20×vol_ok)×2 − 1
```

### 2.3 Network Architecture

```
Input: (batch, 48, 217)   [48-bar sequence × (209 market + 8 portfolio)]

PerspectiveEncoder:
  Phase 1 — Semantic projection per indicator group:
    trend(54→32), momentum(57→32), volatility(21→16), volume(21→16),
    structure(30→16), funding(6→8), orderbook(8→8), portfolio(8→8), signal(4→8)
  Phase 2 — Cross-group Multi-Head Attention (4 heads, d=32)
    9 group tokens × 32 dim → 9×32=288 dim
  Phase 3 — LSTM(input=288, hidden=256, layers=2, dropout=0.1)
    Takes last hidden state → FC(256)→ReLU→LayerNorm → z(256)

Actor:
  z(256) → FC(256)→ReLU → FC(128)→ReLU
         → mean_head(128→5) + log_std_head(128→5)
  log_std clamped to [-3, 0]   →  σ ∈ [0.05, 1.0]
  Output: tanh(mean + std×ε),   ε ~ N(0,1)
  Deterministic: tanh(mean)

Twin Critics (Q1, Q2):
  Each has its own independent PerspectiveEncoder
  z_i concat action → FC(256)→ReLU→FC(128)→ReLU→FC(1)
  Returns min(Q1, Q2)

Parameter count: ~8M total
```

### 2.4 Observation Space

```
Shape: (48, 217)  — 48-bar sliding window

Per bar:
  [0:209]   — 209 market features (all normalised to [-1,1])
  [209:217] — 8 portfolio state features tiled across all 48 bars:
    [0] position       -1/0/+1
    [1] pos_size       fraction of equity in trade (0 if flat)
    [2] sl_dist        (cur_px - sl_price) / cur_px × direction  [positive=above SL]
    [3] hold_bars/48   capped at 1.0
    [4] equity_log     log10(equity) - log10(100000)
    [5] neg_dd         negative drawdown (0 to -1)
    [6] unrealised_pnl clipped ±1
    [7] is_holding     binary
```

### 2.5 Action Space — Session 6

```
5D continuous Box[-1, 1]

action[0] → pos_size    = 0.05 + 0.20 × (a + 1.0) / 2.0     range: [5%, 25%]
action[1] → sl_atr_mult = 0.5  + 2.5  × (a + 1.0) / 2.0     range: [0.5×, 3.0×ATR]
action[2] → tp_atr_mult = 1.0  + 5.0  × (a + 1.0) / 2.0     range: [1.0×, 6.0×ATR]
action[3] → trail_on    = sigmoid(a × 3) > 0.5                binary
action[4] → exit_signal = sigmoid(a × 3) > 0.5                binary

IMPORTANT: Direction (long/short/flat) is NOT an action.
It is computed from composite signals at every step:
  combined = 0.65 × macro_score + 0.35 × swing_score
  if   combined > +0.10 AND regime_score > 0.0: → LONG
  elif combined < -0.10 AND regime_score > 0.0: → SHORT
  else:                                         → FLAT (60% of bars)

The direction rule produces the fixed L/S/F=15/26/60% observed in every val.
```

### 2.6 Trade Mechanics

```
Entry:
  - Triggered when: currently flat AND direction rule fires
  - pos_size, sl_atr_mult, tp_atr_mult, trail_on decoded from actor output at entry bar
  - sl_price = entry_px × (1 − direction × sl_atr_mult × atr_frac)
  - tp_price = entry_px × (1 + direction × tp_atr_mult × atr_frac)
  - atr_frac = atr_pct_1h_feature × 0.10   (real ATR as % of price; typical ~0.7%)
  - Entry fee = 0.04% × pos_size

Holding:
  - If trail_on: sl_price moves with favorable price each bar
  - Funding = 0.01% per 8h × pos_size

Exit conditions (ANY triggers close):
  1. exit_signal = True   (actor action[4])
  2. SL hit               (price crosses sl_price)
  3. TP hit               (price crosses tp_price)
  4. direction_changed    (composite rule changes — new_dir=0 or opposite)
  5. hold_bars ≥ 96       (4-day timeout)

Kill switch: if drawdown from equity peak ≥ 50% → force close + episode ends
Leverage: FIXED at 1.0× (no leverage used)
```

### 2.7 Reward Function

```
Per-bar rewards:
  + bar_pnl        = (next_px/cur_px - 1) × direction × pos_size   [main signal]
  − entry_fee      = 0.04% × pos_size        [at entry bar]
  − exit_fee       = 0.04% × pos_size        [at exit bar]
  − funding        = ~0.00004% × pos_size    [every holding bar]
  − dd_penalty     = current_dd × 3.0 × 0.1  [when DD > 5%]
  − chop_penalty   = 0.02                    [at entry if choppiness_1h > 0.7]
  + trend_bonus    = +0.0015/bar             [when position matches macro direction, regime>0.2]
  − counter_penalty= -0.001/bar              [when position opposes macro direction]

Episode terminal:
  − liq_penalty    = -1.0                    [if DD hits 50%]

NO flat penalty — direction is rule-based, flat is legitimate.
REWARD_SCALE = 1.0 (no scaling).
```

### 2.8 SAC Configuration

```python
BUFFER_SIZE    = 300_000     # ring buffer
BATCH_SIZE     = 512
LR_ACTOR       = 3e-4
LR_CRITIC      = 3e-4
LR_ALPHA       = 0.0         # FROZEN — alpha does not update
ALPHA_FIXED    = 0.3         # constant entropy temperature
GAMMA          = 0.99
TAU            = 0.005       # soft target update
TARGET_ENTROPY = -5/2 = -2.5 # = -ACTION_DIM/2
GRAD_CLIP      = 1.0
UPDATE_EVERY   = 16          # 1 gradient step per 16 env steps
G_STEPS        = 1
WARMUP_STEPS   = 20_000      # random actions before learning
TOTAL_STEPS    = 500_000
```

### 2.9 Replay Buffer

```
Type: Prioritized Experience Replay (PER), Schaul 2015
  α = 0.6  (priority exponent)
  β = 0.4 → 1.0 over 500K steps (IS weight annealing)
  ε = 1e-6
  new transitions start at max_priority → sampled at least once

Stores: per-bar transitions (obs, action, reward, next_obs, done)
  NOT trade-level — every 1h bar is one transition.
  60% of stored transitions are from FLAT bars with near-zero reward.
```

### 2.10 Training Stages — Session 6

```
Stage 1: BC Exit Pretraining (~5 min)
  - Oracle simulation: composite rule entries → ATR-based SL/TP → exit labels
  - 16,116 labeled in-position bars (exit rate=11.4%)
  - Actor supervised: MSE on pos_size/sl_atr/tp_atr + BCE on trail/exit
  - 30 epochs, exit_acc: 42% → 87.58%
  - Rationale: eliminate cold-start Q-cycling oscillation from Session 5
  - Result: oscillation PERSISTS despite BC pretraining

Stage 2: Random Warmup (20,000 steps)
  - action_space.sample() — uniform random
  - Fills buffer with 20K transitions before any gradient step

Stage 3: SAC Learning (0 → 500K steps)
  - Every step: act → store → advance
  - Every 16 steps: 1 gradient update (critic → actor → soft-target)
  - Val every 10K, checkpoint every 50K
```

---

## 3. Session History

### Session 1–4: Direction learning via BC + SAC
- Agent controlled direction (long/short/flat) via action[0]
- Multiple BC regularisation schemes, entropy tuning
- Core issue: SAC eroded BC direction bias, agent often went flat or random

### Session 5: Rule-based direction, hold_exit only active
- Direction moved to composite signal rule (removed from actor)
- Actor still 5D but only action[4] (hold_exit) had real effect
- **New oscillation found**: val Sharpe flipped ±0.95/−2.51 every 20K steps
- Same L/S/F in both states → direction not the cause
- Root cause: exit_signal Q-cycling between "never exit" and "always exit" attractors

### Session 6: BC Exit Pretraining + 5D risk action space
- Repurposed all 5 dims: [pos_size, sl_atr_mult, tp_atr_mult, trail_on, exit_signal]
- Dynamic SL/TP set at entry from actor output
- BC Exit Pretraining: oracle exit labels, 30 epochs
- **Result: oscillation unchanged** (+0.69/−2.80, period ~20K steps)
- BC pretraining overridden by SAC within 10–30K steps
- logπ = -3.4 constant throughout → actor not learning

---

## 4. Diagnostic Data

### 4.1 Training Log (Session 6, full)

```
STAGE 1: BC Exit Pretraining
epoch   1/30  loss=2.9189  exit_acc=42.18%
epoch   5/30  loss=2.4757  exit_acc=62.65%
epoch  10/30  loss=2.1919  exit_acc=68.06%
epoch  15/30  loss=1.8566  exit_acc=72.60%
epoch  20/30  loss=1.4632  exit_acc=79.14%
epoch  25/30  loss=1.2205  exit_acc=83.81%
epoch  30/30  loss=1.0222  exit_acc=87.58%

STAGE 2: WARMUP (20,000 random steps, buffer fills to 20,000)

STAGE 3: LEARNING
EP  1  bars=8,682   ret= -9.9%  completed  L/S/F=28/19/53%  α=0.300  logπ=-3.4  Qc=0.006  sps=36
VAL@10K  ret=+4.22%  Sharpe=+0.71  maxDD=4.5%  L/S/F=15/26/60%  ★BEST
EP  2  bars=12,740  ret=-16.8%  completed  L/S/F=28/18/54%  α=0.300  logπ=-3.4  Qc=0.006  sps=32
VAL@20K  ret=+4.53%  Sharpe=+0.69  maxDD=4.7%  L/S/F=15/26/60%  ★BEST
EP  3  bars=20,070  ret=-23.1%  completed  L/S/F=26/19/55%  α=0.300  logπ=-3.4  Qc=0.005  sps=32
VAL@30K  ret=-18.16% Sharpe=-2.81  maxDD=18.4% L/S/F=15/26/60%
VAL@40K  ret=-17.96% Sharpe=-2.80  maxDD=18.2% L/S/F=15/26/60%
EP  4  bars=20,270  ret=-27.7%  completed  L/S/F=26/19/55%  α=0.300  logπ=-3.4  Qc=0.006  sps=32
EP  5  bars=5,805   ret= -8.7%  completed  L/S/F=29/19/52%  α=0.300  logπ=-3.4  Qc=0.006  sps=32
VAL@50K  ret=+4.42%  Sharpe=+0.69  maxDD=4.5%  L/S/F=15/26/60%
VAL@60K  ret=-17.86% Sharpe=-2.80  maxDD=18.1% L/S/F=15/26/60%
VAL@70K  ret=-17.65% Sharpe=-2.79  maxDD=17.9% L/S/F=15/26/60%
```

### 4.2 Key Metrics That Never Change

| Metric | Value | Implication |
|--------|-------|-------------|
| `logπ` | -3.4 always | Actor distribution frozen |
| `α` | 0.300 always | By design (LR_ALPHA=0) |
| `Qc` | 0.005–0.006 | Q-loss not decreasing |
| L/S/F (val) | 15/26/60% | Direction rule deterministic |
| L/S/F (train) | 26–29/18–19/52–55% | Direction rule consistent |
| sps | 32–36 | Training speed stable |

### 4.3 What the Two Val States Look Like

| Metric | "Good" state | "Bad" state |
|--------|-------------|------------|
| Return | +4.22% to +4.53% | -17.65% to -18.16% |
| Sharpe | +0.69 to +0.71 | -2.79 to -2.81 |
| maxDD | 4.5–4.7% | 17.9–18.4% |
| L/S/F | 15/26/60% | 15/26/60% |
| Period | 10K–20K steps | 30K–40K, 60K–70K steps |

The ONLY difference between good and bad state is maxDD (+4.5% vs 18%).
Direction is identical. The Sharpe difference is therefore entirely about
HOW trades are managed (exit timing / hold duration), not WHICH direction.

---

## 5. Code: Key Components

### 5.1 Direction Rule (btc_env.py)

```python
# Rule-based direction from composite signal
if self._macro_idx is not None and self._regime_idx is not None:
    macro  = float(self._features.iloc[cur_idx, self._macro_idx])
    regime = float(self._features.iloc[cur_idx, self._regime_idx])
    if self._swing_idx is not None:
        swing    = float(self._features.iloc[cur_idx, self._swing_idx])
        combined = 0.65 * macro + 0.35 * swing
    else:
        combined = macro
    if   combined >  ENTRY_THRESHOLD and regime > 0.0: new_dir =  1.0   # LONG
    elif combined < -ENTRY_THRESHOLD and regime > 0.0: new_dir = -1.0   # SHORT
    # else: flat (60% of bars)
```

### 5.2 Action Decoding (btc_env.py)

```python
# All 5 action dims decoded every step
pos_size_act = float(POS_SIZE_MIN    + (POS_SIZE_MAX    - POS_SIZE_MIN)    * (action[0] + 1.0) / 2.0)
sl_atr_act   = float(SL_ATR_MULT_MIN + (SL_ATR_MULT_MAX - SL_ATR_MULT_MIN) * (action[1] + 1.0) / 2.0)
tp_atr_act   = float(TP_ATR_MULT_MIN + (TP_ATR_MULT_MAX - TP_ATR_MULT_MIN) * (action[2] + 1.0) / 2.0)
trail_on_act = _sigmoid(action[3] * 3) > 0.5
exit_signal  = _sigmoid(action[4] * 3) > 0.5
```

### 5.3 Exit Logic (btc_env.py)

```python
# When in position:
sl_hit  = (cur_px <= self._sl_price) if self._position > 0 else (cur_px >= self._sl_price)
tp_hit  = (self._tp_price > 0) and (
    (cur_px >= self._tp_price) if self._position > 0 else (cur_px <= self._tp_price)
)
direction_changed = (new_dir == 0.0) or (new_dir != 0.0 and new_dir != self._position)

if exit_signal or sl_hit or tp_hit or direction_changed or self._hold_bars >= 96:
    step_reward += self._close_position(cur_px)
    position_changed = True
```

### 5.4 SAC Actor Update (sac_agent.py)

```python
# Actor update — all 5 dims trained, no detach
new_acts, log_pi, _ = self.actor(obs)
q1_pi, q2_pi = self.critic(obs, new_acts)
q_pi       = torch.min(q1_pi, q2_pi)
actor_loss = (self.alpha.detach() * log_pi.float() - q_pi.float()).mean()
# alpha = 0.3 fixed
# actor tries to maximise Q while maintaining entropy
```

### 5.5 Replay Buffer Structure

```python
# PER buffer, per-BAR transitions (not per-trade)
# Every 1h bar produces one (obs, action, reward, next_obs, done) tuple
# Buffer capacity: 300,000 transitions
# With ~40% active bars (trading): ~120K active, ~180K flat transitions
# Flat bars have reward ≈ 0 → TD error ≈ 0 → LOW priority in PER → deprioritised
# BUT: buffer still initialised with 20K random transitions before BC policy runs
```

### 5.6 BC Exit Pretraining (bc_exit_pretrain.py)

```python
# Oracle exit labels
sl_hit  = pnl_pct < -BC_SL_ATR_DEFAULT * entry_atr       # 1.5×ATR
tp_hit  = pnl_pct >  BC_TP_ATR_DEFAULT * entry_atr       # 3.0×ATR
dir_rev = (new_dir == 0.0) or (new_dir != 0.0 and new_dir != position)
timeout = hold_bars >= 72
exit_lbl = float(sl_hit or tp_hit or dir_rev or timeout)

# Loss
pos_size_pred = POS_SIZE_MIN + (POS_SIZE_MAX - POS_SIZE_MIN) * (mean_tanh[:, 0] + 1.0) / 2.0
sl_atr_pred   = SL_ATR_MULT_MIN + (SL_ATR_MULT_MAX - SL_ATR_MULT_MIN) * (mean_tanh[:, 1] + 1.0) / 2.0
tp_atr_pred   = TP_ATR_MULT_MIN + (TP_ATR_MULT_MAX - TP_ATR_MULT_MIN) * (mean_tanh[:, 2] + 1.0) / 2.0
trail_logit   = mean_tanh[:, 3] * 3.0
exit_logit    = mean_tanh[:, 4] * 3.0

loss = F.mse_loss(pos_size_pred, tgt[:,0]) + F.mse_loss(sl_atr_pred, tgt[:,1]) +
       F.mse_loss(tp_atr_pred, tgt[:,2]) +
       F.binary_cross_entropy_with_logits(trail_logit, tgt[:,3]) +
       F.binary_cross_entropy_with_logits(exit_logit, tgt[:,4], pos_weight=exit_pw) * 2.0

# After 30 epochs: exit_acc = 87.58%, loss = 1.02
# actor_mod.train() called at end (critical: LSTM must be in train mode for SAC backward)
```

---

## 6. Our Hypotheses

Listed in order of our current confidence:

### H1 (HIGH): exit_signal creates a bistable Q-function
The exit_signal (action[4]) is a binary decision (0 or 1 after sigmoid).
The Q-function naturally discovers two stable policies:
- "exit quickly" → avoid SL hits → low but stable returns
- "hold" → let trades run → high wins but high risk
Both are Nash equilibria for SAC. With only 1 gradient step per 16 env steps (UTD=0.0625),
SAC alternates between these attractors with ~20K step period.
BC pretraining seeds "sometimes exit" but SAC overrides within 10-20K updates.

### H2 (HIGH): Actor is frozen, not learning
logπ = -3.4 is constant at every episode for 70K+ steps.
SAC actor update: `loss = α × logπ - Q = 0.3 × (-3.4) - Q_small ≈ -1.02 - Q`
If Q-values are near zero, gradient is: `∂loss/∂θ ≈ 0.3 × ∂logπ/∂θ`
The entropy gradient alone pushes logπ toward TARGET_ENTROPY = -2.5.
But logπ = -3.4 < -2.5 already — the policy IS more deterministic than target entropy.
With α frozen and logπ already below target, the actor has no clear gradient signal.

### H3 (HIGH): Q-function learning from poisoned buffer
Replay buffer composition:
- 20K warmup transitions (random actions) — these stay in buffer for first ~300K steps
- ~60% flat bars per episode → near-zero reward transitions
- In FLAT states: reward=0, done=0 → Q-target = GAMMA × min(Q1,Q2) - α×logπ ≈ 0.3×3.4 ≈ -1
- This creates a gradient pushing Q of all states toward -1.0
- Qc = 0.005 means Q predictions are already near targets (near -1.0 for flat states)
- The Q-function "learned" that doing anything near a flat state gives Q ≈ -1

### H4 (MEDIUM): Training episodes are structurally difficult
- Episode start index: random in [48, 34035]
- Episodes crossing 2022 (BTC -66%) will lose on long positions
- Direction rule produces 15% LONG exposure even in bear market
- Average episode length ~18,000 bars = 2 years of data per episode
- Only ~4-5 complete episodes in 70K steps → almost no episode-level learning signal

### H5 (MEDIUM): Per-bar transitions vs per-trade credit assignment
- Current buffer: every 1h bar = 1 transition
- A 20-bar trade generates 20 transitions
- The ENTRY bar creates: (obs_entry, action, -fee, obs_entry+1, False)
  → reward = -0.04% (tiny negative, just the fee)
  → Q-target ≈ 0.99 × Q(next) − 1.02 ≈ -1.03
  → Q(entry) → -1.03 (entry looks bad)
- This is the "perfect entry looks bad" problem: the reward of a good entry
  only materialises 5-20 bars later when the trade closes with profit.
  SAC's 1-step TD cannot see that far forward.

### H6 (LOW-MEDIUM): PER oversample catastrophic transitions
- PER priority = |TD error|
- Large TD errors occur at: liquidations (reward=-1), SL hits, TP hits
- Most of these are loss events
- If loss events have high TD error → they're oversampled
- This could teach the critic "unusual situations are dangerous"
  rather than "these are the informative transitions"
- Beta annealing from 0.4 → 1.0 partially corrects this but slowly

---

## 7. What We Have NOT Tried

| Idea | Reason not tried |
|------|-----------------|
| Remove exit_signal entirely | Our first hypothesis — not implemented yet |
| N-step returns (n=5–10) | Would require replay buffer rewrite |
| Trade-level replay (not bar-level) | Major architecture change |
| Fixed SL/TP (no SAC for exits) | Simpler baseline, not tested |
| 1D SAC (pos_size only) | Not tested |
| PPO instead of SAC | Different RL family |
| Reduce exploration noise (lower alpha) | Currently fixed at 0.3 |
| Warmup with BC policy (not random) | Currently warmup = random actions |
| Higher UTD ratio (more gradient steps per env step) | Currently UTD=0.0625 |
| Shorter episodes (cap at 5000 bars) | Currently uncapped |

---

## 8. The Questions We Want Answered

1. **Is the actor truly frozen?**
   If logπ is constant, is it because (a) the gradient is near zero, (b) the gradient
   cancels out, or (c) GRAD_CLIP is clipping everything? How to diagnose?

2. **Is the Q-function meaningful?**
   If Qc=0.005 and Q-values are all near -1.0, the critic has converged to "everything
   is bad." How do we bootstrap useful Q-values from such a noisy, sparse reward signal?

3. **Is BC pretraining counterproductive?**
   BC pretraining puts the actor in a specific region. If SAC's Q-function is already
   "poisoned" (everything near -1), could BC pretraining actually PREVENT the actor
   from learning because it starts too far from the Q-function's "good" region?

4. **Should exit_signal exist at all?**
   The direction rule fires `direction_changed` exits naturally. SL/TP handle risk.
   Does exit_signal add value, or does it only add Q-cycling instability?

5. **What's the right credit assignment mechanism for this problem?**
   Per-bar TD is too myopic (can't see trade outcomes). What's the minimal change
   that gives the critic visibility into trade-level outcomes?

---

## 9. Raw Config Values

```python
# DRL_BTC/config.py (full)

TIMEFRAMES         = ["1h", "4h", "1d"]
BASE_TF            = "1h"
SEQ_LEN            = 48

TRAIN_END          = "2024-12-31"
VAL_START          = "2022-01-01"
VAL_END            = "2022-12-31"
TEST_START         = "2025-01-01"

INITIAL_CAPITAL    = 100_000.0
FEE_RATE           = 0.0004
FUNDING_PER_BAR    = 0.0001 / 8.0
MAX_LEVERAGE       = 2.0
MIN_LEVERAGE       = 1.0
MAX_POS_FRACTION   = 0.50
MIN_POS_FRACTION   = 0.05
CONFIDENCE_GATE    = 0.0        # disabled
DIR_THRESHOLD      = 0.02       # legacy, not used in env
ENTRY_THRESHOLD    = 0.10       # composite signal gate
FLAT_PENALTY       = 0.010      # in config but NOT applied in env
MAX_DRAWDOWN_KILL  = 0.50

LSTM_HIDDEN        = 256
LSTM_LAYERS        = 2
LSTM_DROPOUT       = 0.1
FC_HIDDEN          = 256
ACTION_DIM         = 5

BUFFER_SIZE        = 300_000
BATCH_SIZE         = 512
LR_ACTOR           = 3e-4
LR_CRITIC          = 3e-4
LR_ALPHA           = 0.0        # frozen
GAMMA              = 0.99
TAU                = 0.005
TARGET_ENTROPY     = -2.5       # = -ACTION_DIM/2
ALPHA_FIXED        = 0.3
GRAD_CLIP          = 1.0
UPDATE_EVERY       = 16
G_STEPS            = 1
WARMUP_STEPS       = 20_000
TOTAL_STEPS        = 500_000

REWARD_SCALE       = 1.0
DD_PENALTY_SCALE   = 3.0
CHOP_PENALTY       = 0.02

POS_SIZE_MIN       = 0.05
POS_SIZE_MAX       = 0.25
SL_ATR_MULT_MIN    = 0.5
SL_ATR_MULT_MAX    = 3.0
TP_ATR_MULT_MIN    = 1.0
TP_ATR_MULT_MAX    = 6.0
ATR_FEATURE        = "atr_pct_1h"
ATR_SCALE          = 0.10

BC_PRETRAIN_EPOCHS = 30
BC_PRETRAIN_LR     = 3e-4
BC_PRETRAIN_BATCH  = 256
BC_SL_ATR_DEFAULT  = 1.5
BC_TP_ATR_DEFAULT  = 3.0
```

---

## 10. Session 5 vs Session 6 Comparison

| Aspect | Session 5 | Session 6 |
|--------|-----------|-----------|
| Action dims | dir, conf, size, lev, hold_exit | pos_size, sl_atr, tp_atr, trail_on, exit_signal |
| Active dims | ~1 (hold_exit only) | 5 (all new) |
| Direction | Rule-based | Rule-based (unchanged) |
| SL/TP | Fixed 1.5×ATR / 3.0×ATR | Dynamic from actor |
| BC Pretraining | None for exits | 30 epochs, exit_acc=87.58% |
| Warmup | 20K random | 20K random |
| PER | Yes | Yes |
| Val oscillation | ±0.95 / −2.51 | ±0.69 / −2.80 |
| Oscillation period | ~20K steps | ~20K steps |
| Actor frozen (logπ) | Not recorded | Yes (-3.4 constant) |
| Training eps positive? | No | No |

The oscillation period and pattern are **structurally identical** across two different
action spaces. This is strong evidence the problem is NOT the action space design —
it is something more fundamental in the learning dynamics.

---

## 11. Environment Episode Structure

```python
# btc_env.py reset():
if self._mode == "train":
    max_start = self._len - 1000          # = 34,035
    self._step_idx = self.np_random.integers(SEQ_LEN, max(SEQ_LEN + 1, max_start))
    # start anywhere in [48, 34035)

# step():
terminated = self._step_idx >= self._len - 1   # episode ends when data runs out
truncated  = current_dd >= MAX_DRAWDOWN_KILL   # or 50% DD kill

# Consequences:
# - Average episode length: ~18,000 bars (~2 years)
# - Min episode: 1,000 bars
# - Max episode: 34,986 bars
# - In 70K training steps: only 5 complete episodes
# - Rolling 20-episode stats cover 5 actual episodes → meaningless
```

---

## 12. Summary of Things That Are Correct

(To help narrow the diagnosis — these parts are working as intended)

1. Direction rule fires correctly: 15% LONG / 26% SHORT / 60% FLAT (consistent with composite signal logic)
2. BC pretraining converges well: exit_acc 42% → 87.58% in 30 epochs
3. Training runs without crashes after actor_mod.train() fix
4. PER buffer implementation is correct (SumTree verified)
5. Val rollout is deterministic (tanh(mean), no noise)
6. 2022 val window is appropriate (bear year tests SHORT ability)
7. ATR normalization is correct (atr_pct × 0.10 = real ATR fraction)
8. SL/TP decoding is correct (entry_px × (1 ± mult × atr_frac))
9. LSTM backward works in training mode (fixed from Session 6 crash)
10. Reward structure has sensible magnitudes (bar_pnl ~ 0.001–0.003 per bar)
