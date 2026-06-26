## Strategy Name
Volume-Weighted Mean Reversion (V-RSI)

## Category
Mean Reversion

## Core Hypothesis — WHY should this strategy have an edge?
Standard RSI treats all price changes equally, regardless of the volume behind them. However, in HFT environments, a price move on high volume is much more significant than a move on low volume. A **Volume-Weighted RSI (V-RSI)** gives more weight to high-volume "exhaustion" moves. When the V-RSI hits an extreme, it indicates that a massive amount of volume has been pushed in one direction in a short time, which often leads to temporary liquidity exhaustion and a "snap-back" mean reversion towards the VWAP or a moving average.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Calculate **V-RSI** (14-period):
   - $U = \text{volume} \times \max(0, \text{Close} - \text{Close}_{prev})$
   - $D = \text{volume} \times \max(0, \text{Close}_{prev} - \text{Close})$
   - $RS = \text{SMA}(U, 14) / \text{SMA}(D, 14)$
   - $V\text{-}RSI = 100 - [100 / (1 + RS)]$
2. Trigger long when **V-RSI < 20** (Oversold extreme).
3. Confirm with price being at least 1.5 standard deviations below the VWAP.

**Short Entry:**
1. Trigger short when **V-RSI > 80** (Overbought extreme).
2. Confirm with price being at least 1.5 standard deviations above the VWAP.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Price returns to the **VWAP** (Volume-Weighted Average Price).
- Or V-RSI crosses back over the 50 level.

**Stop Loss:**
- Fixed stop at 0.4% or 2.5 standard deviations from VWAP.
- Exit if V-RSI continues to stay at the extreme (>90 or <10) for more than 3 candles (indicating a trend transition instead of a reversal).

## Key Indicators / Data Required
- `volume` (Total volume).
- `close` (Price).
- `high`, `low` (For VWAP calculation).
- VWAP (Volume-Weighted Average Price).
- V-RSI (Volume-Weighted Relative Strength Index).

## Timeframe Compatibility (scalp / swing / position)
Scalp (1m, 5m, or 15m timeframes).

## Theoretical Risk — what market conditions break this strategy?
- **Strong Trends:** In a strong trend (parabolic move), V-RSI can stay overbought/oversold for a long time as new volume keeps pushing the trend.
- **Low Volume Liquidity Gaps:** If volume is too low, the weighting becomes erratic.
- **Flash Crashes:** Extreme volume on a crash might not lead to an immediate recovery but rather a period of consolidation or further downside.

## Source — URL or reference
- "Technical Analysis of Stocks & Commodities" magazine (Articles on Volume-Weighted Indicators).
- TradingView Community (Volume-Weighted RSI scripts).
- QuantConnect (Mean Reversion using VWAP and Volume).

## Interest Rating — [Medium]
Medium — While logically sound, mean reversion in crypto can be dangerous during parabolic phases; requires tight risk management.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]] · [[_Concepts/SMA]] · [[_Concepts/VWAP]]
