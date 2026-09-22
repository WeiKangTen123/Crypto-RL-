# DRL_BTC — OOS Failure Diagnosis & Enhancement Roadmap

> Created: 2026-07-15  
> Context: Session 7 (best_s42) achieved val Sharpe +0.73 (+4.82%) but OOS returned -6.81% Sharpe -0.99.  
> Session 8: retraining with larger model (LSTM 512, batch 512, G_STEPS 10) — currently running on server.  
> Session 9 / TIA v2: full architectural response to OOS failure — built locally, ready for next training run.

---

## 1. The Core Problem

### Val vs OOS Gap

| Window | Period | Return | Sharpe | MDD | L/S/F | Notes |
|--------|--------|--------|--------|-----|-------|-------|
| Val (early stop) | 2022-01-01 → 2022-12-31 | +4.82% | +0.73 | 4.5% | 15/26/60% | BTC −66% bear year |
| OOS (never seen) | 2025-01-01 → 2026-07-15 | −6.81% | −0.99 | 8.89% | 19/24/57% | BTC mostly bullish |

The model appeared to learn, then failed completely on unseen data.  
Flat 57% of OOS bars — the rule-based entry filter rarely fires with confidence.

---

## 2. Root Cause Diagnosis (Ranked by Confidence)

### D1 — Val window is a single market regime (HIGH CONFIDENCE)

The val window is **one full year of extreme bear market** (BTC −66%, 2022).  
The model's early-stopping criterion is: "be the best at surviving 2022."

**What the model learned to do on 2022:**
- SHORT aggressively when macro_score < 0 (EMA downtrends, Supertrend bearish, high funding rate)
- Tight SL on longs (don't let a long run in a bear market)
- Stay flat when signals are mixed

**Why this fails on 2025-2026 (mostly bull):**
- 2025 BTC: Jan +50%, then range, then bull continuation
- macro_score is POSITIVE most of the time → agent's "short bias" from 2022 training causes it to miss longs or go flat
- The composite direction rule fires longs (19% of OOS bars) but the agent's risk params (tight SLs) stop them out quickly
- TP rate on OOS = ~0% (all exits via SL or direction change, never via TP hit)

**Fix:** Use a multi-period or rolling validation window that includes both bear and bull regimes.  
Candidate: alternate between 2022 (bear) + 2023 (recovery) + 2024 Q4 (bull) for val.

---

### D2 — Direction rule is frozen and may not generalize (HIGH CONFIDENCE)

The direction comes from a **hard-coded composite signal rule**, not from the neural network:
```
combined = 0.65 × macro_score + 0.35 × swing_score
LONG  if combined > 0.10 AND regime_score > 0
SHORT if combined < −0.10 AND regime_score > 0
FLAT  otherwise (~57–60% of bars)
```

This rule was calibrated during feature engineering on 2021-2024 data.  
The RL agent **cannot override this rule** — it can only change position sizing.

**Problem:** If the composite signal fires wrong on OOS data, no amount of RL training can fix it.  
The agent's only tool is "don't trade large when uncertain" — but it still trades in the indicated direction.

**Evidence:** On OOS, L/S/F = 19/24/57%. The SHORT bias (24% vs 19% LONG) persists even in a bull market — the agent is being told to SHORT by the direction rule, sets tight SLs, and loses consistently.

**Fix options:**
1. Let the actor output a direction confidence multiplier that can reduce or skip the rule-based trade
2. Add direction accuracy to the reward (penalize when rule-based direction was wrong)  
3. Reduce ENTRY_THRESHOLD from 0.10 to something regime-adaptive (higher in chop, lower in strong trend)
4. Use the BetaHead (from Session 8 architecture) to override direction based on learned regime classification

---

### D3 — Training optimizes for the wrong objective (HIGH CONFIDENCE)

**Current reward function:**
```
bar_reward = unrealised_PnL_this_bar + trend_bonus − fees − dd_penalty − chop_penalty
```

This is a **bar-level PnL** reward. The agent learns to maximize total bars of positive PnL.

**What it actually encourages:**
- Stay in a trade while it's going up bar by bar (even if it's going to SL eventually)
- Exit quickly when a bar is negative (even if the trade was going to recover)
- Never hits TP because: TP fires late in a trend when momentum slows → last few bars before TP are flat/slightly negative → agent prefers to exit earlier via SL or direction change

