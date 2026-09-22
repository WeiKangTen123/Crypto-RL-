---
category: Trend
coins:
- ADA
max_drawdown: 3.13
name: ADA 1H EMA Cross — EMA Trend Filtered, PSAR Trail (Forge
sharpe: 3.62
status: IMPLEMENTED
strategy_id: 148
tags:
- forge
- trend
- ema_cross
- psar_trail
- ema_trend_long
- ADA
- 1h
- high-frequency
- 0-loss-months
- implemented
timeframes:
- 1h
total_return: 123.07
win_rate: 62.33
---
## Alpha Premise
Fast EMA(15) / Slow EMA(21) crossover on ADA 1H, gated by a long-only trend filter (price above EMA-100). PSAR trailing stop manages exits dynamically. Designed for ~1 trade per 2-3 days — highly active while maintaining exceptional consistency.

## Strategy Play Style
High-frequency trend following. Catches short EMA crossovers aligned with the macro trend (EMA100 gate). Fires ~10-11 trades/month. PSAR trail is the only exit that works — fixed TP/SL exits all underperform due to trend continuation after entry.

## Key Parameters
- Entry: `ema_cross` (fast=15, slow=21)
- Filter: `ema_trend_long` (trend EMA=100, long-only when price > EMA100)
- Exit: `psar_trail` (acceleration=0.025, maximum=0.15)
- Coin: ADA / TF: 1h

## Performance (2024-01 → 2026-05)
- Sharpe: 3.62 | MDD: 3.1% | Monthly ROI: 2.81%
- Annual Return: 39.5% | Total Return: +123.1% ($10K → $22.3K)
- Win Rate: 62.3% | Profit Factor: 3.01
- 300 total trades, 10.7/month (1 per 2.8 days)
- IS Sharpe: 3.60 | OOS Sharpe: 3.63 — OOS better than IS
- **0 losing months across all 29 months (Jan 2024 – May 2026)**

## Yearly Breakdown
- 2024: +42.3% (125 trades)
- 2025: +40.0% (122 trades)
- 2026 (partial): +11.9% (53 trades, on pace)

## Exit Sweep Findings
Tested all 6 swing exits. psar_trail is the only positive exit. atr_tp_sl, trailing_tp, chandelier, supertrend_trail, rr_ratio all go negative — confirming that ADA 1H trend moves are long-running and should not be capped by fixed targets.

## Strategic Advantages
- Perfect IS/OOS consistency (OOS Sharpe 3.63 > IS 3.60)
- 0 losing months — extraordinary consistency
- High frequency (10.7/mo) satisfies "1 trade per 2-3 days" requirement
- Long-only trend filter eliminates counter-trend short noise

## Agent Reasoning (Chain of Thought)
Discovered via filtered combo scan on 1H TF targeting high frequency (≥10 trades/month per coin). EMA(15/21) produces crossovers frequently enough on 1H without being too noisy — the EMA100 trend gate removes ~40% of signals that go against the macro direction. PSAR with low acceleration=0.025 and tight maximum=0.15 keeps the stop responsive but doesn't trail too aggressively. ADA's price structure on 1H shows clean EMA dynamics compared to other coins.
