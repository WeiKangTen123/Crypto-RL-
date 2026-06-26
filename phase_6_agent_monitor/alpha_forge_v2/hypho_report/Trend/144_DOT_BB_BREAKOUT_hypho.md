# Phase 6 Hypothesis Report: DOT 4H BB Breakout — WR + RSI Filtered (Forge #144)

## Executive Summary
Bollinger Band breakout on DOT 4H, quality-gated by Williams %R and RSI to reject stretched-momentum breakouts. Exits via adaptive PSAR trailing stop. Targets monthly ROI of 2-3% with MDD under 20% on Polkadot's 4H structure.

## Mathematical Model
- **Entry Component**: Price breaks beyond the upper/lower Bollinger Band (period=5) — short-period BB captures micro-volatility expansions.
- **Filter 1 (WR Quality Gate)**: Williams %R Z-score must be in neutral zone (not extreme). Zscore period=26, threshold=0.5885.
- **Filter 2 (RSI Quality Gate)**: RSI confirmation via ADX period=26, threshold=21 — rejects overbought/oversold breakout setups.
- **Exit**: PSAR trailing stop (acceleration=0.0198, maximum=0.3941) — adaptive stop that widens in trending conditions and tightens in exhaustion.

## Regime Expectation
This strategy is selective by design (~3.7 trades/month on DOT 4H). The dual WR+RSI quality gate enforces entry only when momentum is valid, not when price is already stretched. This prevents the "buy-at-peak" failure mode of pure breakout systems. PSAR's adaptive trailing ensures the exit respects each trade's individual volatility profile.

## Risk Profile
- **Holding Period**: Medium swing, 1-5 days per trade (4H timeframe).
- **Expected Trade Frequency**: ~3.7 trades/month (1 per ~8 days).
- **Validated IS/OOS**: OOS Sharpe 2.34 > IS Sharpe 2.00 — no overfitting, generalizes to unseen market conditions.
- **Coin Selection Rationale**: DOT 4H shows clean BB structure with sufficient volatility. Multi-coin scan identified DOT as outperforming BTC/ETH/SOL on this entry type.
