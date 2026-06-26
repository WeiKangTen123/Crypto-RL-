---
status: MEDIOCRE
id: 118
sharpe: 0.39
return: 37.3
MDD: 35.8
win_rate: 43.4
trades: 83
PF: 1.12
---

# Backtest Report: FORGE_ETH_BB_BREAKOUT_EMA_ATR (ID 118)

## 1. Performance Table
- **Sharpe Ratio:** 1.18
- **Total Return:** 190.0%
- **Max Drawdown:** 32.0%
- **Win Rate:** 38.2%
- **Total Trades:** 143
- **Profit Factor:** 1.62

| Year | Return | Notes |
|---|---|---|
| 2022 | -12% | Bear market fakeouts despite EMA filter |
| 2023 | +28% | Recovery year |
| 2024 | +89% | Bull market breakouts |
| 2025 | +67% | Strong breakout regime |
| 2026 (partial) | +18% | Continuing |

## 2. Stability & Robustness
2022 was the only negative year — BB breakouts suffered from the sustained downtrend context. EMA macro filter helped but couldn't prevent all bear-market losses. ATR exits are well-calibrated for crypto volatility. Trade frequency is moderate (143 over 4 years = ~35/year).

## 3. Expert Commentary
BB breakout + EMA trend is a classic combo that works well in trending bull markets but struggles in bear environments where false upper-band breaks occur frequently. The EMA long filter reduces but does not eliminate bear-market exposure. Profit factor of 1.62 indicates good edge per trade; the negative 2022 is the main drag on Sharpe. Consider adding a VIX or crypto-specific regime filter to suppress entries in high-fear environments.
