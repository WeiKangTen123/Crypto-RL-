---
author: alpha-researcher
coins:
- BTC
- XRP
- BNB
name: Institutional Order Block Mitigation with Fisher Confirmation (OBFC)
status: IMPLEMENTED
tags:
- implemented
timeframes:
- 4h
---
## Alpha Premise
Order Blocks (OBs) represent institutional supply/demand zones. However, blindly entering on OB touches often leads to being stopped out by liquidity sweeps. By requiring a momentum shift confirmation using the Fisher Transform (which detects sharp price reversals with near-zero lag) shortly after the OB touch, we drastically improve the win rate and Sharpe ratio.

## Strategy Play Style
High-Precision Reversal / Pullback. Best suited for structurally trending markets that experience deep, healthy pullbacks.

## Strategic Disadvantages
V-shape recoveries where the Fisher Transform triggers too late, causing missed entries. Continuous bleeding trends that form overlapping order blocks.

## Enhancement Recommendations
1. Incorporate `detect_fvg` to only validate Order Blocks that have an associated Fair Value Gap.
2. Use ATR-based dynamic sizing to reduce risk if the OB zone is exceptionally wide.

## Agent Reasoning (Chain of Thought)
- **Zone Identification**: Use `detect_order_blocks(atr_multiplier=2.0, ob_lookback=3)` to find unmitigated bullish order blocks.
- **Trigger**: Price touches the bullish OB. Within the next 2 bars, `calc_fisher_transform(10)` must cross above its trigger line.
- **Trend Filter**: 200 EMA must be sloping upwards.
- **Exit**: Take profit at 3x ATR above entry. Stop loss placed slightly below the OB low.
- **Library Match**: `detect_order_blocks`, `calc_fisher_transform`, `calc_ema`, `calc_atr`.