**Evidence:** tp_rate ≈ 1% on val, ≈ 0% on OOS. The agent almost never lets a trade run to TP.

**Fix:** Reward should be based on **completed trade outcome**, not per-bar PnL.  
Session 7's trade-level replay partially addresses this (buffer stores trade-level transitions), but the environment still gives per-bar rewards during the episode.  
True fix: give reward = 0 during trade, then reward = total_trade_pnl only at close.

---

### D4 — Position size is too small to overcome fees (MEDIUM CONFIDENCE)

Max pos_size = 25% of equity. With 1.0× leverage, each trade risks:
```
Fee cost = 0.04% × 2 (entry + exit) = 0.08% per round trip
Min win to break even = 0.08% / 0.25 = 0.32% price move
```

Average 1h ATR for BTC ≈ 0.73% → most trades need 0.44% price move to profit.  
With avg_hold = 7-8 bars, the agent only captures small moves and gets fee-eroded.

**Fix:** Increase max_pos_size to 40-50% OR reduce fees by only entering on higher-conviction setups.

---

### D5 — 2022 bear year was artificially easy to SHORT (MEDIUM CONFIDENCE)

BTC fell 66% in 2022. The SHORT direction produced reliable positive PnL.  
The composite signals (EMA bearish, Supertrend bearish, RSI low) were consistently aligned SHORT.  
The agent's BC pretrain produced good SL/TP defaults.

This was an **easy regime** for a SHORT-biased strategy. The model converged to "be a reliable short-seller in bear markets" which is not a generalizable skill.

**Fix:** Include 2021 (bull) and 2023 (recovery) in the val window. Make early stopping reward performance across multiple regimes.

---

### D6 — No explicit anti-overfitting mechanism (MEDIUM CONFIDENCE)

The RL training runs for 500K-600K steps on 35,035 bars.  
That's ~14× coverage of the training data per training run (with random starts).  
There's no dropout annealing, weight decay, or early-stopping on OOS.

The model can memorize which specific bars in training produce good PnL and overfit the risk parameters to those bars.

**Fix:** Add L2 weight decay (1e-4), increase LSTM dropout (0.2), reduce TOTAL_STEPS.

---

## 3. Proposed Enhancements (Prioritized)

### Priority 1 — Fix the Validation Window (CRITICAL, LOW EFFORT)

**Change:** Replace single-year 2022 val with a 3-period rolling val:
```python
# New val candidates (rotate through or average):
VAL_PERIOD_1 = "2022-01-01" → "2022-12-31"   # bear year (current)
VAL_PERIOD_2 = "2023-07-01" → "2023-12-31"   # recovery/bull
VAL_PERIOD_3 = "2024-01-01" → "2024-06-30"   # consolidation / mini-bear
```

**Early-stopping criterion:** Average Sharpe across all 3 periods (or worst-of-3 if you want robustness).  
This forces the model to work across regimes, not just 2022.

**Impact:** Prevents bear-regime overfitting. Highest impact change possible.

---

### Priority 2 — End-of-Trade Reward (HIGH IMPACT, MEDIUM EFFORT)

**Change:** Remove per-bar PnL reward. Give reward only when trade closes.

```python
# Current (per-bar):
reward = bar_pnl + trend_bonus − fees

# Proposed (trade-close only):
if trade_just_closed:
    reward = total_trade_pnl − total_fees − total_funding
    reward = reward × pos_size   # scale by position fraction
else:
    reward = 0.0  # (minus small funding cost only)
```

