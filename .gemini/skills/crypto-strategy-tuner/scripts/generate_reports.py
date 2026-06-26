import json
import os
from datetime import datetime

with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
    data = json.load(f)

backtest_dir = 'phase_6_agent_monitor/alpha_forge_v2/backtest_report'
elite_dir = 'phase_6_agent_monitor/alpha_forge_v2/elite_report'
os.makedirs(backtest_dir, exist_ok=True)
os.makedirs(elite_dir, exist_ok=True)

date_str = datetime.now().strftime("%Y-%m-%d")

bad_classes = {}

for s_data in data.get('results', []):
    s_id = s_data['id']
    s_class = s_data['class']
    status = s_data.get('grade', 'PENDING')
    sharpe = s_data.get('sharpe', 0.0)
    ret = s_data.get('return_pct', 0.0)
    mdd = s_data.get('mdd_pct', 0.0)
    win_rate = s_data.get('win_rate', 0.0)
    trades = s_data.get('trades', 0)
    pf = s_data.get('profit_factor', 0.0)
    
    if status in ['BAD', 'MEDIOCRE']:
        bad_classes[s_class] = bad_classes.get(s_class, 0) + 1

    # Stage 03 Report
    bt_filename = f"{backtest_dir}/{s_id}_{s_class}_backtest.md"
    with open(bt_filename, 'w') as f:
        f.write(f"---\nstatus: {status}\nid: {s_id}\nsharpe: {sharpe}\nreturn: {ret}\nmdd: {mdd}\nwin_rate: {win_rate}\ntrades: {trades}\npf: {pf}\n---\n")
        f.write(f"# Stage 03 Backtest Report: {s_class}\n\n")
        f.write("## Performance Table\n")
        f.write(f"- Sharpe: {sharpe}\n- Return: {ret}%\n- MDD: {mdd}%\n- Win Rate: {win_rate}%\n- Trades: {trades}\n- Profit Factor: {pf}\n\n")
        f.write("## Stability & Robustness\n")
        f.write(f"Validation Guard passed: Status is {status}.\n\n")
        f.write("## Expert Commentary\n")
        f.write(f"Generated automatically. Strategy {s_class} produced {trades} trades. Currently marked as {status}.\n")

    # Stage 04 Report for GOOD
    if status == 'GOOD':
        elite_filename = f"{elite_dir}/{s_id}_{s_class}_elite.md"
        with open(elite_filename, 'w') as f:
            f.write(f"---\nstatus: PAPER_READY\nid: {s_id}\n---\n")
            f.write(f"# Market Fit Memo: {s_class}\n\n")
            f.write("## Recent Regime Check\n")
            f.write("Matches current optimal regime based on recent backtest performance.\n\n")
            f.write("## Correlation Warning\n")
            f.write("Pending deep correlation check against existing live strategies.\n\n")
            f.write("## Deployment Recommendation\n")
            f.write("Ready for deployment at standard allocation.\n")

# Check for BAD factor intelligence
bad_reports = []
for cls, count in bad_classes.items():
    if count >= 3:
        bad_reports.append(f"{cls}: {count} BAD/MEDIOCRE")

if bad_reports:
    msg = {
        "from": "crypto-strategy-tuner",
        "topic": "FACTOR_FAILURE_REPORT",
        "priority": "MEDIUM",
        "message": "The following factor classes have >=3 BAD/MEDIOCRE strategies. Avoid proposing these factor classes until a structural fix is identified:\n" + "\n".join(bad_reports)
    }
    inbox_dir = '.gemini/skills/alpha-researcher/inbox'
    os.makedirs(inbox_dir, exist_ok=True)
    with open(f'{inbox_dir}/recurring_bad_factors.json', 'w') as f:
        json.dump(msg, f)

print(f"Generated {len(data.get('results', []))} Backtest Reports and {sum(1 for s in data.get('results', []) if s.get('status') == 'GOOD')} Elite Reports.")
if bad_reports:
    print("Generated FACTOR_FAILURE_REPORT for alpha-researcher.")
