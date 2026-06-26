# Hypothesis Report: Hammer Volume Exhaustion Reversion (HVE)

## 1. Mathematical Formulation
- **Extension**: `Close_t <= LowerDonchian_20,t`
- **Exhaustion**: `VRSI_14,t < 25`
- **Pattern**: `IsHammer_t == True`
- **Exit**: Target = `MidDonchian_20,t`, SL = `Low_t - (Low_t * 0.01)`

## 2. Expected Performance Envelope
- **Sharpe Ratio**: Target 1.2 - 1.4
- **Max Drawdown**: Target ~20%
- **Monthly ROI**: Target 2.0% - 2.5%
- **Trade Frequency**: Swing 4H (approx. 1 trade every 2-3 days)

## 3. Rationale
Cryptocurrency markets frequently experience cascading liquidations followed by sharp V-shaped bounces. The strict criteria (Donchian lower band + VRSI < 25 + Hammer) ensures we only enter when Price Extreme, Volume Exhaustion, and Price Action Reversal align.
