---
status: BAD
id: "67"
sharpe: -0.3
return: -88.9
mdd: 96.3
win_rate: 25.1
trades: 510
pf: 0.68
---
# Stage 03 Backtest Report: T3NexusStiffStrategy (ID: 67)

## Performance Table
| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | -0.30 |
| **Total Return** | -88.9% |
| **Max Drawdown (MDD)** | 96.3% |
| **Win Rate** | 25.1% |
| **Total Trades** | 510 |
| **Profit Factor (PF)** | 0.68 |

## Stability & Robustness

### 1. Parameter Stability Test (±10% perturbations)
The strategy was subjected to sensitivity analysis across its 10 tunable parameters. It exhibits extreme performance weakness:
- **`t3_length`**: Varying from 32 to 29 (Sharpe = `-0.17`) or 35 (Sharpe = `-0.14`).
- **`t3_vf`**: Varying from 0.937 to 0.8433 crashes Sharpe to `-0.58`. Increasing to 1.0307 yields Sharpe of `0.06`.
- **`wae_sensitivity`**: Varying to 225 or 275 keeps Sharpe at `-0.30`.
- **`wae_fast_len`**: Varying fast period to 9 drops Sharpe to `-0.35`.
- **`wae_slow_len`**: Varying to 54 drops Sharpe to `-0.36`.
- **`stiff_len`**: Increasing from 37 to 41 drops Sharpe significantly to `-0.79`.
- **`stiff_threshold`**: Decreasing from 0.9263 to 0.8337 crashes Sharpe to `-0.82`.

> [!WARNING]
> **Severe Downward Sensitivity**: Perturbing parameter values like `stiff_len` or `stiff_threshold` causes the Sharpe ratio to drop even deeper to `-0.79` and `-0.82`, showing that the strategy's current configuration is highly fragile and vulnerable to parameter shifts.

### 2. Cross-Asset Stress Test
The strategy was tested on secondary assets:
- **ETH/1h**: Sharpe Ratio = `-0.54` | Return = `-99.25%` | MDD = `99.49%` | Trades = 519
- **BTC/1h**: Sharpe Ratio = `-0.30` | Return = `-88.89%` | MDD = `96.34%` | Trades = 510

> [!CAUTION]
> **Cross-Asset Catastrophe**: The strategy is globally unprofitable. On ETH, it produces near-total liquidation (-99.25% return) with a Sharpe of -0.54, demonstrating that the underlying momentum-detection logic does not possess any global asset edge.

### 3. Hypothesis Verification
- **Hypothesis**: T3 Tillson moving average combined with Waddah Attar momentum explosion and the Stiffness indicator can identify and profitably exploit strong trending regimes on the 1h timeframe.
- **Verification**: The backtest results **disprove** the hypothesis. The strategy is unprofitable across both BTC (-0.30 Sharpe) and ETH (-0.54 Sharpe) over the multi-year backtest period. The high drawdown (96.3% on BTC, 99.5% on ETH) confirms that the lagging nature of the T3 Nexus and Stiffness indicators leads to entry signals at local trend peaks, followed by catastrophic failures to exit.

---

## Expert Commentary

### Trade Character
With 510 trades on the 1h timeframe, the strategy has high activity but suffers from a "death by a thousand cuts" trade character. It features a very low win rate (25.1%) and a profit factor of 0.68. It routinely stays in positions through massive adverse price movements, causing extreme drawdown profiles that render it completely undeployable.

### Chop Warnings
The Waddah Attar Explosion deadzone filter (`wae_deadzone` = 14) is insufficient. In choppy and sideways consolidation zones, the strategy gets repeatedly stopped out, entering false breakouts. The Stiffness indicator fails to differentiate between high-volatility range expansions and sustainable trend momentum, resulting in frequent whipsaws.

### Hypothesis Alignment
The strategy's failure to capture real trend alphas points to a fundamental flaw: MACD-based WAE signals combined with moving average stiffness suffer from lag that offsets any potential trend-following edge. Rather than capturing explosive moves early, it enters late and remains exposed to reversals. Structural redesign is required before any further parameter optimization.
