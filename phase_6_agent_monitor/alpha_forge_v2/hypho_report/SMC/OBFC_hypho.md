# Hypothesis Report: Order Block Mitigation with Fisher Confirmation (OBFC)

## 1. Mathematical Formulation
- **Zone**: `Signal_OB,t == 1` (Bullish OB touch)
- **Momentum Shift**: `Fisher_10,t > FisherTrigger_10,t` within `[t, t+2]` of OB touch.
- **Filter**: `EMA_200,t > EMA_200,t-1`
- **Exit**: TP = Entry + `3 * ATR_14`, SL = Min(OB_Low) - `0.5 * ATR_14`

## 2. Expected Performance Envelope
- **Sharpe Ratio**: Target 1.5+
- **Max Drawdown**: Target ~15%
- **Monthly ROI**: Target 2.5% - 3.0%
- **Trade Frequency**: Swing 4H (approx. 1 trade every 2-3 days)

## 3. Rationale
The strategy aims to buy institutional pullbacks. Waiting for the Fisher Transform to cross ensures that the buying momentum has actually resumed before committing capital, lowering the drawdown and maximizing the Sharpe Ratio.
