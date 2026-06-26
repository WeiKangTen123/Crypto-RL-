# Recommendation: Implementing Long-Term Memory (LTM) for Agents

## 1. The Gap: Short-Term vs. Permanent Insight
Currently, your agents have **Short-Term Memory** (`session_memory.md`), which tracks the last 10 tasks, and **System Records** (`CHANGELOG.md`), which track file edits.

**The Problem**: When the 11th session occurs, the 1st session is deleted. If that 1st session contained a critical "lesson learned" (e.g., *"Strategy X fails specifically during BTC dominance spikes"*), that insight is **lost forever**. The agents will likely repeat the same mistake a week later.

---

## 2. Recommendation: The "Agent Knowledge Base" (AKB)
We should implement a **Long-Term Memory** tier that captures "Distilled Insights" rather than "Action Logs."

### Proposed Structure:
We recommend creating `LTM.md` files (Long-Term Memory) within each agent's folder and a shared `GLOBAL_LTM.md`.

#### A. @alpha-researcher/LTM.md (Strategy Wisdom)
Instead of "I ran a test," this file stores:
*   **Asset Profiles**: "SOL is highly sensitive to funding-rate reversals; avoid 5m scalping here."
*   **Failed Archetypes**: "Grid-trading without a trend-filter has failed 4 times in 2024; stop exploring this path."
*   **Regime Sensitivities**: "T3Nexus decay is linked to the 2024 'crashing volatility' regime."

#### B. @crypto-data-engineer/LTM.md (Data Reliability)
*   **Known Gaps**: "Binance 1m data for XRP is missing from 2022-03 to 2022-05."
*   **Quality Alerts**: "Funding rate parquet files require manual ffill() due to API lag."

---

## 3. The "Distillation" Process (How it works)
To keep the LTM clean and high-signal, we use a **Distillation Trigger**:

1.  **Weekly Review**: Every Friday (or every 10 sessions), the agent is instructed to read its own `session_memory.md`.
2.  **Extract Patterns**: The agent identifies recurring failures or surprising successes.
3.  **Update LTM**: The agent adds a one-line bullet point to its `LTM.md`.
4.  **Clear STM**: The agent can then safely truncate the `session_memory.md` knowing the "wisdom" is saved.

---

## 4. Why this helps "Last Night's" Memory
If an agent worked on a complex bug last night, the LTM ensures that even if you start a new conversation today, the agent can check its LTM and say:
> *"I remember from my long-term memory that we discovered a race condition in the backtest engine last night; I will check if the fix is still active before I start my new research."*

---

## 5. Implementation Plan
1.  **Create Files**: Initialize `LTM.md` for Quant, Data, and Fullstack agents.
2.  **Update `GEMINI.md`**: Add a mandatory directive: *"Before starting any task, agents MUST check their local LTM.md for historical constraints."*
3.  **Add a "Distillation" Step**: Update the Quant agent's research loop to include an "LTM Update" phase after Phase 8.

---
*Created by Gemini CLI | 2026-06-04*