This forces Q(entry_state, entry_action) to estimate the full trade outcome.  
Trade-level replay already stores entry→exit transitions, so the buffer structure is compatible.

**Impact:** Agent learns to distinguish "good entry with bad early bars" from "genuinely bad trade."  
TP rate should increase from ~1% to something meaningful.

---

### Priority 3 — Direction Override via Confidence Multiplier (HIGH IMPACT, MEDIUM EFFORT)

Allow the actor to **reduce position size to near-zero** when it disagrees with the direction signal:

```python
# Modified action decoding:
# action[0] = pos_size (5% to 25%)  -- UNCHANGED
# NEW: allow pos_size → 0 by gating:
#   pos_size_final = pos_size × F.softplus(confidence_logit)  where confidence_logit from actor
# If actor outputs low confidence → position shrinks to near-zero → effective SKIP

# OR simpler: expand pos_size range to include 0:
POS_SIZE_MIN = 0.00   # allow full skip
POS_SIZE_MAX = 0.30
```

This gives the agent a "soft veto" on the direction signal without breaking the rule-based direction architecture. When the actor is uncertain about OOS data, it can output pos_size ≈ 0 and avoid trading.

**Impact:** Directly addresses the "57% flat but trades go wrong" problem — agent can choose to stay flat more often than the direction rule dictates.

---

### Priority 4 — Sharpe-Optimizing Reward (HIGH IMPACT, HIGH EFFORT)

Replace raw PnL reward with a Sharpe-aware formulation:

```python
# Rolling reward normalization:
# Track last N trade returns as a window
# reward_normalized = (trade_pnl − mean(last_N)) / (std(last_N) + ε)

# Alternative — direct Sharpe approximation:
SHARPE_WINDOW = 50  # bars
rolling_ret  = deque of last 50 bar returns
rolling_mean = mean(rolling_ret)
rolling_std  = std(rolling_ret) + 1e-8
reward = (bar_pnl − rolling_mean) / rolling_std × REWARD_SCALE
```

This directly optimizes for the Sharpe ratio that we measure in validation.  
Current reward (raw PnL) ≠ what we measure (Sharpe). Alignment should improve OOS.

---

### Priority 5 — Adaptive Position Sizing by Regime (MEDIUM IMPACT, LOW EFFORT)

Apply a regime multiplier to pos_size:

```python
# In btc_env.py, modify pos_size decoding:
regime_mult = max(0.3, float(regime_score))   # 0.3× to 1.0×
pos_size_final = pos_size_base × regime_mult

# Effect: agent trades smaller in choppy market, larger in trending market
```

This is a simple change that reduces fee drag in low-conviction environments.

---

### Priority 6 — Add 2024 Q4 to Training Data (MEDIUM IMPACT, LOW EFFORT)

Currently TRAIN_END = "2024-12-31". The OOS starts 2025-01-01.  
The model saw 2024 during training but the val window (2022) didn't encourage it to learn 2024 patterns.

**Change:** Add a 2024 Q4 eval window (bull market regime) to the val set.  
This exposes the early-stopping to a more recent bull market regime.

---

### Priority 7 — Lower ENTRY_THRESHOLD in Strong Trends (LOW EFFORT)

Current: ENTRY_THRESHOLD = 0.10 (fires ~40% of bars during training)

In a strong bull trend, composite signals may consistently score 0.15-0.20 but the 0.10 threshold means the agent enters even on weak signals. Raising the threshold to 0.20 in choppy regimes would reduce noise trades:

```python
# In btc_env.py:
effective_threshold = ENTRY_THRESHOLD + max(0, 0.10 × (1 - regime_score))
# In chop (regime_score=0): effective = 0.10 + 0.10 = 0.20
# In trend (regime_score=1): effective = 0.10 + 0.00 = 0.10
```

