"""
sync_scan_results.py
Update .gemini/skills/crypto-strategy-tuner/data/scan_results.json with
fresh post-fix metrics from results/technical_backtest.csv.

Grade rules (reconstructed from existing grade_reason patterns):
  trades <  10               → BAD  "hard minimum not met"
  trades <  30               → BAD  "below CLT minimum of 30"
  mdd    >  85               → BAD  "undeployable regardless of Sharpe"
  mdd    >  70               → BAD  "catastrophic drawdown"
  sharpe <  0.3              → BAD  "no meaningful edge"
  sharpe >= 1.0, trades ≥100 → GOOD "Fine-tuned — Sharpe X, N trades"
  otherwise                  → MEDIOCRE (with reason details)
"""

import json, os, sys
from datetime import datetime, timezone

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from strategy_backtest.settings import STRATEGY_LIBRARY

SCAN_JSON   = os.path.join(_ROOT, '.gemini', 'skills', 'crypto-strategy-tuner',
                           'data', 'scan_results.json')
RESULTS_CSV = os.path.join(_ROOT, 'results', 'technical_backtest.csv')

# ── Build settings_key → strategy_id mapping ─────────────────────────────────
key_to_sid = {}
for k, v in STRATEGY_LIBRARY.items():
    key_to_sid[str(k)] = v['id']

# ── Load CSV ──────────────────────────────────────────────────────────────────
df = pd.read_csv(RESULTS_CSV)
csv_map = df.set_index('strategy_id').to_dict('index')

# ── Grade logic ───────────────────────────────────────────────────────────────
def compute_grade(sharpe, trades, mdd, pf):
    s = round(sharpe, 2)
    t = int(trades)
    m = round(mdd, 1)

    if t < 10:
        return 'BAD', f"Only {t} trades — hard minimum not met (pure luck, nothing to tune)"
    if t < 30:
        return 'BAD', f"Only {t} trades — below CLT minimum of 30; metrics statistically unreliable"
    if m > 85:
        return 'BAD', f"MDD {m}% > 85% — undeployable regardless of Sharpe"
    if m > 70:
        return 'BAD', f"MDD {m}% > 70% — catastrophic drawdown, no realistic position size"
    if s < 0.3:
        return 'BAD', f"Sharpe {s} < 0.3 — no meaningful edge"

    if s >= 1.0 and t >= 100:
        return 'GOOD', f"Fine-tuned — Sharpe {s}, {t} trades"

    reasons = []
    if s < 1.0:
        reasons.append(f"Sharpe {s} below 1.0")
    if t < 100:
        reasons.append(f"only {t} trades (need ≥ 100 for GOOD)")
    if m > 35:
        reasons.append(f"MDD {m}% above 35%")
    reason = '; '.join(reasons) + ' — tuning may improve' if reasons else f"Sharpe {s} — tuning may improve"
    return 'MEDIOCRE', reason

# ── Main update ───────────────────────────────────────────────────────────────
with open(SCAN_JSON) as f:
    scan = json.load(f)

now_iso = datetime.now(timezone.utc).isoformat()
updated = skipped = no_match = 0

for entry in scan['results']:
    eid = str(entry['id'])
    sid = key_to_sid.get(eid)
    if sid is None or sid not in csv_map:
        no_match += 1
        print(f"  [MISS]  id={eid:<8}  → settings key not in CSV")
        continue

    row = csv_map[sid]
    sharpe  = round(float(row['Sharpe Ratio']),  2)
    ret     = round(float(row['Total Return']),   2)
    mdd     = round(float(row['Max Drawdown %']), 1)
    wr      = round(float(row['Win Rate']),       2)
    trades  = int(  float(row['Total Trades']))
    pf      = round(float(row['Profit Factor']),  2)

    grade, grade_reason = compute_grade(sharpe, trades, mdd, pf)

    entry['sharpe']        = sharpe
    entry['total_return']  = ret
    entry['max_drawdown']  = mdd
    entry['win_rate']      = wr
    entry['total_trades']  = trades
    entry['profit_factor'] = pf
    entry['grade']         = grade
    entry['grade_reason']  = grade_reason
    entry['scanned_at']    = now_iso

    updated += 1
    print(f"  [OK]    id={eid:<8}  grade={grade:<10} sharpe={sharpe:+.2f}  "
          f"ret={ret:+.1f}%  mdd={mdd:.1f}%  trades={trades}")

# ── Recount top-level grade tallies ──────────────────────────────────────────
counts = {'GOOD': 0, 'MEDIOCRE': 0, 'BAD': 0, 'PENDING': 0, 'ERROR': 0}
for entry in scan['results']:
    g = entry.get('grade', 'PENDING')
    counts[g] = counts.get(g, 0) + 1

scan['GOOD']    = counts['GOOD']
scan['MEDIOCRE']= counts['MEDIOCRE']
scan['BAD']     = counts['BAD']
scan['PENDING'] = counts.get('PENDING', 0)
scan['ERROR']   = counts.get('ERROR', 0)
scan['classified']    = updated
scan['classified_at'] = now_iso
scan['scanned_at']    = now_iso

with open(SCAN_JSON, 'w') as f:
    json.dump(scan, f, indent=2)

print(f"\n[DONE]  updated={updated}  no_match={no_match}  skipped={skipped}")
print(f"[COUNTS] GOOD={counts['GOOD']}  MEDIOCRE={counts['MEDIOCRE']}  BAD={counts['BAD']}  PENDING={counts['PENDING']}")
