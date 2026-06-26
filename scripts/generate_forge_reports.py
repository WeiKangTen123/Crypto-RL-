import json
import os
import sys
from datetime import datetime

# Load settings and scan results
sys.path.append('.')
from strategy_backtest import settings

with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
    scan_data = json.load(f)

# Create output directories
base_dir = 'phase_6_agent_monitor/alpha_forge_v2'
hypho_dir = os.path.join(base_dir, 'hypho_report', 'Trend_Momentum')
dev_dir = os.path.join(base_dir, 'dev_report')
os.makedirs(hypho_dir, exist_ok=True)
os.makedirs(dev_dir, exist_ok=True)

date_str = datetime.now().strftime("%Y%m%d")
display_date = datetime.now().strftime("%Y-%m-%d")

# Process specific strategies
target_ids = ['131', '132', '133', '134', '135', '136', '137', '138']

for s_data in scan_data.get('results', []):
    s_id = str(s_data['id'])
    if s_id not in target_ids:
        continue
    
    s_class = s_data['class']
    status = s_data.get('grade', 'PENDING')
    sharpe = s_data.get('sharpe', 0.0)
    ret = s_data.get('return_pct', 0.0)
    mdd = s_data.get('mdd_pct', 0.0)
    win_rate = s_data.get('win_rate', 0.0)
    trades = s_data.get('trades', 0)
    pf = s_data.get('profit_factor', 0.0)
    
    # Get config from settings
    config = settings.STRATEGY_LIBRARY.get(s_id, {})
    coin = config.get('coin', 'BTC')
    tf = config.get('timeframe', '5m')

    # 1. Dev Report
    dev_content = f"""---
status: IMPLEMENTED
id: {s_id}
class: {s_class}
coin: {coin}
timeframe: {tf}
sharpe: {sharpe}
return: {ret}
MDD: {mdd}
win_rate: {win_rate}
trades: {trades}
PF: {pf}
date: {date_str}
recommendation: {'REJECT' if sharpe < 0 else ('PASS' if sharpe >= 1 else 'CONDITIONAL_PASS')}
---

# Dev Report: {s_class} (ID {s_id})

**Alpha Hypothesis:** Sniper-Swing combo utilizing rule-based entry triggers ({s_class}) combined with HTF trend filters and ATR exits.
**Built by:** @alpha-developer
**Date:** {display_date}
**Registered:** `settings.py` ID {s_id}

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | {sharpe} |
| Total Return | {ret}% |
| Max Drawdown | {mdd}% |
| Win Rate | {win_rate}% |
| Total Trades | {trades} |
| Profit Factor | {pf} |

---

## 2. Developer Recommendation

**Verdict: {'REJECT' if sharpe < 0 else ('PASS' if sharpe >= 1 else 'CONDITIONAL_PASS')}**

> Generated automatically after Optuna finetuning. Sharpe ratio is {sharpe}.
"""
    dev_path = os.path.join(dev_dir, f"{date_str}_{s_id}_{s_class}_dev.md")
    with open(dev_path, 'w') as f:
        f.write(dev_content)
    print(f"Generated Dev Report: {dev_path}")

    # 2. Hypho Report
    hypho_content = f"""---
name: {s_class}
strategy_id: {s_id}
type: short-term
factor_class: Momentum
directional_bias: Symmetric
optimal_regime: Any
timeframes: {tf}
coins: {coin}
interest: High
status: IMPLEMENTED
sharpe: {sharpe}
---

# Hypothesis: {s_class}

## Concept
Exploits intra-day momentum using short-term entry triggers with higher timeframe trend alignment.

## Entry Logic
- **Long/Short**: Uses `ForgeStrategy` configuration registered in settings.py

## Key Indicators
- Entry Signal
- HTF EMA/Supertrend Filter
- ATR for volatility trailing

Implementation handled by `ForgeStrategy` dynamic registry.
"""
    hypho_path = os.path.join(hypho_dir, f"{date_str}_{s_id}_{s_class}_hypho.md")
    with open(hypho_path, 'w') as f:
        f.write(hypho_content)
    print(f"Generated Hypho Report: {hypho_path}")
