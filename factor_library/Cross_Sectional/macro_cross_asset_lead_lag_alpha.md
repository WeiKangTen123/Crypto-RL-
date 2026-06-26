## Strategy Name
Cross-Asset Lead-Lag Alpha

## Category
Macro

## Core Hypothesis — WHY should this strategy have an edge?
Bitcoin is increasingly integrated into the global macro landscape. During periods of high institutional activity—specifically the New York session open (8:30 - 9:30 AM EST)—BTC often responds to shifts in the US Dollar Index (DXY) and S&P 500 (SPY) with a slight lag (15-60 minutes). By identifying a confirmed trend in macro assets that hasn't yet been priced into BTC, a DRL agent can front-run the eventual correlation-driven move. This "lead-lag" effect is most pronounced when macro volatility is high, providing a "direction filter" for the daily trend.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Time: 9:30 AM - 10:30 AM EST (First hour of NY equity open).
2. DXY (US Dollar Index) is down > 0.2% on the 1h candle.
3. SPY (S&P 500) is up > 0.2% on the 1h candle.
4. BTC has NOT yet broken its previous 4-hour high.
5. **Action:** Go Long on BTC expecting a catch-up move.

**Short Entry:**
1. Time: 9:30 AM - 10:30 AM EST.
2. DXY is up > 0.2% on the 1h candle.
3. SPY is down > 0.2% on the 1h candle.
4. BTC has NOT yet broken its previous 4-hour low.
5. **Action:** Go Short on BTC.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- End of the New York session (4:00 PM EST).
- Or a fixed Risk:Reward ratio of 1:3.

**Stop Loss:**
- BTC breaks the low/high of the 8:30 AM - 9:30 AM EST "Macro Lead" candle.
- Or if DXY/SPY correlation flips (e.g., DXY starts rallying after the entry).

## Key Indicators / Data Required
- `DXY_close` (1h timeframe).
- `SPY_close` (1h timeframe).
- `BTC_close` (1h/4h timeframe).
- Server Time (to filter for NY open).

## Timeframe Compatibility (scalp / swing / position)
Day Trade / Swing (1h entry, held for hours).

## Theoretical Risk — what market conditions break this strategy?
- **Decoupling Events:** Crypto-specific news (e.g., exchange hacks, regulatory news) can cause BTC to decouple completely from macro assets.
- **FOMC/CPI Days:** During major economic releases, volatility is so high that lead-lag relationships can flip instantly or become "noise."
- **Low Volatility Regimes:** In "crab" markets, macro moves may be too small to trigger a meaningful lag response in BTC.

## Source — URL or reference
- "Intermarket Analysis" by John J. Murphy.
- Research on "Cross-Asset Contagion and Lead-Lag Relationships" (Quantitative Finance journals).

## Interest Rating — [Medium-High]
Medium-High — Essential for DRL agents to understand the "Environment" they are trading in; macro assets provide the "wind" at the agent's back.

---
## Connections

**Category:** [[Cross_Sectional/_Index]]
