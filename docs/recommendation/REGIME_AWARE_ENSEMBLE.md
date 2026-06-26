# Detailed Recommendation: Regime-Aware Ensemble Strategy

## 1. Executive Summary
The proposed "Regime-Aware Ensemble" (RAE) system aims to solve the problem of strategy "decay"—where a technical strategy works in one year (e.g., 2023) but loses money in another (e.g., 2024). Instead of seeking a single robust set of parameters, the RAE system dynamically switches between specialized sub-strategies based on the current market environment.

---

## 2. Core Components & Scripts Involved

### A. The Regime Detection Engine (`core/regime_classifier.py`)
*   **Purpose**: To categorize every OHLCV bar into a "Regime ID" (e.g., 0=Trend, 1=Range, 2=Crisis).
*   **Technique**: Use `GaussianMixture` (from `scikit-learn`) or `MarkovRegression` (from `statsmodels`).
*   **Input Features**:
    *   `log_returns`: (Close - Close[1]) / Close[1]
    *   `volatility`: ATR(14) / Close
    *   `momentum`: RSI(14)
    *   `volume_intensity`: `taker_buy_base_vol` / `Volume`
*   **Output**: A new column `regime_id` added to the shared parquet dataset.

### B. The Ensemble Manager (`strategy_backtest/ensemble_engine.py`)
*   **Purpose**: Orchestrate multiple strategy classes simultaneously.
*   **Logic**:
    1.  At each bar, the engine checks the `regime_id`.
    2.  It queries a "Strategy Map" to see which sub-strategy is active for that regime.
    3.  If the regime changes, the engine handles the **Handoff Logic**:
        *   Option A (Strict): Close current position and open the new strategy's signal.
        *   Option B (Fluid): Keep current position but only allow the *new* strategy to exit or add to it.

### C. Configuration Extension (`strategy_backtest/settings.py`)
*   **Changes**: Add an `ENSEMBLE_CONFIG` block.
    ```python
    ENSEMBLE_CONFIG = {
        "id": "BTC_ENSEMBLE_V1",
        "regime_mapping": {
            0: "MACDKDJStrategy",      # Trend Regime -> Trend Strategy
            1: "MeanReversionVRSI",    # Range Regime -> Reversion Strategy
            2: "RiskOffStrategy"       # Crisis Regime -> Tight Stops / Cash
        }
    }
    ```

---

## 3. Implementation Workflow (Step-by-Step)

### Step 1: Feature Engineering
Enhance the `load_data` function in `run_backtest.py` to include regime features.
*   **Linked Script**: `strategy_backtest/run_backtest.py`
*   **Action**: Add a call to `RegimeClassifier.annotate(df)`.

### Step 2: Meta-Strategy Implementation
Create a new class `EnsembleStrategy` that inherits from `BaseStrategy`.
*   **Linked Script**: `strategy_backtest/strategies/ensemble_strategy.py`
*   **Internal Logic**:
    *   `__init__`: Instantiates 2–3 sub-strategies.
    *   `generate_signals`: Aggregates signals from all children.
    *   `manage_trade`: Decides which child's exit logic to follow based on the current regime.

### Step 3: Backtest Engine Update
Modify the `BacktestEngine.run()` loop to be "State-Aware."
*   **Linked Script**: `strategy_backtest/engine.py`
*   **Change**: Add a check at the start of the loop: `current_regime = _bar.regime_id`.

---

## 4. Key Factors for Success

1.  **Regime Stability**: We must use a smoothing window (e.g., 24 hours) for regime detection to prevent "jitter"—frequent switching between strategies that creates excessive fees.
2.  **Cross-Validation**: The Ensemble must be validated using the existing **4-Window WFO** (Walk-Forward Optimization) to ensure the regime detection itself isn't overfitted to 2023 data.
3.  **Order Flow Integration**: Since we have `taker_buy_base_vol`, we should use the "Taker Intensity" as a primary feature for regime detection. High taker intensity often signals the start of a Trend regime before it appears in price.

---

## 5. Summary of Modified Files
| File Path | Change Type | Responsibility |
| :--- | :--- | :--- |
| `strategy_backtest/engine.py` | Update | Support regime-based state switching. |
| `strategy_backtest/settings.py` | Update | Add strategy-to-regime mapping configuration. |
| `strategy_backtest/run_backtest.py` | Update | Add CLI flag `--ensemble`. |
| `core/regime_classifier.py` | **NEW** | Unsupervised learning for market state. |
| `strategy_backtest/strategies/ensemble_strategy.py` | **NEW** | Meta-strategy wrapper. |

---
*Created by Gemini CLI | 2026-06-04*
