---
name: OU Mean-Reversion Speed
strategy_id: 195
type: short-term
factor_class: Mean-Reversion
directional_bias: Symmetric
optimal_regime: Ranging
timeframes: [1h, 4h, 1d]
coins: [BTC, ETH, SOL]
source: main.pdf
interest: High
status: QUEUED
sharpe: 0.0
win_rate: 0.0
total_return: 0.0
max_drawdown: 0.0
tags: [alpha, factor, Mean-Reversion]
---

# OU Mean-Reversion Speed

## Concept
The Ornstein-Uhlenbeck (OU) process models price as a mean-reverting process with constant volatility. The "speed" of reversion ($\kappa$) to the long-term mean is estimated using an AR(1) coefficient ($\phi$), where $\kappa = -\ln(\phi) \times 252$. Higher $\kappa$ indicates faster reversion.

## Agent Reasoning (Chain of Thought)
We employ the AR(1) modeling technique on price deviations from a dynamic trend (EMA). This captures the elasticity of the price. If the reversion speed is too low, the asset is trending; if high, it is reverting. This factor provides a statistical basis for entering trades when the mean-reverting tendency is strong.

## Market Regime
- **Works best in**: Ranging / Low-Vol
- **Breaks down in**: Strong directional trend / High-Vol
- **Suggested regime filter**: BB Width < 0.03

## Entry Logic
- **Long**: $\kappa$ > threshold (Strong MR) AND Price < EMA(20)
- **Short**: $\kappa$ > threshold (Strong MR) AND Price > EMA(20)

## Exit Logic
- **Take Profit**: Price reaches EMA(20)
- **Stop Loss**: 1.5× ATR from entry
- **Default R:R**: 2:1

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute AR1 coeff and Kappa
# Price deviation from EMA(20)
dev = Close - EMA(Close, 20)
# Fit AR1: dev_t = phi * dev_{t-1} + e
phi = corr(dev, dev.shift(1))
kappa = -log(phi) * 252

# Step 2 — Entry
long_signal  = (kappa > 5.0) AND (Close < EMA(Close, 20))
short_signal = (kappa > 5.0) AND (Close > EMA(Close, 20))
```

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| EMA | period=20 | `calc_ema(df, 20)` |
| Kappa | N/A | Custom implementation |

## Recommended Logic Switches (For @alpha-developer)
- `entry_filter`: ['NONE', 'BB_WIDTH_SQUEEZE']
- `exit_mode`: ['EMA_RETURN', 'FIXED_ATR']

## Data Requirements
None special.

## Implementation
- Minimum timeframe: 1h
- Minimum history: 1 year
- Library function: `strategy_backtest/library.py`

## Performance Summary
| Metric | Value |
|---|---|
| Sharpe Ratio | 0.0 |
| Win Rate | 0.0% |
| Total Return | 0.0% |
| Max Drawdown | 0.0% |
