# Alpha Developer Build Pipeline

This document covers your job scope: **receive factor → build strategy → validate → hand off to tuner**.
Discovery and factor extraction are owned by `@alpha-researcher`.

## Stage 1 — Strategy Assembly
Triggered by a `NEW_FACTOR_DISCOVERED` inbox message from `@alpha-researcher`.

1. Read the Candidate Card at the path specified in the inbox message.
2. Review `factor_class`, `directional_bias`, `optimal_regime`, and the `Recommended Logic Switches`.
3. Write the strategy class in `strategy_backtest/strategies/{name}_strategy.py`.
   - Use any math functions from `strategy_backtest/library.py` that the researcher provided.
   - **The Architect Rule (Critical)**: Include every `Recommended Logic Switch` from the Candidate Card as a Categorical Parameter inside `OPTIMIZATION_RANGES`. Add 1 additional logic switch of your own if you see a natural extension.

## Stage 2 — Registration
Register the new strategy in `strategy_backtest/settings.py`:
- Assign the next available integer ID.
- Set initial baseline parameters (conservative defaults).
- Set `date_from` and `date_to` to cover the full available history for the primary coin.

## Stage 3 — Smoke Test
```bash
./venv/bin/python strategy_backtest/run_backtest.py --strategy {id} --date_from 2024-01-01 --date_to 2024-06-30
```
- Fix any syntax or import errors immediately.
- If the engine crashes (not the strategy): send `STRATEGY_ERROR_ESCALATION` to `@crypto-fullstack`.

## Stage 4 — Multi-Coin Baseline Sweep
Run the strategy on BTC, ETH, SOL using baseline params over the same 6-month window.
- If Sharpe < -1.0 across **all** coins: log `REJECTED` in the Candidate Card and stop.
- If at least one coin shows Sharpe ≥ 0: proceed to Stage 5.

## Stage 5 — WFO Baseline Validation
Run the 4 standard WFO windows:
```bash
./venv/bin/python strategy_backtest/run_backtest.py --strategy {id} --date_from 2023-01-01 --date_to 2023-06-30
./venv/bin/python strategy_backtest/run_backtest.py --strategy {id} --date_from 2024-01-01 --date_to 2024-06-30
./venv/bin/python strategy_backtest/run_backtest.py --strategy {id} --date_from 2025-01-01 --date_to 2025-06-30
./venv/bin/python strategy_backtest/run_backtest.py --strategy {id} --date_from 2026-01-01 --date_to 2026-05-01
```

**VIABLE** if: Sharpe > 0 in at least 3/4 windows (strategy has potential for Optuna to improve).
**REJECTED** if all 4 windows show Sharpe < 0 → update Candidate Card status to `REJECTED`, add `## Rejection Notes` block, stop.

## Stage 6 — Handoff to Tuner
```
Send inbox to @crypto-strategy-tuner:
  topic: FINETUNE
  strategy_id: {id}
```
Add a summary row to `.gemini/shared/AGENT_COLLABORATION.md`.
Update the Candidate Card `status` to `TUNING`.

## Stage 7 — Notify Fullstack (conditional)
If the WFO baseline already achieves Sharpe ≥ 1.0 before tuning:
```
Send inbox to @crypto-fullstack:
  topic: NEW_STRATEGY_READY
  strategy_id: {id}
  sharpe: {x}
  return: {x}%
  max_dd: {x}%
  best_coin: {COIN}
```

## Stage 8 — Multi-Coin Expansion (post-tuning)
After `@crypto-strategy-tuner` returns a `FINETUNE_PROMOTED` result (Sharpe ≥ 1.0):
1. Register the same class for additional coins (BNB, SOL, XRP) where `optimal_regime` fits.
2. Run a 2-year backtest per coin.
3. Keep registrations where Sharpe > 0.3. Remove where Sharpe ≤ 0.
