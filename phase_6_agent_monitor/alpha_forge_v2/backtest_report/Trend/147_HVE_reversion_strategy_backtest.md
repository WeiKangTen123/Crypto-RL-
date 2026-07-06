---
status: BAD
id: '147'
sharpe: 0.03
return: -2.4
mdd: 33.7
win_rate: 51.9
trades: 54
pf: 0.97
---
# Stage 03 Backtest Report: Strategy 147 (HVEStrategy)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe Ratio | 0.03 |
| Total Return | -2.4% |
| Max Drawdown (MDD) | 33.7% |
| Win Rate | 51.9% |
| Total Trades | 54 |
| Profit Factor (PF) | 0.97 |

## Stability & Robustness

### 1. Parameter Stability Test
- **Status**: **FAILED (Fragile Peak)**
- **Detail**: Perturbing key parameters by ±10% resulted in significant performance degradation:
  - `dc_period` (13) perturbed to 12.0: Sharpe dropped to **-0.280**
  - `dc_period` (13) perturbed to 14.0: Sharpe dropped to **-0.100**
  - `vrsi_period` (10) perturbed to 9.0: Sharpe dropped to **-0.650**
  - `vrsi_period` (10) perturbed to 11.0: Sharpe dropped to **-0.180**
  - `vrsi_thresh` (30.6496) perturbed to 27.5846: Sharpe dropped to **-0.070**
  - `vrsi_thresh` (30.6496) perturbed to 33.7146: Sharpe dropped to **-0.080**
- **Verdict**: The parameter space is extremely narrow and fragile. The strategy exhibits overfitted characteristics around the baseline configuration.

### 2. Cross-Asset Stress Test
- **Status**: **FAILED (No Global Validity)**
- **ETH/4h**: Sharpe **-0.370** | Trades: 53 | Return: -15.1%
- **BTC/4h**: Sharpe **-0.130** | Trades: 59 | Return: -5.8%
- **Verdict**: The alpha factor fails to generalise. It performs negatively on both major assets (BTC and ETH), proving it lacks robust cross-asset validity.

## Expert Commentary

### 1. Trade Character
The strategy relies on a combination of Donchian Channels (DC), Volatility Z-Score, and Volume RSI (VRSI). With a win rate of 51.9% but a profit factor of 0.97, the strategy suffers from a negative skew—average losses are larger than average wins. The trade distribution suggests it frequently enters mean-reversion trades on short-term exhaustion signals that then get overrun by strong trend continuations.

### 2. Chop Warnings
Under sideways or low-volatility regimes, the Volatility Z-score filter prevents over-trading, keeping the total trade count low (54 trades over 3 years). However, during range extensions or transition regimes, the strategy gets chopped repeatedly as it fails to distinguish between true volatility-driven break-outs and temporary noise spikes.

### 3. Hypothesis Alignment
The Researcher's hypothesis assumed that volatility-adjusted Volume RSI would identify high-probability exhaustion extremes on SOL. While the VRSI threshold successfully triggered trades, the lack of a macro-trend or trend-regime filter (e.g. EMA trend gate) meant the strategy was constantly buying into falling knives or shorting strong momentum expansions, resulting in a flat-to-negative equity curve (Total Return of -2.4%). To make this factor class viable, structural entry filters (such as ADX or high-timeframe EMA direction) must be added.
