# ChatGPT Enhancement Prompt — DRL BTC Agent

> Copy everything below this line and paste into ChatGPT.

---

## Context: What I'm Building

I'm training a Soft Actor-Critic (SAC) deep reinforcement learning agent to trade BTC/USDT perpetual futures on Binance, operating on 1-hour bars. The agent controls 4 risk dimensions: position size, stop-loss distance, take-profit distance, and whether to use a trailing stop. Entry direction (LONG/SHORT/FLAT) is NOT controlled by the neural network — it comes from a deterministic composite signal rule I designed.

The system passed internal validation (+4.82% return, Sharpe +0.73) but failed on out-of-sample data (−6.81% return, Sharpe −0.99) and I want to understand why and how to fix it.

---

## System Architecture

### Data and Features (209 total)
- **Data**: BTC/USDT 1h OHLCV, 4h OHLCV, 1d OHLCV from Binance, plus 1h funding rate and order book depth
- **Date splits**: Train = 2021-01-01 to 2024-12-31 (35,035 bars), Val = 2022-01-01 to 2022-12-31 (8,737 bars, BTC −66% bear year), OOS = 2025-01-01 to now (never seen during training)
- **Feature groups**: Trend (EMA, Supertrend, ADX, Ichimoku), Momentum (RSI, MACD, KDJ, WaveTrend, Stochastic), Volatility (ATR, Bollinger, Choppiness), Volume (Volume Z, Taker Ratio, CVD, OBV), Structure (Price Z, FVG, Imbalance, Order Block, Swing pivots), plus Funding Rate (6 features), Order Book Depth (8 features)
- **Normalisation**: All features clipped and scaled to [-1, +1]

### Composite Signals (pre-computed, appended as 4 extra features)
These are NOT learned — they are engineered signal combinations the agent can read:

1. **macro_score** = 0.50 × avg(ema_cross across 1h/4h/1d) + 0.35 × avg(supertrend across 1h/4h/1d) + 0.15 × (−funding_raw)
   → range [-1,+1]: +1 = strong bullish, -1 = strong bearish

2. **swing_score** = 0.35×macd_hist_4h + 0.30×(rsi14_4h−0.5)×2 + 0.25×aroon_diff_4h + 0.10×(kdj_j_4h−0.5)×2
   → range [-1,+1]: confirms 4h momentum

3. **entry_score** = 0.35×ob_ba_ratio + 0.30×taker_ratio_z + 0.25×cvd_z + 0.10×rsi14_slope_1h
   → range [-1,+1]: 1h microstructure entry quality

4. **regime_score** = 0.35×anti_chop + 0.45×adx_4h + 0.20×vol_ok
   → range [-1,+1]: >0 = trending market, <0 = choppy

### Direction Rule (fully deterministic, actor cannot override)
```
combined = 0.65 × macro_score + 0.35 × swing_score

if combined > +0.10 AND regime_score > 0:  LONG
if combined < −0.10 AND regime_score > 0:  SHORT
else:                                      FLAT (no trade)
```
Result: ~15% LONG, 26% SHORT, 60% FLAT on training data.

### Neural Network (PerspectiveEncoder → LSTM → Actor)
- **Input**: (batch, 48 bars, 217 values) = 209 market features + 8 portfolio state features
- **PerspectiveEncoder**: Split 217 features into 9 semantic groups → each group gets Linear projection → 32-dim embedding → 9 tokens → Multi-Head Self-Attention (4 heads) → 9×32 = 288 pooled → fed into LSTM
- **LSTM**: hidden=512, 2 layers, dropout=0.1 → output z(512)
- **Actor (SAC)**: z(512) → FC(512)→ReLU→FC(256) → 4D Gaussian (μ, log_std) for {pos_size, sl_atr_mult, tp_atr_mult, trail_on}
- **Twin Critics**: Each has own encoder; Q = FC(512)→ReLU→FC(256)→1; use min(Q1,Q2) with separate target networks

