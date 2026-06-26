## Strategy Name
Donchian Channel Breakout

## Category
Trend Following

## Core Hypothesis — WHY should this strategy have an edge?
BTC price action is often driven by "liquidation cascades" and momentum-chasing. When price breaks out of a multi-day range (the Donchian Channel), it often indicates a fundamental shift in supply/demand or the triggering of a massive cluster of stop-losses/liquidations, leading to a sustained trend extension.

## Entry Signal — exact condition that triggers a buy
1. **Breakout:** Price reaches and closes above the Upper Band of the N-period Donchian Channel (Standard N=20).
2. **Volume Confirmation:** (Optional but recommended) Breakout occurs on above-average trading volume.

## Exit Signal — exact condition that triggers a sell or position close
1. **Mean Reversion Exit:** Price touches or closes below the Middle Line (Median) of the Donchian Channel.
2. **Trend Reversal Exit:** Price touches the Lower Band of the Donchian Channel (Classic Turtle approach).

## Key Indicators / Data Required
- OHLCV Data
- Donchian Channels (N=20 for swing or N=55 for position trading)

## Timeframe Compatibility (scalp / swing / position)
- **Position:** Daily (1D) or Weekly (1W) charts.
- **Swing:** 4H chart.

## Theoretical Risk — what market conditions break this strategy?
- **False Breakouts (Fakeouts):** BTC often "wicks" above a resistance level to grab liquidity before reversing back into the range.
- **Low Volatility Regimes:** In a low-volatility "crab" market, the bands tighten and trigger entries that have no follow-through.

## Source — URL or reference
https://trendspider.com/learning-center/donchian-channels-explained/

## Interest Rating — [Medium] with one-line reason
Medium - Robust and historically proven, but requires sophisticated "close-only" validation to filter out BTC's aggressive stop-hunting wicks.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/Donchian_Channel]]
