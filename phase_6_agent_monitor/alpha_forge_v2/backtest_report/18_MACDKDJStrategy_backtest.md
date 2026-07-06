---
status: MEDIOCRE
id: 18
sharpe: 0.77
return: 127.23
mdd: 23.64
win_rate: 43.59
trades: 195
pf: 1.34
---
# Stage 03 Backtest Report: MACDKDJStrategy (ID 18)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe Ratio | 0.77 |
| Total Return | 127.23% |
| Max Drawdown (MDD) | 23.64% |
| Win Rate | 43.59% |
| Total Trades | 195 |
| Profit Factor | 1.34 |

## Stability & Robustness

### 1. Parameter Stability Test (FAILED)
The strategy was subjected to +/-10% perturbations on key parameters. Significant sensitivity was found on KDJ period:
- **macd_fast** (18): 16.0 -> Sharpe 0.80 | 20.0 -> Sharpe 0.69 (Stable)
- **macd_slow** (28): 25.0 -> Sharpe 0.70 | 31.0 -> Sharpe 0.57 (Stable)
- **macd_signal** (16): 14.0 -> Sharpe 0.79 | 18.0 -> Sharpe 0.53 (Stable)
- **kdj_period** (28): 25.0 -> Sharpe 0.27 | 31.0 -> Sharpe -0.05 (CRITICAL DROPOUT)
- **kdj_oversold** (38) & **kdj_overbought** (89): High stability observed across bounds.
- **stop_loss_pct** (0.0957) & **take_profit_pct** (0.0822): High stability observed.

> [!WARNING]
> The strategy exhibits high fragility around its `kdj_period` parameter. A slight shift from 28 to 31 drops the Sharpe ratio to -0.05. This indicates a fragile peak in parameter space.

### 2. Cross-Asset Stress Test (FAILED)
The optimized parameters were validated on secondary assets under the same settings (4h timeframe, 2021-01-01 to 2026-05-31):
- **ETH/4h**: Sharpe 0.11 | 185 Trades | Return -0.75% | MDD 38.05%
- **BTC/4h**: Sharpe 0.02 | 186 Trades | Return -10.34% | MDD 32.92%

> [!IMPORTANT]
> The strategy fails to show global asset validity. Performance on BTC and ETH is near break-even or negative, indicating that the parameters are highly overfit to BNB's unique asset dynamics.

## Expert Commentary

### Trade Character
MACDKDJStrategy operates as a medium-frequency swing strategy on the 4h timeframe. With a win rate of 43.59%, its profitability depends on catching longer-term trend movements on BNB where the average winning trade size offsets small choppy losses.

### Chop Warnings
During periods of market consolidation, KDJ overlays trigger early entries on false pullbacks, while MACD is prone to whipsawing. The KDJ period sensitivity confirms that the filter is narrow and susceptible to market noise when the regime shifts from trending to choppy.

### Hypothesis Alignment
The core hypothesis was that KDJ would filter out bad entries during strong trends identified by MACD. While this is successful on BNB, the complete lack of profitability on BTC and ETH, combined with the fragile KDJ period setting, indicates that the optimized setup captures a narrow, BNB-specific historical artifact rather than a robust, generalizable market edge.
