---coins: BTC, ETH, SOL
interest: High
name: ict-holy-trinity-confluence
source: TradingView / ICT Concepts 2026
status: VALIDATED
strategy_id: ICT_HOLY_TRINITY_BTC_1H
tags:
- implemented
timeframes: 1h, 4h
type: short-term
sharpe: 0.21
win_rate: 36.36
total_return: 2.0
max_drawdown: 28.25
---
# ICT Holy Trinity + Supertrend/MACD/RSI

## Concept
This strategy combines institutional order flow concepts (ICT) with classic momentum and trend indicators. It looks for a Liquidity Sweep followed by a Market Structure Shift (MSS) and a Fair Value Gap (FVG), confirmed by Supertrend, MACD, and RSI filters to ensure high-probability entries.

## Entry Conditions
- **Liquidity Sweep**: Price takes out a recent swing high/low (lookback 20-50 bars) but fails to sustain.
- **Market Structure Shift (MSS)**: Price aggressively breaks the previous candle's high/low in the opposite direction of the sweep.
- **Fair Value Gap (FVG)**: A displacement candle creates a gap between the high/low of candles N-2 and N.
- **Filters**: 
    - Long: Supertrend is green, MACD Line > Signal Line, RSI < 70.
    - Short: Supertrend is red, MACD Line < Signal Line, RSI > 30.

## Exit Conditions
- **Take profit**: Target the opposite major liquidity pool or a fixed 2:1 / 3:1 RR ratio.
- **Stop loss**: Below the "Sweep Low" for longs or above the "Sweep High" for shorts.

## Key Indicators
- Supertrend (10, 3.0)
- MACD (12, 26, 9)
- RSI (14)
- Swing High/Low Detection
- FVG Detection

## Expected Edge
The "Smart Money" often sweeps retail liquidity (stop losses) before moving the market in the intended direction. Entering after the sweep + MSS + FVG provides an entry alongside institutional displacement, while indicators filter out noise in choppy markets.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Requires precise FVG and MSS detection logic.
- Supertrend acts as a regime filter to prevent counter-trend trades during strong breakouts.



## Performance Summary
*Auto-updated by sync_backtest_to_obsidian.py when strategy_id matches.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 0.21 |
| Win Rate | 36.36% |
| Total Return | 2.0% |
| Max Drawdown | 28.25% |