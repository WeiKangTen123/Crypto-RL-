"""
run_targeted_backtest.py
Run backtest for a specific list of strategy IDs and print a summary.
Used to validate Phase 1 quick-fix tweaks.
"""
import os, sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from strategy_backtest.settings  import STRATEGY_LIBRARY
from strategy_backtest.run_backtest import run_strategy
import strategy_backtest.strategies  # noqa: F401  triggers auto-loader

TARGET_IDS = ["1", "6", "11", "13", "14", "16", "34", "36", "106", "135", "146"]

results = []
for sid in TARGET_IDS:
    cfg = STRATEGY_LIBRARY.get(sid)
    if cfg is None:
        print(f"[SKIP] id={sid} not found")
        continue
    print(f"\n>>> id={sid}  {cfg['class']} ({cfg['data']['coins']} {cfg['data']['timeframes']})")
    try:
        metrics = run_strategy(cfg)
        if not metrics:
            continue
        sharpe = round(float(metrics.get("Sharpe Ratio",  0)), 2)
        ret    = round(float(metrics.get("Total Return",  0)), 2)
        mdd    = round(float(metrics.get("Max Drawdown %",0)), 1)
        wr     = round(float(metrics.get("Win Rate",      0)), 1)
        trades = int(  float(metrics.get("Total Trades",  0)))
        pf     = round(float(metrics.get("Profit Factor", 0)), 2)
        results.append({"id": sid, "class": cfg["class"],
                        "sharpe": sharpe, "ret": ret, "mdd": mdd,
                        "wr": wr, "trades": trades, "pf": pf})
    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n\n========= PHASE 1 RESULTS =========")
print(f"{'ID':<8} {'Sharpe':>7} {'Return':>10} {'MDD':>7} {'Trades':>7}  Outcome")
print("-" * 70)
for r in results:
    if r["sharpe"] >= 1.0 and r["trades"] >= 100 and r["mdd"] <= 70:
        outcome = "GOOD ✓"
    elif r["sharpe"] >= 0.3 and r["trades"] >= 30:
        outcome = "MEDIOCRE ✓"
    else:
        outcome = "still BAD"
    print(f"{r['id']:<8} {r['sharpe']:>+7.2f} {r['ret']:>+9.1f}% {r['mdd']:>6.1f}% {r['trades']:>7}  {outcome}  ({r['class']})")
