---
strategy_id: 141
strategy_name: AVS_BTC_4H
status: REJECTED
date: 2026-06-23
failure_stage: PBO_AUDIT (Stage 7)
pbo: 0.400
oos_loss_prob: 0.800
---
## Autopsy Report for Adaptive Volatility Squeeze (AVS_BTC_4H)

**Date of Autopsy:** 2026-06-23

**Strategy ID:** 141
**Strategy Name:** AVS_BTC_4H
**Failure Stage:** PBO_AUDIT (Stage 7)

**Parameters:**
- `bb_period`: 20
- `bb_std`: 2.0
- `kc_period`: 20
- `kc_mult`: 1.5
- `adx_period`: 14
- `adx_threshold`: 25.0
- `fisher_period`: 10
- `use_vrsi_filter`: True
- `vrsi_period`: 14
- `vrsi_threshold`: 70.0
- `chandelier_atr_period`: 22
- `chandelier_mult`: 3.0
- `use_regime_filter`: True
- `use_squeeze_filter`: True

**Reason for Rejection:**
The strategy failed the Probability of Overfitting (PBO) audit and Tier 1 Fatal Gates:
- The strategy failed the PBO check `T2-03` with a Probability of Overfitting (PBO) of 0.400 and an Out-of-Sample (OOS) Loss Probability of 0.800 (thresholds: PBO < 0.50 and OOS Loss Prob < 0.30). The extremely high OOS Loss Probability of 80% shows that there is a high likelihood of loss in unseen regimes.
- The strategy failed key Tier 1 metrics in the validator report:
  - Sharpe Ratio = -0.820 (threshold: >= 0.5)
  - Total Return = -36.58% (threshold: > 0)
  - Win Rate = 22.84% (threshold: >= 30.0%)
  - Profit Factor = 0.78 (threshold: >= 1.0)
  - WF Efficiency = 0.000 (threshold: >= 0.5)
  - Regime Survival T1-10: 0/2 positive regimes (bear_2022 was N/A (< 50 bars), range_2023 Sharpe = -2.814, bull_2024 Sharpe = -0.245)

**Root Cause Diagnosis:**
The strategy exhibits persistent losses and high volatility during both the in-sample (IS) and out-of-sample (OOS) periods. The core logic of the Adaptive Volatility Squeeze fails to filter out false breakouts in consolidating/ranging regimes, resulting in an elevated number of trades (162) and a very poor win rate (22.84%). The high probability of OOS loss (80%) confirms substantial overfitting to the training samples, rendering it unsafe for live incubation or stress testing.

**Recommendation:**
The strategy is permanently exiled to the GRAVEYARD stage. The core Volatility Squeeze concept requires structural redesign (e.g. better trend-following confirmations or stricter dynamic volume gating) before any future strategy assembly can be attempted.
