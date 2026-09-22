# Strategy 199: Volume-Close Anti-Momentum (Alpha #12) Backtest Report

## 1. Strategy Overview
- **Name**: Volume-Close Anti-Momentum
- **Logic**: Implements WorldQuant Alpha #12: `sign(delta(vol,1)) * (-delta(close,1))`. This logic fades the price move when there is a volume surge. A volume surge and price drop gives a positive score (long signal), while a volume drop and price rise gives a negative score (short signal). The alpha is scored and ranked cross-sectionally. We long the top asset and short the bottom asset in a portfolio setup.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `smoothing_period`: 3
- `sl_pct`: 0.05
- `tp_pct`: 0.10
- `risk_per_trade`: 5%

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.32`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The initial baseline produced a negative Sharpe out of the box (`-0.32`).
- As we saw with Alpha #42, crypto trends rather than mean-reverts during extreme volume spikes. Fading strong volume-backed price moves often results in fading strong trends (which is a losing proposition).
- **Optuna Tuning Results**: After running 100 trials, the Optuna tuner improved the Sharpe ratio to `-0.11` (Return: `-9.1%`, Trades: `1087`).
- **Tuned Parameters**: `{'smoothing_period': 5, 'sl_pct': 0.03, 'tp_pct': 0.1}`
- The optimizer was unable to squeeze out a positive Sharpe ratio while the logic strictly acts as an anti-momentum signal. It confirms the thesis that volume-backed price spikes are trending signals in crypto. Flipping the entry signals (buying momentum instead of fading it) would likely perform much better.
