# DRL_BTC Training Analysis

> **Status: Historical — issues documented here were addressed in Sessions 2–6.**
> See `agent_overview.md` for current architecture.

This document recorded early-stage training pathologies observed before Sessions 2–3 fixes.

---

## Issues (all resolved)

### 1. Always-In Trap — `FLAT_PENALTY = 0.010` ✅ Resolved (Session 5)
- **Was**: Heavy flat penalty forced the agent to always trade, bleeding equity through fees.
- **Fix**: Direction is now rule-based (composite signal gate). The agent can't choose to be flat —
  it's either directed to enter or not. FLAT_PENALTY config remains but is not applied in env.

### 2. Continuous Drawdown Penalty ✅ Resolved (Session 2)
- **Was**: `current_dd × 3.0 × 0.1` per bar in drawdown destroyed Q-value estimation.
- **Fix**: Drawdown penalty kept but properly scaled; agent no longer intentionally liquidates.

### 3. Hardcoded Risk — Action Overrides ✅ Resolved (Session 6)
- **Was**: Actor outputs 5D actions but env overrode size=0.20, leverage=1.5 (hardcoded).
- **Fix (Session 6)**: Action space repurposed — SAC controls [pos_size, sl_atr, tp_atr, trail_on, exit_signal].
  Dynamic SL/TP set at entry from actor output. Leverage fixed at 1.0× (not overriding actor, just simplified).

### 4. Forced Churning — 96-bar Hold Limit ✅ Partially mitigated
- **Was**: 96-bar timeout + flat penalty → forced fee-bleed cycle.
- **Fix**: Flat penalty removed (direction rule-based). 96-bar timeout retained as hard backstop
  but no longer the primary exit driver — SL/TP and exit_signal are.

### 5. Liquidation Loop ✅ Resolved (Session 2–4)
- **Was**: Untrained agent statistically liquidated every 5,000–7,000 bars.
- **Fix**: MAX_LEVERAGE 5× → 2× (Session 2), pos_size 0.30 → 0.20 (Session 4),
  then dynamic sizing 5–25% (Session 6). Agent survives long enough to learn from rewards.
