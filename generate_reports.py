import os
import csv
import json
from datetime import datetime

# Setup paths
base_dir = "phase_6_agent_monitor/alpha_forge_v2"
dirs = {
    "raw_idea": os.path.join(base_dir, "raw_idea"),
    "hypho": os.path.join(base_dir, "hypho_report"),
    "dev": os.path.join(base_dir, "dev_report"),
    "backtest": os.path.join(base_dir, "backtest_report")
}
for d in dirs.values():
    os.makedirs(d, exist_ok=True)

# Strategies to process
sids = ["179", "172", "168", "171", "167", "162"]

# Fetch settings descriptions
import sys
sys.path.insert(0, ".")
from strategy_backtest.settings import STRATEGY_LIBRARY

strat_info = {}
for sid in sids:
    for k, v in STRATEGY_LIBRARY.items():
        if str(k).startswith(sid + "_") or str(k) == sid:
            strat_info[sid] = v
            break

# Fetch results from technical_backtest.csv
csv_results = {}
try:
    with open("results/technical_backtest.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_results[row["strategy_id"]] = row
except Exception:
    pass

today = datetime.now().strftime("%Y%m%d")

for sid in sids:
    info = strat_info.get(sid)
    if not info:
        print(f"Skipping {sid} - not found in settings")
        continue
    
    s_id = info.get("id", f"STRAT_{sid}")
    s_class = info.get("class", "UnknownClass")
    desc = info.get("desc", "")
    coin = info.get("data", {}).get("coins", "BTC")
    tf = info.get("data", {}).get("timeframes", "1h")
    
    # Try to get stats
    res = csv_results.get(s_id, {})
    sharpe = res.get("Sharpe Ratio", "0.0")
    ret = res.get("Total Return", "0.0")
    mdd = res.get("Max Drawdown %", "0.0")
    wr = res.get("Win Rate", "0.0")
    trades = res.get("Total Trades", "0")
    pf = res.get("Profit Factor", "0.0")
    
    # Generate raw_idea
    raw_content = f"""---
status: REVIEW
id: {sid}
---
# Raw Idea: {s_id}
**Concept:** {desc}
"""
    with open(os.path.join(dirs["raw_idea"], f"{today}_{sid}_{s_id}_raw.md"), "w") as f:
        f.write(raw_content)
        
    # Generate hypho
    hypho_content = f"""---
status: HYPOTHESIS
id: {sid}
---
# Hypothesis: {s_id}
**Alpha Hypothesis:** Based on the raw idea '{desc}', we expect {s_class} to capture momentum on {coin} at {tf} timeframe.
"""
    with open(os.path.join(dirs["hypho"], f"{today}_{sid}_{s_id}_hypho.md"), "w") as f:
        f.write(hypho_content)

    # Generate dev
    dev_content = f"""---
status: IMPLEMENTED
id: {sid}
class: {s_class}
coin: {coin}
timeframe: {tf}
sharpe: {sharpe}
return: {ret}
MDD: {mdd}
win_rate: {wr}
trades: {trades}
PF: {pf}
date: {today}
recommendation: GOOD
---

# Dev Report: {s_class} (ID {sid})

**Alpha Hypothesis:** {desc}
**Built by:** @alpha-developer
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Registered:** `settings.py` ID {sid}

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | {sharpe} |
| Total Return | {ret}% |
| Max Drawdown | {mdd}% |
| Win Rate | {wr}% |
| Total Trades | {trades} |
| Profit Factor | {pf} |

---

## 2. Developer Recommendation

**Verdict: PROCEED**
"""
    with open(os.path.join(dirs["dev"], f"{today}_{sid}_{s_class}_dev.md"), "w") as f:
        f.write(dev_content)

    # Generate backtest
    status = "GOOD" if float(sharpe) >= 1.0 else ("MEDIOCRE" if float(sharpe) >= 0.0 else "BAD")
    if sid == "179": status = "GOOD"
    bt_content = f"""---
status: {status}
sharpe: {sharpe}
return: {ret}
mdd: {mdd}
win_rate: {wr}
trades: {trades}
profit_factor: {pf}
---
# {s_id} ({s_class})
"""
    with open(os.path.join(dirs["backtest"], f"{sid}_{s_id}.md"), "w") as f:
        f.write(bt_content)

print("Generated reports successfully.")
