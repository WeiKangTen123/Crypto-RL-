# Crypto-RL Project Mandate & Architectural Guidance

## 1. Executive Summary
Crypto-RL is an autonomous algorithmic trading ecosystem powered by Deep Reinforcement Learning (DRL) and Multi-Factor Technical Analysis. The system utilizes a specialized 6-agent hierarchy to discover alpha, build strategies, and monitor live performance.

## 2. Specialized Sub-Agents (The Roster)
Whenever you are tasked with a mission, you MUST activate the appropriate expert skill from `.gemini/skills/`.

| Agent | Responsibility | Key Folders |
|---|---|---|
| **`alpha-researcher`** | Discovery, Web Research, Factor extraction. | `factor_library/`, `library.py` |
| **`alpha-developer`** | Python Strategy implementation, Logic Switches. | `strategies/`, `library.py` |
| **`crypto-strategy-tuner`** | Optuna Parameter Tuning, Benchmarking. | `scan_results.json`, `settings.py` |
| **`crypto-qa-tester`** | Automated System Testing, Failure Routing. | `scripts/system_test.py`, `logs/` |
| **`crypto-fullstack`** | Flask Backend, UI/Dashboard, Bug Fixing. | `main_controller/`, `engine.py` |
| **`crypto-data-engineer`** | Parquet Integrity, Gap Repairs, BTC Health. | `dataset/`, `utility/` |

---

## 3. Core Protocols (Operational Standards)

### 3.1 Factor Library Protocol (library.py)
To maintain a high-speed research environment, we enforce the **Library-First Mandate**:
1. **Factor Isolation**: Mathematical logic must live in `strategy_backtest/library.py` as pure functions.
2. **Obsidian Zettelkasten**: Every new factor must have a card in `factor_library/` (YAML-compatible).
3. **Obsidian Bridge**: Every backtest run MUST be synchronized to the factor library using `utility/sync_backtest_to_obsidian.py` to maintain a live performance ledger.
4. **DRY Enforcement**: No duplicate RSI/VWAP/ATR code across strategy files. Import them from the library.

### 3.2 Visibility Protocol (Mandatory Logging)
Agents must maintain 100% transparency through the logging stack:
- **Activity Log**: Append one-line summaries to `.gemini/skills/{agent}/activity.log`.
- **Heartbeat**: Update `heartbeat.json` with status (`ONLINE`, `STANDBY`, `ERROR`) and current `action`.
- **System Changelog**: Append file edits to `.gemini/shared/SYSTEM_CHANGELOG.md`.
- **Long-Term Memory**: Distill major insights (not actions) into `LTM.md`.

### 3.3 Regime-Aware Mandate (Phase 7 & 8)
Live trading must NEVER use static parameters. 
1. **Mining Requirement**: Every strategy must have a `wisdom_matrix.csv` (Phase 7).
2. **Flash Backtest**: Trades are only executed if they pass a real-time "Flash Backtest" against the current market regime.

### 3.4 State Registry & The Graveyard
The **Phase 6 Interactive Dashboard** is the project's **Primary State Registry**:
1. **Source of Truth**: If a strategy is not in Phase 6 INCUBATION or STRESS_TEST, it is not live.
2. **The Graveyard**: Strategies that fail at SMOKE, WFO, or PBO stages are permanently exiled to the **GRAVEYARD** stage (XX). 
3. **Auditability**: Every exiled strategy MUST have a corresponding "Autopsy Report" in the Failure Vault.

---

## 4. Development Lifecycle (The Scientist Mandate)
Any strategy seeking `VALIDATED` status must pass the **8-Stage Scientific Pipeline**:
1. **INGEST** (Factors) → 2. **BUILD** (Logic) → 3. **SYNTAX** (AST) → 4. **SMOKE** (Execution) → 5. **BACKTEST** (Baseline) → 6. **WFO_EVO** (Stability) → 7. **PBO_AUDIT** (Overfit) → 8. **MANIFEST** (Deploy).

---

## 5. Security & Safety
- **Secrets**: Never log `.env` contents, API keys (Binance/OpenAI), or credentials.
- **Rollback**: Critical system files (`main.py`, `settings.py`) must have a `.bak` snapshot before modification.
- **Quota**: Prefer **Flash** models for maintenance. Save **Pro** for Alpha discovery and complex refactors.
