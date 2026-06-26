# Institutional Pairs Trading Blueprint: Cointegration, Execution & Analytics

## 1. Strategy Overview
Pairs trading is a quantitative, market-neutral strategy designed to capture alpha from the statistical mispricing between two closely related assets. By betting on the mean-reversion of a cointegrated spread, the strategy hedges out broader market beta. When executed in cryptocurrency markets (e.g., trading the spread between **ETH** and **AAVE**), this approach isolates the relative valuation decoupling while remaining immune to macro directional crashes.

## 2. The Mathematical Pipeline (Core Indicators)
The "indicators" are pure statistical calculations computed on a rolling basis via Python libraries like `statsmodels` and `pandas`:

1.  **Hedge Ratio ($\beta$):** Calculated via Ordinary Least Squares (OLS) regression to find exactly how much of Asset B is needed to hedge Asset A.
    * **Formula:** $\log(P_{A,t}) = \alpha + \beta \log(P_{B,t}) + \epsilon_t$
2.  **Verify Stationarity (ADF Test):** The residual spread ($\epsilon_t$) must be tested using the Augmented Dickey-Fuller (ADF) test. A p-value < 0.05 confirms statistical stationarity.
3.  **Standardize the Spread (Z-Score):** The algorithm normalizes the residual spread into a rolling Z-score:
    * **Formula:** $Z_t = \frac{\epsilon_t - \mu}{\sigma}$

## 3. Dynamic Thresholds & Execution Logic
While retail systems use hard static bands (e.g., $\pm2.0$), institutional systems adapt to structural regime shifts using dynamic thresholds. By applying rolling Bollinger Bands directly to the Z-score of the spread, the entry parameters expand during high-volatility events to avoid premature execution.

* **Shorting the Spread (Z crosses Upper Dynamic Band):** Asset A is statistically overvalued.
    * *Action:* Sell short Asset A, simultaneously Buy long Asset B.
* **Longing the Spread (Z crosses Lower Dynamic Band):** Asset A is statistically undervalued.
    * *Action:* Buy long Asset A, simultaneously Sell short Asset B.
* **The Exit Signal ($Z \approx 0.0$):** The assets have returned to their historical equilibrium.
    * *Action:* Close both legs simultaneously.

## 4. The Half-Life of Mean Reversion (Time-Based Exits)
Not all stationary series revert at the same speed. The algorithm must calculate the **Half-Life** of the spread, derived from the Ornstein-Uhlenbeck process.
* **Application:** This calculation tells the execution engine exactly how many periods a trade *should* take to revert. If a trade remains open past its historical half-life without reverting to the mean, it triggers a strict **time-based stop loss** to free up capital and prevent holding a permanently decoupling pair.

## 5. Advanced Trade Analytics (MFE & MAE)
Evaluating the backtest solely on terminal PnL masks execution inefficiencies. A professional backtesting engine logs the internal state of every trade using advanced excursion metrics. For deep analysis, implementing a tick-by-tick state playback (a "VCR" logic module) allows the quantitative analyst to visually replay trade lifecycle states.
* **Maximum Favorable Excursion (MFE):** Measures peak unrealized profit before the trade was closed. High MFE with low realized profit indicates the system is exiting too late and giving back spread convergence.
* **Maximum Adverse Excursion (MAE):** Measures peak unrealized loss during the trade. This dictates the optimal Z-score entry threshold and required margin to survive drawdown.

## 6. Transaction Cost Analysis (TCA) & Fee Drag
Pairs trading requires executing four distinct orders per cycle (Entry: 2 legs, Exit: 2 legs). 
* **Fee Impact:** If the target spread convergence is 1.2%, but round-trip taker fees and bid-ask slippage total 0.5%, nearly half the alpha is destroyed. The system must route orders logically—using limit orders (Maker rebates) on the less volatile leg and market orders (Taker fees) on the highly volatile leg to guarantee simultaneous fills.

## 7. Systematic Validation Architecture
Because crypto market regimes shift violently, cointegration can break. The backtesting infrastructure must utilize a strict **60/20/20 data split** to prevent curve-fitting, moving through three distinct phases:
* **Sniff Test (60% - In-Sample):** Formation period to calculate initial OLS, establish $\beta$, and pass the ADF test.
* **Robustness Test (20% - Out-of-Sample 1):** Validates the strategy under changing market conditions without optimizing parameters.
* **Stress Test (20% - Out-of-Sample 2):** Pure forward-walk simulation to measure max drawdown and edge decay.

## 8. Leverage & Capital Requirements
* **Leverage Profile:** Running **10x leverage** is mathematically viable because the market-neutral stance (long one coin, short the other) severely reduces the risk of liquidation from directional flash crashes.
* **Capital Sizing:** Requires cross-margin or portfolio-margin accounts on derivative exchanges (perpetual futures) to allow the unrealized profits of the winning leg to offset the unrealized losses of the losing leg.

## 9. Major Strategy Risks
1. **Cointegration Breakdown:** The fundamental relationship permanently decouples. Time-based stops (Half-Life) must catch this.
2. **Leg Risk (Slippage):** Failing to execute both legs at the exact same millisecond leaves the portfolio exposed to naked directional risk.
3. **Margin Squeeze:** The spread can widen significantly before it reverts. The 10x leveraged position must have enough free margin (modeled via MAE) to survive extreme Z-score deviations.