### Action Space (4D — risk management only)
| Action | Decoding | Range |
|--------|---------|-------|
| pos_size | linear remap [-1,1] | 5% – 25% of equity |
| sl_atr_mult | linear remap [-1,1] | 0.5× – 3.0× ATR |
| tp_atr_mult | linear remap [-1,1] | 1.0× – 6.0× ATR |
| trail_on | sigmoid(a×3) > 0.5 | bool |

**Actor only acts at trade ENTRY.** Risk params are fixed for the entire trade duration.

### Trade Mechanics
- Entry only when direction signal fires (LONG/SHORT) and currently flat
- SL and TP computed from ATR at entry: `sl_price = entry_px × (1 − dir × sl_mult × atr_frac)`
- Trailing stop: if trail_on, SL follows trail_peak in favorable direction
- Exit triggers (rule-based, actor cannot control): (A) SL hit, (B) TP hit, (C) direction reverses, (D) 96-bar timeout (4 days)
- Fees: 0.04% taker on entry + exit = 0.08% round-trip
- Funding: ~0.00004% per bar while holding
- Kill switch: if drawdown ≥ 50%, episode terminates

### Replay Buffer
**Trade-level replay** (key design choice): stores 1 transition per CLOSED trade:
```
(obs_at_entry, action_at_entry, total_trade_pnl, obs_after_exit)
```
This means Q(entry_state, action) ≈ E[total_trade_pnl directly]. No per-bar transitions.

### Training Pipeline (4 stages)
- **Stage 0**: SharedModel supervised pretrain on encoder:
  - BetaHead: predict Bull/Bear/Range regime from 24h forward return (30 epochs)
  - AlphaHead: predict [E[return], MFE, MAE, P(TP), hold_time] (30 epochs)
  - Encoder weights copied to Actor before stage 1
- **Stage 1**: Behavioral Cloning pretrain (~30 seconds): actor trained on oracle risk labels (pos_size = regime×0.20+0.05, sl = 1.5×ATR, tp = 3.0+adx×2.0, trail = 1 if adx>0.5)
- **Stage 2**: Warmup — 500 complete trades with random actions to fill replay buffer
- **Stage 3**: SAC learning (600K environment steps, update every 1 closed trade with 20 gradient steps, batch=512)

### Key SAC hyperparameters (Session 8, currently training)
- BATCH_SIZE = 512, G_STEPS = 20 (UTD ratio = 20×)
- GAMMA = 0.99, TAU = 0.005
- ALPHA_FIXED = 0.3 (entropy temperature frozen — no auto-tuning)
- BUFFER_SIZE = 100K trades
- LR_ACTOR = LR_CRITIC = 3e-4

---

## Problem Statement: OOS Failure

### Val vs OOS Results

| Window | Period | Return | Sharpe | MDD | L/S/F |
|--------|--------|--------|--------|-----|-------|
| Validation | 2022-01-01 → 2022-12-31 | +4.82% | +0.73 | 4.5% | 15/26/60% |
| OOS (never seen) | 2025-01-01 → 2026-07-15 | **−6.81%** | **−0.99** | **8.89%** | 19/24/57% |

The best checkpoint (selected by highest val Sharpe at step 120K) failed badly on OOS.

### Specific OOS Symptoms
1. **57% of OOS bars are flat** — direction rule fires infrequently on 2025 data
2. **TP rate ≈ 0%** on OOS — almost no trades exit via take-profit; all exit via SL or direction change
3. **SHORT bias in a bull market** — OOS L/S = 19%/24% even though 2025-2026 BTC is mostly bullish
4. **Average hold drops** — shorter holds than validation, suggesting SL stops being hit early
5. **Avg trade PnL strongly negative** — consistent losing trades, not just a few large ones

