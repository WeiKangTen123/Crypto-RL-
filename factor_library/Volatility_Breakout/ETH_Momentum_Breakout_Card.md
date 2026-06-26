---
coins: ETH, SOL
directional_bias: Symmetric
factor_class: Volatility-Breakout
interest: High
name: ETH Momentum Breakout
optimal_regime: High-Vol
sharpe: 0.0
source: Web Search (google_web_search, referencing github.com for core concept)
status: IMPLEMENTED
strategy_id: 101
tags:
- alpha
- factor
- volatility-breakout
- momentum
- queued
- implemented
timeframes: 1H, 2H, 4H
total_return: 0.0
type: Factor
win_rate: 0.0
---
# ETH Momentum Breakout

## Concept
This strategy identifies periods of low volatility (squeeze) using Bollinger Bands and Keltner Channels, then enters on a price breakout confirmed by volume and RSI. It is designed for high-volatility assets.

## Recommended Logic Switches (For @alpha-developer)
List 2–3 categorical variables the developer MUST include in `OPTIMIZATION_RANGES`.
- `squeeze_duration`: ['3_BARS', '5_BARS', '8_BARS'] (minimum number of bars the squeeze condition must hold)
- `entry_confirmation`: ['VOLUME_SPIKE', 'RSI_FILTER', 'BOTH'] (type of confirmation for entry after squeeze break)
- `exit_strategy`: ['ATR_TRAILING_STOP', 'FIXED_RR_3_5X'] (exit mechanism)

## Entry Logic
- **Squeeze Condition**: Bollinger Bands contract inside Keltner Channels for a specified `squeeze_duration`.
- **Long**: Price breaks above upper Bollinger Band with a significant volume spike (>1.8x average) AND RSI(14) is below 75 (to avoid buying absolute tops).
- **Short**: Price breaks below lower Bollinger Band with a significant volume spike (>1.8x average) AND RSI(14) is above 25 (to avoid selling absolute bottoms).

## Exit Logic
- **Take Profit (TP)**: ATR-based trailing stop or a fixed Risk/Reward target (e.g., 3.5x initial risk).
- **Stop Loss (SL)**: ATR-based stop loss, typically 1-2% from entry or previous swing low/high.

## Key Indicators
- Bollinger Bands (BB)
- Keltner Channels (KC)
- Average True Range (ATR)
- Relative Strength Index (RSI)
- Volume

## Data Requirements
- Columns needed: Close, High, Low, Volume.
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation
- Library Function: `strategy_backtest/library.py` → `calc_bb_kc_squeeze` (for squeeze detection)

## Performance Summary
*Automatically updated by `./venv/bin/python utility/sync_backtest_to_obsidian.py` when `strategy_id` matches.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 0.0 |
| Win Rate | 0.0% |
| Total Return | 0.0% |
| Max Drawdown | 0.0% |

## Observations & Wisdom
- This strategy thrives in volatile markets and during expansion phases after consolidation.
- The volume spike and RSI filter are crucial to avoid false breakouts.
- The 2H timeframe for ETH showed historical performance.
