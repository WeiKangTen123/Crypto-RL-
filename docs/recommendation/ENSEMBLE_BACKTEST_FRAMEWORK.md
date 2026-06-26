# Recommendation: Advanced Backtest Framework for Ensemble Strategies

## 1. The Challenge of "Ensemble Backtesting"
Backtesting a regime-switching ensemble is significantly more complex than a single strategy. The primary risk is **"Look-Ahead Bias"**—where the regime classifier accidentally uses future data to decide the current market state, leading to impossibly high returns that fail in real-time paper trading.

---

## 2. Recommended Validation Framework: "Sequential Walk-Forward"

Instead of a simple backtest, we recommend a **Three-Stage Validation Loop**:

### Stage 1: Regime Robustness Test
Before testing ROI, we must test the "Regime Classifier" alone.
*   **Metric**: "State Persistence."
*   **Goal**: Ensure the classifier doesn't switch states too frequently (e.g., every 5 minutes), which would drain the account through trading fees.
*   **Output**: A heatmap showing the percentage of time spent in each regime across 2023, 2024, 2025, and 2026.

### Stage 2: Purged Out-of-Sample (OOS) Backtest
To avoid overfitting, the backtest must be "Purged":
1.  **Train** the Regime Classifier on 2021–2022 data.
2.  **Test** on 2023.
3.  **Retrain** on 2021–2023.
4.  **Test** on 2024.
*This ensures the system only "knows" what happened in the past when making decisions for the future.*

### Stage 3: Slippage & "Handoff" Stress Test
When the regime switches from "Trend" to "Range," there is a period of uncertainty.
*   **The "Lag" Test**: Simulate a 1-hour or 4-hour delay in regime detection. If the strategy still makes money with a 4-hour delay, it is **robust**. If it fails, it is too sensitive for live paper trading.

---

## 3. New Script: `strategy_backtest/scripts/ensemble_validator.py`

We recommend creating a specialized validator script with these features:

### A. Regime Contribution Analysis
The report should break down performance by market state:
*   "Trend Strategy Return while in Trend Regime: +45%"
*   "Trend Strategy Return while in Range Regime: -12% (FILTERED)"
*   *This proves the ensemble logic is actually adding value.*

### B. Comparative Benchmarking
Automatically generate a 4-way comparison table:
1.  **HODL** (Buy and Hold)
2.  **Single-Best Strategy** (e.g., just MACD_KDJ)
3.  **Static Multi-Strategy** (Equal weight to all)
4.  **RAE Ensemble** (The dynamic switching version)

---

## 4. Implementation Steps for the Backtester

1.  **Modify `engine.py`**: Add a `RegimeLogger` that tracks which strategy was active at each timestamp.
2.  **Update `metrics.py`**: Add a function `compute_regime_metrics()` to calculate Sharpe and MDD per market state.
3.  **Enhance `run_backtest.py`**: Add a `--visualize_regimes` flag to generate a chart where the background color changes based on the detected regime (e.g., Green for Trend, Yellow for Range, Red for Crisis).

---

## 5. Success Criteria for Paper-Trade Readiness
A strategy is only ready for paper trading if it passes these "Hard Guards":
*   **Sharpe Ratio**: > 1.2 across the full 2023–2026 period.
*   **Regime-Switching Cost**: Total fees from switching must be < 5% of total profit.
*   **Max Drawdown**: Must not exceed 25% during the "Crisis" regime.

---
*Created by Gemini CLI | 2026-06-04*
