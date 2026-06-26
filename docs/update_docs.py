import os

file_path = "/Users/weikangten/Desktop/Crypto-RL/docs/important/SYSTEM_ARCHITECTURE.md"

appendix = """

---

## Appendix: Backtest Execution Mechanics & Realism
*Update: June 2026*

The Crypto-RL Backtesting Engine (`strategy_backtest/engine.py`) employs standard institutional "Intra-bar Interpolation" to process Stop-Loss (SL), Trailing Stop (TS), and Take Profit (TP) orders.

### 1. Intrabar Priority (Pessimistic Execution Bias)
Because OHLC data cannot provide the exact tick sequence of a single bar, it is possible for a bar's High to breach a Take Profit and its Low to breach a Stop Loss simultaneously.
* **Standard Rule:** Crypto-RL uses a **Pessimistic Execution Bias**. If both limits are breached within the same bar, the engine always prioritizes the **Stop-Loss / Trailing Stop** first. This ensures backtest results do not overstate profitability.

### 2. The Gap-Through Guard
Crypto-RL natively handles market gaps (e.g., when the `Open` price of a bar skips entirely past a resting stop-market or limit order):
* **Stop Orders (SL / TS):** If a bar opens past the stop-loss level, the fill price is downgraded to the exact `Open` price.
* **Limit Orders (TP):** If a bar opens past the take-profit level, the limit order is upgraded to fill at the `Open` price.

### 3. "Look-Ahead Bias" vs Intra-Bar Interpolation
Using the `Low` of the current bar to detect an intrabar Stop-Loss breach—and executing exactly at that exact level—is **NOT** Look-Ahead Bias. It correctly simulates an exchange holding a Stop-Market order. Delaying market orders until the Bar Close (as seen in rudimentary frameworks like `backtesting.py`) creates unrealistic "Pessimistic Execution Bias." Crypto-RL simulates exact exchange execution semantics without looking at the next bar's data.
"""

with open(file_path, "a", encoding="utf-8") as f:
    f.write(appendix)

print("Updated SYSTEM_ARCHITECTURE.md")
