# System QA Specifications

## Core Rule — Test Everything, Fix Nothing
**You find breakages and route them. You do NOT fix anything — even if you see an obvious one-line fix.**
If you catch yourself thinking "I could just change X" → stop. Write the inbox message instead.

---

## Severity Levels

| Level | Meaning | Example |
|---|---|---|
| **CRITICAL** | System is completely down or unusable | Server not responding, all routes failing |
| **HIGH** | A core feature is broken, blocks other agents | Import error, parquet missing, route 500 |
| **MEDIUM** | Degraded functionality, workaround exists | Smoke test crash, 0 trades, stale data |
| **LOW** | Informational, non-blocking | Warning in log, minor formatting issue |

---

## Routing Table

| Failure Type | Route To | Priority |
|---|---|---|
| Server not responding (connection refused) | @crypto-fullstack | CRITICAL |
| All Flask routes returning 500 | @crypto-fullstack | CRITICAL |
| Flask API route returns non-200 (single route) | @crypto-fullstack | HIGH |
| Strategy class fails to import | @crypto-fullstack | HIGH |
| `importlib.reload` fails on `settings.py` | @crypto-fullstack | HIGH |
| Backtest smoke test crashes with exception | @crypto-fullstack | HIGH |
| Backtest returns 0 trades | @crypto-fullstack | MEDIUM |
| Parquet file missing for a registered strategy | @crypto-data-engineer | HIGH |
| dtype error in parquet | @crypto-data-engineer | HIGH |
| `scan_results.json` missing or corrupt | @crypto-strategy-tuner | MEDIUM |
| `finetune_results.json` corrupt | @crypto-strategy-tuner | MEDIUM |
| `/api/strategy_scan_results` returns empty or error | @crypto-strategy-tuner | MEDIUM |
| `/api/run_tuner_scan` returns error | @crypto-fullstack | MEDIUM |
| Agent heartbeat stale (> 10 min, status ONLINE) | agent-specific (see below) | LOW |

### Agent Heartbeat Routing
| Stale agent | Route to |
|---|---|
| @crypto-fullstack heartbeat stale | No escalation — it monitors itself |
| @crypto-data-engineer stale | @crypto-fullstack |
| @alpha-researcher stale | @crypto-fullstack |
| @alpha-developer stale | @crypto-fullstack |
| @crypto-strategy-tuner stale | @crypto-fullstack |

---

## Flaky Test Handling
If a test FAILS → **retry once immediately** before escalating:
- Retry passes → log `[WARN] flaky: {test_name}` — do NOT send inbox (not a real failure)
- Retry fails again → escalate as normal FAIL with note "confirmed on 2 consecutive runs"

This prevents false positives from transient network/timing issues.

---

## Test Suite Components

1. **Flask Routes** — ping all major endpoints:
   - `GET /api/strategy_list` → expect 200 + JSON array
   - `GET /api/strategy_scan_results` → expect 200 + JSON
   - `POST /api/run_tuner_scan` → expect 200
   - `POST /api/trigger_tuner_rescan` → expect 200
   - `POST /api/trigger_finetune` → expect 200 or 400 (if no body)
   - `GET /api/agent_telemetry` → expect 200 + JSON

2. **Strategy Imports** — validate every class in `strategy_backtest/strategies/` loads without error

3. **Data Linkage** — confirm every entry in `settings.py` STRATEGY_LIBRARY has a matching parquet in `dataset/`

4. **Smoke Tests** — run 1-month backtests (2023-01-01 → 2023-02-01) for a sample of 5 registered strategies

5. **Agent Health** — check each agent's `heartbeat.json`:
   - `ts` field should be within last 10 minutes if status is ONLINE
   - If stale: log LOW warning, do NOT send inbox unless > 30 min stale

6. **Shared Files Integrity**:
   - `scan_results.json` — must be valid JSON and contain `results` array
   - `finetune_results.json` — must be valid JSON if it exists

---

## Inbox Message Format
```json
{
  "from":     "crypto-qa-tester",
  "priority": "HIGH",
  "topic":    "ROUTE_FAILURE",
  "message":  "Describe what failed and what the exact error was",
  "context":  { "test": "test_name", "detail": "exact error text" }
}
```
