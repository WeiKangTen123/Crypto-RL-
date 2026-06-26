# Crypto-RL Project Guidance

## Overview
This project utilizes a sophisticated autonomous agent ecosystem for quantitative research, system testing, and full-stack development.

## Specialized Sub-Agents
The following skills are defined as the primary experts for their respective domains. Use `activate_skill` to engage them.

| Agent | Responsibility | Primary Scope |
|---|---|---|
| **@alpha-researcher** | Alpha discovery, web research, factor extraction | `factor_library/`, `strategy_backtest/library.py` |
| **@alpha-developer** | Strategy assembly, Python implementation, logic switches | `strategy_backtest/strategies/`, `strategy_backtest/library.py` |
| **@crypto-strategy-tuner** | Benchmarking, grading (GOOD/MEDIOCRE/BAD), Optuna fine-tuning, proactive optimisation | `.gemini/skills/crypto-strategy-tuner/`, `settings.py` |
| **@crypto-qa-tester** | System testing, route validation, data linkage | `.gemini/skills/crypto-qa-tester/scripts/`, `logs/` |
| **@crypto-fullstack** | UI/Dashboard, Flask Backend, bug fixing | `main_controller/`, `strategy_backtest/engine.py` |
| **@crypto-data-engineer** | Data integrity, gaps, schema maintenance | `dataset/`, `utility/`, `data/` |

## Visibility Protocol (Mandatory)
Every action taken by an agent MUST be logged to maintain system transparency:
1. **Activity Log**: Append a one-line summary to `.gemini/skills/{agent_name}/activity.log` (each agent has its own log).
2. **Heartbeat**: Update `.gemini/skills/{agent_name}/heartbeat.json` with the current `status` and `action`.
3. **Collaboration Ledger**: Record completed tasks or handoffs in `.gemini/shared/AGENT_COLLABORATION.md`.
4. **Changelog**: Append every file modification to `.gemini/shared/SYSTEM_CHANGELOG.md` using the format:
   `| TIMESTAMP | AGENT | FILE_CHANGED | WHAT | WHY |`
5. **Long-Term Memory**: Record distilled insights and lessons learned in `.gemini/skills/{agent_name}/LTM.md`.

## Memory & Knowledge Management (LTM)
To ensure long-term intelligence and prevent recurring errors, agents must adhere to the LTM protocol:
1. **Initial Review**: At the start of every session, agents MUST read their local `LTM.md` and the `GLOBAL_LTM.md`.
2. **Distillation**: After completing a major task or at the end of a session, agents should identify "lessons learned" (e.g., "XRP data is stale on 4h", "Backtest engine fails on empty CSVs").
3. **Record Wisdom**: Distilled insights must be appended to the agent's `LTM.md`. Do NOT log actions; log *conclusions* and *patterns*.
4. **Knowledge Sharing**: If an insight affects the entire system, append it to `.gemini/shared/GLOBAL_LTM.md`.

## Cross-Agent Communication
Agents communicate via inbox messages in `.gemini/skills/{target}/inbox/`.
Format: `{ts}_from_{source}_{topic}.json`

## Development Lifecycle
- **Phases 0-3**: Data, Training, Validation.
- **Phase 4 (Backtesting)**: Performance evaluation and visual dashboard analysis.
- **Phase 5 (PBO)**: Probability of Backtest Overfitting analysis.
- **Phase 6 (System Monitoring)**: Real-time agent telemetry, system health dashboard, and centralized logging.
- **Phase 7 (Pattern Mining)**: Recursive optimization across Micro/Meso/Macro windows to generate the `wisdom_matrix.csv`.
- **Phase 8 (Pattern Execution)**: Live paper trading using real-time pattern matching and entry validation.
- **Quota Efficiency**: Always prefer **Flash** models for routine tasks (inbox checks, status reviews). **Pro** models should be reserved for high-reasoning tasks like research, complex bug fixing, or when explicitly requested via `HIGH` priority.
- **Research**: Always verify data integrity before strategy research.
- **Strategy**: Use 4-Window WFO and CPCV for all strategy validations.
- **Execution**: Always create `.bak` files before modifying critical system files.
- **Validation**: Every fix must be verified with automated tests (Chaos Test for API, System Test for logic).