---

### Priority 8 — N-Step Returns (MEDIUM IMPACT, MEDIUM EFFORT)

Current: 1-step TD targets (Q(s) ← r + γ × Q(s'))  
Proposed: N-step returns (n=4 or 8 hours)

```
G_t^n = r_t + γ r_{t+1} + ... + γ^{n-1} r_{t+n-1} + γ^n Q(s_{t+n})
```

N-step returns reduce the gap between entry reward (just fees) and trade outcome (actual PnL).  
Combined with trade-level replay, this could significantly improve credit assignment.

---

### Priority 9 — Weight Decay + Stronger Regularization

Add L2 regularization to prevent overfitting:

```python
actor_opt  = optim.Adam(actor.parameters(),  lr=LR_ACTOR,  weight_decay=1e-4)
critic_opt = optim.Adam(critic.parameters(), lr=LR_CRITIC, weight_decay=1e-4)
```

Also increase LSTM dropout from 0.1 to 0.2.

---

## 4. What Session 8 Changes (Currently Running)

Session 8 is running on the server with these improvements over Session 7:

| Change | Session 7 | Session 8 |
|--------|-----------|-----------|
| LSTM_HIDDEN | 256 | 512 |
| FC_HIDDEN | 256 | 512 |
| BATCH_SIZE | 64 | 512 |
| G_STEPS | 1 | 10 (UTD 80×) |
| WARMUP_TRADES | 300 | 500 |
| TOTAL_STEPS | 500K | 600K |
| SharedModel pretrain | No | Yes (BetaHead + AlphaHead) |

Session 8 does NOT yet implement Priorities 1-4 above. Those require architectural changes.

---

## 5. What Session 9 / TIA v2 Implements (Built 2026-07-15)

Session 9 is a full architectural response to the OOS failure diagnosis. Every high-confidence root cause has a direct fix:

| Priority | Issue | Fix Implemented | Notes |
|----------|-------|-----------------|-------|
| P1 ✅ | Single-regime val | **Multi-regime val (3 windows)** | 2022-bear + 2023-bull + 2024-consol |
| P1 ✅ | Wrong early-stop | **Min Sharpe across 3 regimes** | Robustness: must work in every regime |
| P3 ✅ | No trade skip | **POS_SIZE_MIN=0.00** | Actor can output pos_size≈0 to soft-veto |
| P3 ✅ | No gate over direction | **ConfidenceGate: EXECUTE/REDUCE/SKIP** | Replaces DecisionFusionHead; trained by RL only |
| P6 ✅ | Overfitting / no regularisation | **weight_decay=1e-4** on Actor + Critic Adam | L2 regularisation across all learned weights |
| NEW ✅ | No OOD awareness | **MarketDiagnostics** | EMA z-space detector; ood_score fed to ConfidenceGate |
| NEW ✅ | Shallow regime understanding | **BetaEngine: +regime_stability** | Knows whether regime will persist (next 12 bars) |
| NEW ✅ | Shallow return prediction | **AlphaEngine: quantile returns (p10/p50/p90), sl_prob, exp_vol** | Full return distribution + downside probability |

**What Session 9 does NOT yet change:**

| Priority | Remaining Gap | Reason deferred |
|----------|---------------|-----------------|
| P2 | End-of-trade reward | Still per-bar reward. TP rate improvement expected from ConfidenceGate + multi-regime val first. Address in Session 10 if TP rate remains ≈0%. |
| P4 | Sharpe-optimizing reward | Deferred. Try multi-regime val first; Sharpe reward adds complexity. |
| P8 | N-step returns | Not implemented. Trade-level replay already bridges credit assignment gap. |

---

## 6. Recommended Session 10 (if Session 9 OOS still fails)

If Session 9 OOS Sharpe still < 0 after training, the remaining P2 fix is the most likely culprit:

### End-of-Trade Reward (Priority 2)
```python
# Current (per-bar):
reward = bar_pnl + trend_bonus − fees

# Proposed (trade-close only):
if trade_just_closed:
    reward = total_trade_pnl − total_fees − total_funding
else:
    reward = 0.0  # (minus funding only)
```

Agent learns to estimate full trade outcome at entry, not per-bar myopia.
TP rate should increase from ~1% to something meaningful.

---

## 7. Summary Table

| Issue | Symptom | Fix | Status |
|-------|---------|-----|--------|
| Single-regime val (2022 only) | Bear-overfitting | Multi-regime val (3 windows) | ✅ Session 9 |
| Wrong early-stop criterion | Overfit to 2022 ret_pct | Min Sharpe across regimes | ✅ Session 9 |
| No trade skip option | Wrong-direction entries unavoidable | POS_SIZE_MIN=0 + ConfidenceGate | ✅ Session 9 |
| No OOD detection | Agent unaware when market ≠ training | MarketDiagnostics EMA z-space | ✅ Session 9 |
| Overfitting | Good val, bad OOS | weight_decay=1e-4 | ✅ Session 9 |
| Shallow regime model | Can't detect regime persistence | BetaEngine stability head | ✅ Session 9 |
| Shallow risk model | Underestimates downside | AlphaEngine quantile + sl_prob | ✅ Session 9 |
| Per-bar reward misalignment | TP rate ≈ 0% | End-of-trade reward | ⏳ Session 10 |
| Reward ≠ objective | Optimize PnL, measure Sharpe | Sharpe reward shaping | ⏳ Session 10 |
| Fee drag | Small pos × fees eat returns | Increase pos_size or threshold | — Not prioritised |

---

## 8. Session 11 & Quant Macro V1: The "Fee Drag" Collapse (2026-07-16)

### The Setup
Session 11 was trained and submitted to the live API backtest over a 5-year log (2021-08 to 2026-07).
We also ran a rule-based `Quant_Macro_v1` submission that bypassed the RL agent entirely, relying strictly on `0.65 * macro_score + 0.35 * swing_score` to dictate entry confidence and sizing.

### The Results

| Submission | Total Trades | CAGR | Fees + Slippage | Note |
|------------|--------------|------|-----------------|------|
| **Quant_Macro_v1** (No RL) | 683 | -7.9% | $487,000 | The raw signals generate a baseline loss against live execution costs. |
| **DRL_v2_session11** | 89 | -2.2% | $147,000 | The agent recognized the negative expectancy and mathematically collapsed its sizing to ~0.500 (zero conviction). |

### The Diagnosis
During the `Session 11` OOS diagnosis, we uncovered a critical flaw in our testing framework:
Our local validation/grid search scripts (which estimated a +22% ROI for the macro indicators) heavily underestimated the true cost of **exchange funding rates** and **dynamic slippage**.

When subjected to the API platform's exact institutional friction:
1. The `Quant_Macro_v1` rules lost **$487,000** in fees/slippage, entirely wiping out any gross profitability generated by the `macro_score` trend following.
2. The Deep RL agent (`session11`), having been penalized by these same drawdowns during training, accurately modeled that trading these specific features leads to a net loss. To preserve capital, the agent optimally refused to trade, collapsing its `pos_size` output to universally output the smallest possible tier (yielding just 89 executed trades over 5 years).

### Conclusion & Enhancement Path
The RL agent is not broken; it is accurately protecting capital from features that lack sufficient predictive Alpha to overcome the 0.05% fee barrier.

**Enhancement (Alpha Generation):**
Tuning risk thresholds will not salvage negative-expectancy features. The immediate next step is to pivot to the **Alpha Researcher** agent to develop higher-Sharpe, higher-Information Ratio features (e.g., localized mean-reversion, volume-node imbalances) inside `factor_library/`. Once the agent is fed features that mathematically beat the fee drag, its confidence sizing will naturally expand.
