---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: basis-mean-reversion
source: Alpha Researcher (Priority Queue)
status: IMPLEMENTED
tags:
- research
- arbitrage
- implemented
timeframes: 4h
type: mean-reversion
---
# Basis Mean Reversion (Spot-Perp Spread)

## Concept
The "Basis" is the difference between the Spot price and the Perpetual Futures price. In a bull market, Perps usually trade at a premium (Positive Basis). In a bear market or during panic, they can trade at a discount (Negative Basis). This strategy bets that extreme basis spreads will eventually return to the mean.

## Math/Logic
1. **Basis Calculation**: `Basis = Perp_Price - Spot_Price`.
2. **Normalized Basis (Z-Score)**: 
   - `Rolling_Mean = SMA(Basis, 20)`
   - `Rolling_Std = STD(Basis, 20)`
   - `Basis_Z = (Basis - Rolling_Mean) / Rolling_Std`
3. **Signals**:
   - `Long`: Basis_Z < -2.0 (Perp is significantly cheaper than Spot).
   - `Short`: Basis_Z > 2.0 (Perp is significantly more expensive than Spot).

## Market Regime Notes
Best in high-volatility environments where funding rates are spiking or diving.

---
## Connections
**Category:** [[Basis_Arb/_Index]]
