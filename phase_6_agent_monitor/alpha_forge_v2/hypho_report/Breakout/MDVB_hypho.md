# Hypothesis Report: McGinley Dynamic Volume Breakout (MDVB)

## 1. Mathematical Formulation
- **Trend**: `Close_t > McGinley_50,t`
- **Noise Filter**: `CHOP_14,t < 38.2`
- **Entry**: `VRSI_14,t` crosses above 50.
- **Exit**: `Close_t < McGinley_20,t`

## 2. Expected Performance Envelope
- **Sharpe Ratio**: Target 1.4+
- **Max Drawdown**: Target ~18%
- **Monthly ROI**: Target 2.5%
- **Trade Frequency**: Swing 4H (approx. 1 trade every 2-3 days)

## 3. Rationale
The McGinley Dynamic adapts to market speed, preventing the classic moving average whipsaw. The combination with VRSI ensures that breakouts are volume-backed, satisfying the MFT criteria on the 4H timeframe.
