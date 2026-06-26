# Common Bug Patterns Reference

**Before debugging any error**: check `.gemini/shared/SYSTEM_CHANGELOG.md` for recent file changes — the root cause is usually the last thing that was modified.

---

## Backend — Python / Flask

| Error | Root Cause | Fix |
|---|---|---|
| `truediv not supported for dtype str` | `taker_buy_base_vol` or `num_trades` stored as object in parquet | `run_backtest.py` `load_data()` — add `pd.to_numeric(..., errors='coerce')` |
| `No results — strategies may have insufficient data` | Empty df after date filter OR all signals NaN | Check parquet date range vs `date_from`/`date_to` in `settings.py` |
| `KeyError: 'bb_high'` in manage_trade | `generate_signals()` failed before signals were written to df | Trace the strategy's `generate_signals()` for dtype/column errors |
| `FutureWarning: Downcasting object dtype arrays on .fillna` | pandas 2.x deprecation in strategy signal generation | Add `.infer_objects(copy=False)` after `.fillna()` in the strategy file |
| `ImportError: freqtrade.strategy` or `numpy.rec` | DRL/FreqAI components not installed — out of scope for strategy backtest | Do NOT attempt to fix — log "DRL scope, skipping" and move on |
| `ModuleNotFoundError: No module named 'X'` | Package missing from venv | `./venv/bin/pip install X` — if fails, escalate to user in `activity.log` |
| `pandas-ta pip install fails` | Version naming issue (`0.3.14b` vs `0.3.14b0`) | Use `./venv/bin/pip install pandas-ta-classic` as a drop-in replacement |
| `CORS error` | Missing `Access-Control-Allow-Origin` header | `main.py` `add_header()` — ensure `*` is set |
| Flask returns 500 on `/api/strategy_backtest` | Module cache stale after `settings.py` edit | Route now uses `importlib.reload()` — restart Flask if persists |
| Empty equity curve from backtest | Strategy generates 0 trades | Check `generate_signals()` — signals may all be NaN or filtered out |

---

## Agent / Tooling

| Error | Root Cause | Fix |
|---|---|---|
| `activity.log update failed — command injection` | Bash echo with special chars in timestamp or message | Use `write_file` in append mode, not bash echo |
| `web_fetch: must contain valid URL` | Called `web_fetch` without a full `https://` URL | Always pass a complete URL; do not pass a query string or path alone |
| `[ERROR] Invalid stream: malformed tool call` | Gemini API returned empty or malformed response | Retry the tool call once. If it fails twice in a row, log and skip that step |
| `TerminalQuotaError: You have exhausted your capacity` | Flash/Pro model quota hit | Model cascade handles this automatically — do NOT retry manually |
| `File not found` in read_file | Wrong path or file does not exist | Run `ls <parent_dir>` first to confirm the path before retrying |
| `Error executing tool run_backtest: 0 trades` | Strategy logic not triggering any entries | Check signal columns in `generate_signals()` — add a debug backtest on 1 month of data |

---

## Frontend — JavaScript / CSS

| Error | Root Cause | Fix |
|---|---|---|
| Tabs stacking in UI | Tab elements inside flex card-header | Move tab bar to sibling `<div>` below `card-header` |
| No gap between dashboard sections | Mode content div lacks flex layout | Add `display: flex; flex-direction: column; gap: 32px` to mode containers |
| Toggle shows wrong state after click | Module cache / heartbeat race condition | Check `ctrlsEl.dataset.currentStatus` — optimistic update pattern needed |
| Strategy list not refreshing after fine-tune | Flask caches `settings.py` module | Route must call `importlib.reload()` before reading `STRATEGY_LIBRARY` |

---

## Inbox Message Routing Errors

| Wrong routing seen | Correct fix |
|---|---|
| `WEB_SEARCH_TOOL_FAILURE` sent to @crypto-fullstack | This is a quant researcher internal issue — log it, do NOT try to fix the web search |
| `0 trades` routed to @alpha-developer | @alpha-developer fixes strategy logic; if engine crash, escalate to @crypto-fullstack |
| `STALE_CRITICAL` (data freshness) | Route to @crypto-data-engineer, not fullstack |
