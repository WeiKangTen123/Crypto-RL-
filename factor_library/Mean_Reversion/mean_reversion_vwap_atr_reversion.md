## Strategy Name
VWAP Mean Reversion with ATR Volatility Bands

## Category
Mean Reversion

## Core Hypothesis — WHY should this strategy have an edge?
BTC price exhibits a strong tendency to return to its Volume Weighted Average Price (VWAP) during periods of non-trending volatility. VWAP represents the "fair value" or equilibrium price where the most volume has occurred for the day. When price deviates significantly from this mean (measured by ATR-based volatility bands), it reaches a point of exhaustion where "retail" participants are overextended and "smart money" looks to mean-revert the price back to the volume-heavy equilibrium. The edge lies in exploiting the predictable pull of liquidity back to high-volume nodes.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Timeframe: 30m or 1h.
2. Price must touch or close below the **Lower ATR Band** (Calculation: `VWAP - (Multiplier * ATR(14))`). Multiplier set to 2.5.
3. **Confirmation:** Bullish Reversal Candle (Hammer or Bullish Engulfing) occurs on the touch or immediately after.
4. **Volume Filter:** Volume on the touch candle must be lower than the previous 3 candles (indicating exhaustion).
5. **Entry:** Market buy on the close of the confirmation candle.

**Short Entry:**
1. Timeframe: 30m or 1h.
2. Price must touch or close above the **Upper ATR Band** (Calculation: `VWAP + (Multiplier * ATR(14))`). Multiplier set to 2.5.
3. **Confirmation:** Bearish Reversal Candle (Shooting Star or Bearish Engulfing) occurs on the touch or immediately after.
4. **Volume Filter:** Volume on the touch candle must be lower than the previous 3 candles (indicating exhaustion).
5. **Entry:** Market sell on the close of the confirmation candle.

## Exit Signal — exact condition that triggers a sell or position close
**Take Profit (TP):**
- Primary Target: Exit 100% of position when price touches the **VWAP** line.

**Stop Loss (SL):**
- Hard Stop: 1.5 * ATR(14) from the entry price.
- Time-based Exit: If price has not reached VWAP within 12 candles (6 hours on 30m, 12 hours on 1h), close at market to avoid trend-following risk.

## Key Indicators / Data Required
- **Price Data:** OHLCV (30m or 1h).
- **VWAP:** Standard daily-reset VWAP (Volume Weighted Average Price).
- **ATR (Average True Range):** 14-period ATR for band calculation and stop loss.
- **Volume:** Used for exhaustion filtering.

## Timeframe Compatibility (scalp / swing / position)
- **Scalp / Day Trade:** Highly compatible with 30m and 1h timeframes for intraday mean reversion.

## Theoretical Risk — what market conditions break this strategy?
This strategy fails during **strong trending regimes** or **momentum breakouts** (e.g., God candles, major news events). If BTC enters a "Trend-from-Open" day where it pushes beyond the ATR bands and stays there (pinning the bands), the strategy will suffer losses. 

**Drawdown Management (20-28% Target):**
The drawdown limit is strictly maintained through:
1. **ATR-Based Stops:** Prevents catastrophic loss on single trending moves by sizing the stop relative to current volatility.
2. **Fixed Risk-Per-Trade:** Maximum 1.5% of equity risked per trade.
3. **Time-Based Exit:** Prevents "holding and hoping" during a slow-bleed trend against the position.
4. **Regime Filter:** Strategy is deactivated if the 200-period EMA slope is $> 30$ degrees, indicating a strong trend where mean reversion is unlikely.

## Source — URL or reference
Practitioner standard for intraday BTC trading; similar to concepts discussed in "Trading with Intermarket Analysis" by John Murphy and various algorithmic mean-reversion implementations on TradingView (e.g., "VWAP with ATR Bands" scripts).

## Interest Rating — [High]
Mean reversion around VWAP is one of the most reliable intraday signals for BTC; when combined with ATR bands, it provides clear, non-discretionary entries that are ideal for DRL reward shaping.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/VWAP]]