### My Hypotheses for Why it Failed
1. **Single-regime validation**: Val is exclusively 2022 (BTC −66% bear). Model optimises to short bear markets and survive by being conservative. On 2025 bull, this strategy loses.
2. **Reward-objective mismatch**: Per-bar PnL reward ≠ Sharpe (what I measure). Agent learns to maximise bar-by-bar PnL, not risk-adjusted returns.
3. **No TP hits = wrong objective**: TP range is 1.0–6.0×ATR. Agent never lets trades run to TP because per-bar rewards near TP (trend slowing) are slightly negative → agent exits early every time.
4. **Direction rule doesn't adapt**: 2025 BTC has different signal distributions than 2022-2024 training. The composite signal formula was calibrated on 2021-2024, but feature statistics differ in 2025 (different funding rates, different ATR levels, different EMA regime).
5. **Actor can't veto direction**: If the composite signal says SHORT in a bull market, the actor HAS to execute the short. The only lever is position size, but POS_SIZE_MIN=0.05 (5%) means it can't fully skip a bad trade.

---

## What Was Tried (Session History)

| Session | Key Change | Outcome |
|---------|-----------|---------|
| 1-4 | Base architecture, direction BC pretrain, leverage reduction | Overfit; liquidated every episode |
| 5 | Rule-based direction, PER buffer, 2022 val window | +5.74% at 10K but Q-cycling ±Sharpe every 20K |
| 6 | BC Exit Pretrain, 5D action with exit_signal | Q-cycling continued; exit_signal bistable |
| 7 | Remove exit_signal (4D), trade-level replay | Q-cycling FIXED; stable +4.68–4.82% val Sharpe; but OOS −6.81% |
| 8 | LSTM 512, batch 512, G_STEPS 20, SharedModel pretrain | TRAINING NOW — no OOS result yet |

**Biggest fix so far**: Session 7 trade-level replay eliminated Q-oscillation (Session 6 had Sharpe swinging between +0.69 and −2.80 every 20K steps). Now val Sharpe is stable ~+0.73 but doesn't generalise.

---

## My Current Enhancement Plan (asking for your input on these)

I have 9 proposed enhancements. I want your help prioritising them and checking if I'm thinking about them correctly:

### A. Multi-period Validation Window
Replace single 2022 val with average of 3 periods (2022 bear, 2023 recovery, 2024 bull segment).
Early-stop on average Sharpe across all 3. **Is this the right way to prevent single-regime overfitting? What window size and composition would you recommend?**

### B. End-of-Trade Reward
Currently: reward = bar_pnl every bar.
Proposed: reward = 0 during trade, reward = total_trade_pnl only when trade closes.
The trade-level replay buffer already stores (entry, action, total_pnl, exit), so Q(s,a) already approximates total trade PnL. **Would changing the env reward to 0-mid-trade / full-at-close change what Q learns, given the trade-level buffer? Or does the buffer already handle this?**

### C. Allow pos_size = 0 (Trade Skip)
Extend POS_SIZE_MIN from 0.05 to 0.00. Actor can output pos_size≈0 to effectively skip a direction signal it disagrees with.
**Is this a valid approach for soft direction vetoing? What training dynamics does allowing zero-size action create — does the agent collapse to always outputting 0?**

### D. Sharpe-Optimizing Reward
Replace raw bar PnL with rolling Sharpe-like reward:
```
reward_t = (bar_pnl − rolling_mean(last N)) / (rolling_std(last N) + ε)
```
**Is normalizing reward this way equivalent to optimizing Sharpe? What N (window size) works well in practice for 1h BTC trading? Are there known issues with this approach?**

### E. N-Step Returns (n=4 or 8)
Currently 1-step TD. Proposed: 4-step or 8-step returns to give Q faster signal about trade outcomes.
**Given that I already have trade-level replay (not per-bar), do N-step returns still add value? The buffer already gives Q the full trade outcome — isn't that better than N-step?**

