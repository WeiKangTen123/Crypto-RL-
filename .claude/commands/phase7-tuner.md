---
description: Phase 7 autonomous window tuner — checks param ranges, widens boundaries if hitting limits, optionally runs full miner
argument-hint: <strategy_id> [--probe_trials N] [--max_iter N] [--run_miner]
---

You are the **Phase 7 Tuner Agent** for the Crypto-RL project.

Your job: given a strategy ID, autonomously validate that its parameter ranges are wide enough for the Phase 7 window optimizer, adjust them if not, and optionally kick off the full mining run.

## On every invocation

**Step 0 — Read memory**
Read `.claude/commands/logs/session_memory.md` (last session context) and `.claude/commands/logs/LTM.md` (historical patterns and constraints) before doing anything else.

**Step 1 — Validate the strategy exists**
Check `strategy_backtest/settings.py` — confirm the strategy ID is registered and the class exists in `strategy_backtest/strategies/`.
If not found, stop and tell the user what is missing.

**Step 2 — Run the tuner agent script**
```bash
cd /Users/weikangten/Desktop/Crypto-RL && venv/bin/python phase_7/agents/tuner_agent.py --strategy_id $ARGUMENTS
```
The script will:
- Probe 3 representative windows (MICRO / MESO / MACRO) with 30 Optuna trials each
- Detect any params hitting range boundaries (within 5% of min/max)
- Automatically widen those ranges in `phase_7/scripts/window_tuner.py`
- Repeat up to 5 times until stable

**Step 3 — Review output**
After the script finishes:
- If ranges were adjusted in `window_tuner.py` → confirm with the user what changed
- If ranges were adjusted in the **strategy class file** (source=OPTIMIZATION_RANGES) → confirm the class file was edited correctly
- If a param shows `[WARN] not found` for both locations → manually add it:
  - If it's strategy-specific, add to `strat_cls.OPTIMIZATION_RANGES` in the strategy `.py` file
  - If it's generic, add to `DEFAULT_RANGES` in `window_tuner.py`
- If any params remain UNTUNABLE (listed in the UNTUNABLE section) → add them with sensible ranges before proceeding
- If the strategy class has errors → diagnose and fix before re-running

**Step 4 — Confirm before mining**
After ranges are stable, ask:
> "Ranges are stable. Run full Phase 7 mining now (165 windows, ~20–60 min)?"

If yes, run:
```bash
cd /Users/weikangten/Desktop/Crypto-RL && venv/bin/python phase_7/miner.py --strategy_id <id>
```
Monitor stdout for PROGRESS lines and report completion.

**Step 5 — Update memory**
1. Append to `.claude/commands/logs/LTM.md`:
   ```
   [YYYY-MM-DD HH:MM] | Strategy <id> (<class>) | <what was adjusted or confirmed>
   ```
2. Prepend a one-line session summary to `.claude/commands/logs/session_memory.md` (keep max 10 entries).
3. Append the key actions to `.claude/commands/logs/activity_log.md` using the standard action prefixes.

## Important rules
- Never edit `settings.py` params during this flow — only `window_tuner.py` ranges
- If the script cannot auto-edit a range (regex mismatch), edit `window_tuner.py` manually instead of giving up
- Always re-run the probe after each range edit to confirm the boundary is gone
- If a strategy consistently hits boundaries even after 5 iterations, it likely needs wider hand-crafted ranges — report this to the user

## Toolbox
- `phase_7/agents/tuner_agent.py` — the main probe + edit loop
- `phase_7/scripts/window_tuner.py` — DEFAULT_RANGES lives here
- `phase_7/miner.py` — full 165-window mining script
- `.claude/commands/logs/LTM.md` — long-term memory
- `.claude/commands/logs/session_memory.md` — session memory
- `.claude/commands/logs/activity_log.md` — activity log
- `strategy_backtest/settings.py` — strategy configs
- `strategy_backtest/strategies/` — strategy class files (OPTIMIZATION_RANGES live here)
