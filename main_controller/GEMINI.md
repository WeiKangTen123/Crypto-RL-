# main_controller Subdirectory Protocol

## 1. Scope
This directory governs the system's central nervous system, including the Flask API, the Phase 6 Command Center, and the agent terminal infrastructure.

## 2. Dashboard Interface Logic
1. **Pipeline Sync**: The 8 forge stages (00-07) must directly reflect the counts in the underlying file system (`factor_library/`, `strategies/`, `scan_results.json`).
2. **The Failure Vault**: Any entry in `scan_results.json` with grade `BAD` or `ERROR` must be surfaced in the Failure Vault and counted in the Graveyard stage.
3. **Agent Terminal Rules**: 
   - Live telemetry must update every 5 seconds.
   - The **Live Task Evolution** (Infographic circles) must be driven strictly by `[X/Y]` prefixes in the agent's heartbeat `action` string.

## 3. Deployment Safety
1. **Server Integrity**: `main.py` must never be modified without a `.bak` snapshot.
2. **Crash Recovery**: If the server fails to start, agents must use `chaos_test.py` to identify the broken route.
3. **Port Binding**: The controller strictly binds to port `5001`. Do not attempt to use `5000` (MacOS system reserved).