### F. BetaHead Direction Override
The BetaHead (trained in Stage 0) predicts P(Bull/Bear/Range). Instead of ignoring this for direction, use it to optionally override or gate the rule-based direction:
```
rule_dir = composite_signal_direction   # LONG / SHORT / FLAT
beta_conf = BetaHead(z)                 # P(bull), P(bear), P(range)
# Gate: if rule_dir=LONG but beta_conf P(bear) > 0.6 → skip or reduce size
```
**Is this the right way to use a supervised head to soft-veto a rule-based system? Or should the BetaHead replace the rule entirely? What are the risks of the BetaHead being wrong on OOS data too?**

### G. Weight Decay + Dropout
Add L2 weight decay (1e-4) to actor and critic Adam optimisers. Increase LSTM dropout from 0.1 to 0.2.
**Is 1e-4 a reasonable weight decay for SAC with a LSTM encoder? Does weight decay interact negatively with SAC's policy entropy?**

### H. Adaptive Entry Threshold
Make ENTRY_THRESHOLD regime-dependent:
```python
effective_threshold = 0.10 + max(0, 0.10 × (1 - regime_score))
# chop: threshold = 0.20, trend: threshold = 0.10
```
**Does raising the threshold in choppy regimes meaningfully reduce bad trades, or will the agent just learn to output larger positions on the fewer signals it does see?**

### I. Reduce TP_ATR_MULT_MAX from 6.0× to 3.0×
TP rate is 0% on OOS — agent never hits 6.0×ATR. Capping TP at 3.0×ATR might force the agent to use realistic targets.
**Or is the 0% TP rate caused by the reward structure (the agent prefers to exit before TP), not the TP range? If I cap TP at 3.0× but the reward still penalises late exits, does it help?**

---

## Specific Questions

1. **Highest impact fix**: If you had to pick ONE change from A–I above to most likely improve OOS Sharpe from −1.0 to positive, which would it be and why?

2. **Trade-level replay + end-of-trade reward interaction**: I use trade-level replay (buffer stores full trade PnL). Does that make per-bar reward irrelevant — i.e., does Q already know the trade outcome regardless of what reward I give mid-trade? Or does the env reward shape training even with trade-level buffer?

3. **Val window composition**: For a BTC 1h strategy trained on 2021-2024, what validation window would you recommend to get the best OOS correlation? Should I use rolling windows, random segments, or specific known regimes?

4. **Feature distribution shift**: The 2022 BTC composite signals (EMA bearish, Supertrend bearish, funding positive = short pressure) are calibrated to bear market conditions. In 2025, even in a flat/bull market, the composite signals may fire with different base-rates. **How do I detect and handle feature distribution shift in a rule-based direction gate?**

5. **UTD ratio 20× risk**: I increased from 1 to 20 gradient steps per trade. High UTD ratios are known to cause overestimation and instability in SAC. **What symptoms should I watch for, and what diagnostic metrics (Q-value divergence, logπ, actor loss) indicate overfitting to the replay buffer?**

6. **SAC vs IQL vs TQC**: For this use-case (fixed 1h bars, 4D continuous action, rule-based direction, sparse trades), would Implicit Q-Learning (IQL) or Truncated Quantile Critic (TQC) significantly outperform standard SAC? What specific property of the problem makes one better?

7. **Direction learning**: My composite signal was calibrated on 2021-2024 data. If I wanted to **learn** the direction from data instead of hand-coding it, what approach would you use? Should I train a separate classification model first (like my BetaHead) and then use it to generate direction signals? What features would matter most?

---

## What I'm NOT looking for

- Suggestions to add more features (209 is already a lot)
- Suggestions to use a different base algorithm than SAC (I want to solve generalisation first)
- Suggestions to add more lookback (48-bar window is well-motivated for 1h BTC)
- Generic advice to "get more data" — I have 4 years of 1h data (35K bars) which is already limited for RL

---

## Summary of What I Want From You

1. Tell me if my hypotheses about OOS failure are correct and which is most likely the root cause
2. Give me a prioritized enhancement plan (which of A–I would you do first, second, third?)
3. Answer my 7 specific questions above
4. Flag any enhancements I'm missing that have strong theoretical backing for this type of problem (short-holding, crypto, 1h bar, rule-based direction with RL risk management)
