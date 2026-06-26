---
name: forge_v2_mtf_ema_cross
type: Trend_Momentum
strategy_id: 129
status: VALIDATED
---

# Hypothesis: MTF EMA Cross — 1h Entry + 4h Trend Filter

## Core Thesis
On 1h ETH, EMA(8/21) crossovers produce many signals (3-5/week raw) but most are noise. By requiring the 4h EMA(50) trend to be bullish at entry time, only signals aligned with the higher-timeframe structure pass. Taker confirm adds order-flow validation. Result: ~1.1/week high-conviction longs with positive edge.

## MTF Logic
- **Execution TF**: 1h — fine-grained entry timing
- **Filter TF**: 4h — structural trend direction
- **Signal**: long when 1h fast EMA crosses above slow EMA AND 4h price > 4h EMA(50) AND taker buy ratio > 0.5

## Why HTF EMA Filter Works
In a 4h uptrend (price > 50-bar 4h EMA), 1h dips that recover (EMA cross) are high-probability continuations. In a 4h downtrend, the same 1h EMA cross is a dead-cat bounce → filtered out.

## Expected Edge
- Bear market: HTF filter cuts 60-70% of signals → very few trades, minimal drawdown
- Bull market: HTF filter stays open → consistent longs captured via 1-4 day holds
- WR ~34% with 3.3:1 RR → positive expectancy after 10× leverage fee drag

## Validation
- Backtested 2022-2026 (4.5 years, 38,688 bars)
- Sharpe 1.12, ROI 153%, 4 of 5 years positive
- 2022 only -1.7% despite 70%+ crypto drawdown
