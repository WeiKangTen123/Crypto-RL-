# Phase 7: Recursive Pattern Mining & Wisdom Matrix

## Overview
Phase 7 is responsible for the **Recursive Pattern Discovery** system. It iterates through historical market data across multiple time-windows (Micro, Meso, Macro) to identify the optimal strategy parameters for specific market regimes.

The output of this phase is the `wisdom_matrix.csv`, which serves as a "Knowledge Base" for a planned `@crypto-pattern-agent` to use during live paper trading. **This agent has not been built yet** — the skill folder `.gemini/skills/crypto-pattern-agent/` does not exist. `wisdom_matrix.csv` is currently unmined and unused until that agent is implemented.

## Folder Structure
- `scripts/`: Implementation scripts for window generation, regime classification, and mining.
- `data/`: Storage for the final `wisdom_matrix.csv` and raw window results.
- `logs/`: Execution logs for mining runs.

## Window Definitions
- **Micro (1 Month):** High-resolution local patterns (volatility spikes, anomalies).
- **Meso (3 Months):** Medium-term market phases (consolidation, trend establishment).
- **Macro (1 Year):** Broad market cycles (Bull/Bear/Range).

## Wisdom Matrix Schema
| Column | Description |
| :--- | :--- |
| `strategy_id` | Unique ID of the strategy |
| `window_id` | Unique ID for the specific time window |
| `type` | MICRO, MESO, or MACRO |
| `start_date` | Window start (YYYY-MM-DD) |
| `end_date` | Window end (YYYY-MM-DD) |
| `params` | JSON string of optimized parameters |
| `roi` | Return on Investment in window |
| `sharpe` | Sharpe Ratio in window |
| `regime` | Classified market pattern (e.g., TREND_UP, CHOP_VOL) |
| `regime_score` | Similarity score or confidence metric |

## Usage
Run the miner for a specific strategy:
```bash
./venv/bin/python phase_7/miner.py --strategy_id 86
```
