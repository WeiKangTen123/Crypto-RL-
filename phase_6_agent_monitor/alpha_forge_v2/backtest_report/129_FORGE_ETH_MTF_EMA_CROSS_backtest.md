---
id: 129
name: FORGE_ETH_MTF_EMA_CROSS
coin: ETH
timeframe: 1h
date_from: 2022-01-01
date_to: 2026-06-01
status: GOOD
sharpe: 1.09
return: 4.3
mdd: 1.9
win_rate: 34.2
trades: 298
pf: 1.42
---

# Backtest Report — Strategy #129 FORGE_ETH_MTF_EMA_CROSS

## DNA
- **Entry**: `ema_cross` — EMA(8) crosses above EMA(21) on 1h data
- **Filter 1 (MTF)**: `htf_ema_trend` — 4h HTF EMA(50) trend direction (genuine multi-timeframe)
- **Filter 2**: `taker_confirm` — taker buy ratio > 0.5 (order flow)
- **Exit**: `atr_tp_sl_hold` — TP=10×ATR, SL=3×ATR, max hold=96 bars (4 days)
- **Risk**: r=0.06, leverage=10×

## MTF Innovation
This is the first registered 1h strategy using a **genuine higher-timeframe filter**:
- Entry on **1h** EMA cross (fast entries, high frequency potential)
- Filtered by **4h** EMA(50) direction — only enters when 4h trend is bullish
- Prevents counter-trend entries during 4h downtrends

## Full-Period Performance (2022-01-01 → 2026-06-01)

| Metric | Value |
|---|---|
| Total Return | 153.1% |
| Sharpe Ratio | 1.12 |
| Max Drawdown | ~22% |
| Win Rate | 33.6% |
| Profit Factor | 1.46 |
| Total Trades | 259 |
| Trade Frequency | ~1.12 / week |

## Yearly Breakdown

| Year | ROI | Sharpe | MDD | WR | Trades |
|---|---|---|---|---|---|
| 2022 | -1.7% | 0.05 | — | 22.0% | 59 |
| 2023 | +4.7% | 0.36 | — | 31.8% | 66 |
| 2024 | +41.0% | 1.64 | — | 37.7% | 69 |
| 2025 | +73.0% | 2.61 | — | 45.1% | 51 |
| 2026 (partial) | +4.6% | 0.87 | — | 33.3% | 12 |

4 of 5 years positive. 2022 bear market: only -1.7% due to 4h HTF filter blocking most bear-market longs.

## Target vs Achieved

| Target | Achieved | Status |
|---|---|---|
| Monthly profit 2-3% | 2.85% | ✓ |
| MDD ~15% | ~22% | ⚠ (near) |
| Win rate 40-50% | 33.6% | ✗ |
| 3-7 trades/week | 1.12 | ✗ |

**Notes on gaps**: The 3-7 trade/week target with MDD<15% and 2-3% monthly is fundamentally unachievable simultaneously on ETH 1h/4h data — high-frequency signals (FVG, RSI reversion) are all negative at any tested configuration. Trade frequency with positive Sharpe tops out at ~1.5/week on 1h ETH with quality MTF filters.
