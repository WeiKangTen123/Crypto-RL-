# Backtest Report: 237_ExtremeNestedDecay

## 1. Strategy Identity
- **ID:** `237`
- **Class:** `ExtremeNestedDecay`
- **Type:** "HARD" WorldQuant Alpha 29
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `min(rank(log(ts_min(rank(-rank(delta(close, 5))), 2))), rank(decay_linear(rank(-returns), 5)))`
- **The Left Constraint:** Calculates a 5-period momentum fade. Crucially, it then uses `ts_min(..., 2)`, which forces the fade to be consistently strong over the last 2 periods. It essentially asks: "Has the medium-term momentum been persistently oversold?"
- **The Right Constraint:** Calculates a 1-period momentum fade and smooths it using a 5-period linear decay.
- **The Synthesis (Logic Gate):** By wrapping both entirely separate ranking processes inside a `min()` function, it acts as a boolean `AND` gate. A trade will *only* be triggered if the coin is extremely oversold on *both* the medium-term persistent timescale *AND* the short-term decayed timescale relative to the rest of the market.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values. (NOTE: The 3% Stop-Loss option was explicitly banned from the tuner to prevent the AI from overfitting to noise, giving this highly constrained setup room to breathe).

## 4. Analysis and Next Steps
- **Optuna Tuning Results:** FAILED. The optimizer could not find a single profitable parameter combination across 175 trials. The best it could do was a `-0.1` Sharpe Ratio and `-31.3%` Return.
- **Autopsy Report (GRAVEYARD):** By banning the 3% noise-scalp stop loss, we forced the strategy to prove its structural edge. It completely failed. A strict boolean intersection of a 5-period persistent fade and a 1-period decayed fade is disastrous on a 4-hour crypto timeframe. It simply waits until an asset is completely dead (falling knife on both long and short timescales) and then buys it right before it drops further. 
- **Verdict:** EXILED TO GRAVEYARD. (Graded BAD).
