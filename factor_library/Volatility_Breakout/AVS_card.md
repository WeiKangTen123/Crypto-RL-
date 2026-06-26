---name: Adaptive Volatility Squeeze (AVS)
category: Volatility_Breakout
coins:
- BTC
- ETH
- BNB
- SOL
- XRP
timeframes:
- 4h
strategy_id: AVS_BTC_4H
status: VALIDATED
sharpe: 1.55
win_rate: 44.5
total_return: 211.56
max_drawdown: 17.84
---

## Strategy Play Style
Aggressive Volatility Breakout. This strategy thrives in market regimes transitioning from prolonged consolidation to new trend expansions. It's an MFT strategy designed to hold positions for multi-days.

## Strategic Disadvantages
Hostile in "choppy" high-volatility ranges where false breakouts occur repeatedly without a sustained follow-through.

## Enhancement Recommendations
- Add volume-exhaustion gating using `calc_vrsi` to filter out fakeouts.
- Implement walk-forward optimization to dynamically adjust the ADX threshold based on rolling 30-day volatility.

## Agent Reasoning (Chain of Thought)
- The user requested an MFT strategy for the `4h` timeframe with strict targets: 2-3% monthly ROI, ~25% MDD, and Sharpe 1.0-1.5.
- Our `LTM.md` specifically identified Volatility Squeezes as highly promising for crypto.
- By combining `calc_bb_kc_squeeze` with a regime filter `calc_adx < 25`, we ensure the squeeze happens in true consolidation.
- Using `calc_fisher_transform` as the directional trigger avoids the lag of moving averages, allowing us to capture the initial volatility expansion.
- `calc_chandelier_exit` provides the perfect trailing stop for multi-day crypto trends.


## Performance Summary
*Auto-updated by sync_backtest_to_obsidian.py when strategy_id matches.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 1.55 |
| Win Rate | 44.5% |
| Total Return | 211.56% |
| Max Drawdown | 17.84% |