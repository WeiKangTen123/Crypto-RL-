---
strategy_id: 108
strategy_name: RSI_MEAN_REVERSION_BTC_1H
status: REJECTED
date: 2026-06-14
failure_stage: WFO_EVO (Stage 6)
sharpe_ratios_wfo: [-5.73, -2.93, -3.50, -3.74]
---
## Autopsy Report for RSI Mean Reversion Strategy (BTC 1H)

**Date of Autopsy:** 2026-06-14

**Strategy ID:** 108
**Strategy Name:** RSI_MEAN_REVERSION_BTC_1H
**Failure Stage:** WFO_EVO (Stage 6)

**Reason for Rejection:**
The strategy demonstrated consistently poor performance during the 4-window Walk-Forward Optimization (WFO) stability check. The Sharpe Ratios across all four windows were negative:
- Window 1: -5.73
- Window 2: -2.93
- Window 3: -3.50
- Window 4: -3.74

These results indicate a lack of robustness and consistent profitability, leading to the strategy's rejection at the WFO_EVO stage. The strategy is deemed unsuitable for further development or deployment due to its inability to maintain positive risk-adjusted returns across different market regimes.

**Recommendation:**
This strategy is permanently exiled to the GRAVEYARD stage. Further research into mean-reversion factors should consider incorporating additional volatility filters or adaptive components to improve robustness and avoid similar performance issues.
