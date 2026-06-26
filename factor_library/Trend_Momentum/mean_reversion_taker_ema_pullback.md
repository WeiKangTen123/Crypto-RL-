## Strategy Name
The "Taker-EMA" Pullback

## Category
Mean Reversion / Pullback

## Core Hypothesis — WHY should this strategy have an edge?
BTC often experiences "liquidity hunt" pullbacks during strong trends. Traditional traders often get stopped out when price touches a key moving average like the 50 EMA. This strategy gains an edge by using `taker_buy_base_vol`. If the taker-buy ratio remains > 52% during a price drop to the EMA, it indicates that "aggressive" buyers are still absorbing every available offer, suggesting the pullback is a temporary lack of sell-side liquidity rather than a trend shift.

## Entry Signal — exact condition that triggers a buy
1. **Trend Context:** Price must be above the 200 EMA (Bullish Macro).
2. **Setup:** Price pulls back to touch the 50 EMA on the 15m timeframe.
3. **Aggressive Support Filter:** During the pullback candles (at least 2 candles), the average `taker_buy_base_vol / total_volume` ratio must be >= 52%.
4. **Trigger:** A bullish engulfing or pin-bar candle close on the 50 EMA.

## Exit Signal — exact condition that triggers a sell or position close
1. **Stop Loss:** Close below the 50 EMA by more than 0.5% or below the recent swing low.
2. **Take Profit:** Exit at the previous local high (pre-pullback peak) or 1.5:1 RR.

## Key Indicators / Data Required
- 15m OHLCV Data
- `taker_buy_base_vol` (Taker Buy Volume)
- `volume` (Total Volume)
- 50 EMA and 200 EMA

## Timeframe Compatibility (scalp / swing / position)
- **Scalp/Day Trade:** 15m (Primary)
- **Micro:** 5m (Requires higher taker ratio threshold like 54%)

## Theoretical Risk — what market conditions break this strategy?
- **Flash Crashes:** Extreme sell-side pressure can overwhelm taker buyers, leading to a "knife catch" scenario.
- **Taker Deception:** In very low volume environments, a few large taker orders can skew the ratio without representing broad market consensus.

## Source — URL or reference
Internal Research - Order Flow + Moving Average Synergy

## Interest Rating — [High] with one-line reason
High - Directly maps "aggression" onto technical support levels, filtering for "high-conviction" dip-buying opportunities.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/Order_Flow]]
