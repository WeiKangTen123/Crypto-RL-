---
status: PAPER_READY
id: 117
sharpe: 1.48
return: 512.0
MDD: 35.2
---

# Market Fit Memo: FORGE_ETH_ZLEMA_TAKER_MAXHOLD (ID 117)

## 1. Recent Regime Check
Current ETH/4h regime (June 2026) shows sustained uptrend with healthy taker buy ratios — optimal conditions for ZLEMA trend detection and taker confirmation. ATR in normal range (not extreme low-vol or high-vol). Regime matches backtested conditions.

## 2. Correlation Warning
Strategy shares taker flow dependency with #125 (FVG + taker). If both are deployed simultaneously, allocate no more than 15% combined on taker-flow correlated signals to avoid doubling exposure to a single factor failing (e.g., exchange reporting anomaly affecting taker data).

## 3. Deployment Recommendation
Ready for paper trading. ZLEMA crossover signals are mechanical and easily monitored. Set alerts on taker buy ratio crossing threshold. Begin with 50% of target allocation for 30 days of paper monitoring, then scale to full allocation if slippage < 0.15%.
