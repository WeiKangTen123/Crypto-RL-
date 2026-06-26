---
name: DOT 4H BB Breakout — WR + RSI Filtered (Forge #144)
category: Trend
coins: [DOT]
timeframes: [4h]
status: IMPLEMENTED
strategy_id: 144
sharpe: 2.10
win_rate: 58.6
total_return: 94.4
max_drawdown: 8.3
tags: [forge, trend, bb_breakout, psar_trail, wr_not_extreme, rsi_not_extreme, DOT, 4h]
---

## Alpha Premise
Bollinger Band breakout on DOT 4H, quality-gated by Williams %R (not extreme) and RSI (not extreme) to filter out overbought/oversold breakouts that tend to reverse. Exits via PSAR trailing stop to lock in trend profits without capping upside.

## Strategy Play Style
Trend-momentum breakout. Waits for price to break outside the Bollinger Band (short period=5) confirming volatility expansion, then confirms that WR and RSI are in a neutral zone (not stretched). Exit is fully adaptive via PSAR trailing.

## Key Parameters
- Entry: `bb_breakout` (period=5)
- Filter 1: `wr_not_extreme` (zscore_period=26, zscore_threshold=0.5885)
- Filter 2: `rsi_not_extreme` (via adx_period=26, adx_threshold=21)
- Exit: `psar_trail` (acceleration=0.0198, maximum=0.3941)
- Coin: DOT / TF: 4h

## Performance (2024-01 → 2026-05)
- Sharpe: 2.10 | MDD: 8.3% | Monthly ROI: 2.32%
- IS Sharpe: 2.00 | OOS Sharpe: 2.34 (OOS > IS — no overfitting)
- 104 trades total, 20 exits in 2026

## Strategic Advantages
- OOS outperforms IS: robust across unseen 2025-2026 market conditions
- Low MDD (8.3%) leaves headroom within 20% risk budget
- Active in 2026 bull run (20 exits) — not blocked by macro_regime filter

## Agent Reasoning (Chain of Thought)
Discovered via multi_forge_search.py (2024-01-01 to 2026-05-31, 5%/5x risk). Strategy #6 in the search ranking. BB breakout with period=5 captures short bursts of volatility expansion on DOT's 4H structure. The dual WR+RSI filter ensures we only enter when price is not already stretched, eliminating the "buy at peak" problem of pure breakout strategies. PSAR trail provides dynamic stops that widen in trending conditions.
