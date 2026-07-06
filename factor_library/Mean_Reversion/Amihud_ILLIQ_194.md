---
name: Amihud ILLIQ Mean-Reversion
strategy_id: 194
type: short-term
factor_class: Mean-Reversion
directional_bias: Symmetric
optimal_regime: Ranging
timeframes: [1h, 4h, 1d]
coins: [BTC, ETH, SOL]
source: 6890659
interest: High
status: QUEUED
sharpe: 0.0
win_rate: 0.0
total_return: 0.0
max_drawdown: 0.0
tags: [alpha, factor, Mean-Reversion]
---

# Amihud ILLIQ Mean-Reversion

## Concept
The Amihud Illiquidity ratio (ILLIQ) measures the price impact of a trading volume. In cryptocurrency, periods of extreme illiquidity often reflect temporary market exhaustion or liquidity voids, which frequently precede sharp mean-reversion price movements as market makers and large participants re-liquify the order book.

## Agent Reasoning (Chain of Thought)
This factor utilizes the Amihud ILLIQ metric (absolute return/volume) to quantify market impact. By normalizing this via a rolling Z-score, we identify statistically significant liquidity anomalies. Given crypto's microstructure, this is highly effective for identifying 'exhaustion' points after which price tends to snap back to equilibrium.

## Market Regime
- **Works best in**: Ranging / Post-liquidation recovery
- **Breaks down in**: Strong directional trend / Low-liquidity hours (00:00–04:00 UTC)
- **Suggested regime filter**: ADX(14) < 25

## Entry Logic
- **Long**: ILLIQ Z-score > 2.0 (High illiquidity, bearish exhaustion) AND Price < Mean(20)
- **Short**: ILLIQ Z-score < -2.0 (High liquidity, bullish overextension) AND Price > Mean(20)

## Exit Logic
- **Take Profit**: ILLIQ Z-score returns to 0
- **Stop Loss**: 1.5× ATR from entry
- **Default R:R**: 2:1

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute indicators
illiq = abs(df['Close'].pct_change()) / df['Volume']
z_illiq = (illiq - rolling_mean(illiq, 20)) / rolling_std(illiq, 20)

# Step 2 — Entry
long_signal  = (z_illiq > 2.0)
short_signal = (z_illiq < -2.0)
```

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| ILLIQ | period=20 | Custom implementation |
| Z-Score | period=20 | `calc_zscore(series, 20)` |

## Recommended Logic Switches (For @alpha-developer)
- `entry_filter`: ['NONE', 'ADX_BELOW_25']
- `exit_mode`: ['Z_RETURN', 'FIXED_ATR']

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
