# Volume-Price Correlation Extremas

## Core Mathematical Concept
A formulaic alpha factor extracted via Agentic Alpha Mining frameworks designed to handle heavy-tailed crypto data.
The factor identifies extreme negative or positive correlations between high price and volume over a rolling window.

**Base Math:**
`Alpha = S_log1p(ts_min(ts_corr(high, volume, Window_1), Window_2))`
*Where `S_log1p` is a signed log1p transformation to normalize heavy-tailed distributions.*

## Institutional Guards
- **Data Quality Constraint:** Memory logs indicate widespread stale data and anomalies across lower timeframes for major pairs (BTC, ETH, BNB, SOL, XRP). This factor MUST strictly be tested on robust timeframes (4h primary, 1h secondary) and avoid the compromised lower TFs.
- **Poison Control:** Uncorrelated out-of-sample data might trigger false positives. Must be coupled with a market regime filter.
- **Library-First Mandate:** The mathematical functions `ts_corr`, `ts_min`, and `S_log1p` must be implemented as pure, isolated functions in `strategy_backtest/library.py`.

## Strategy Play Style
- **Momentum Continuation:** Capitalizes on momentum bursts where high volume confirms price action, jumping into trend continuations.
- **Reversion on Extremes:** When extreme negative correlations occur during high volume, it signals capitulation or blow-off tops, triggering counter-trend positioning.

## Strategic Disadvantages
- **Whipsaw Vulnerability:** Sensitive to low-volume spikes or fakeouts during low-liquidity market hours.
- **Data Sensitivity:** The rolling correlation calculation requires highly consistent volume data; any missing bars will significantly skew the window.
- **Overfitting Risk:** Derived from formulaic tree searches, this factor is susceptible to overfitting if not strictly validated via 4-Window WFO and Out-of-Sample testing.

## Enhancement Recommendations
- **Regime Filter Integration:** Combine with a Volatility Regime filter (e.g., ATR percentile) to only activate trades when overall market volatility is structurally sound.
- **Cross-Sectional Z-Score:** Instead of trading on absolute alpha values, normalize the output cross-sectionally against a basket of assets to capture relative momentum.
- **Developer Logic Switches:** Add built-in developer logic switches to toggle between Momentum-following (positive correlation) and Mean-Reversion (negative correlation extremas).