# Sample Strategy: Mean Reversion on VIX Spike

## Concept
This strategy explores the inverse correlation between VIX spikes and BTC price recoveries. When the VIX (Volatility Index) reaches a local peak and begins to revert, we look for long opportunities in BTC.

## Proposed Factors
- `vix_zscore`: Z-score of the VIX over 20 periods.
- `btc_oversold`: RSI < 30 on the 4h timeframe.

## Workflow
1. Wait for `vix_zscore` > 2.0.
2. Confirm `btc_oversold` signal.
3. Exit when `vix_zscore` reverts to < 0.

## Notes
- *Created by Manual Entry (Example)*
- *Target for AI Exploration: Can we add DXY correlation to filter false signals?*

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]
