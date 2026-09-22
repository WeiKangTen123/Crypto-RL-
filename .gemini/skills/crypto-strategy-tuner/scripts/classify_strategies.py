"""
classify_strategies.py — Classify PENDING entries in scan_results.json.

Applies the full tuner_specs.md grading criteria:
  HARD OVERRIDES (always BAD):
    - total_trades < 10 — pure luck, nothing to tune
    - max_drawdown > 85% — undeployable
    - profit_factor = 0 — every trade a loser

  BAD (any one disqualifies):
    - Sharpe < 0.3
    - Total return < 0
    - total_trades < 30 — below CLT minimum
    - max_drawdown > 70%
    - profit_factor < 1.0

  GOOD (all must pass):
    - Sharpe >= 1.0, MDD <= 35%, trades >= 100, PF >= 1.2

  MEDIOCRE: passes BAD checks but does not meet all GOOD criteria.

Usage:
    ./venv/bin/python .gemini/skills/crypto-strategy-tuner/scripts/classify_strategies.py

Only classifies entries with grade == 'PENDING'.
Leaves existing GOOD / MEDIOCRE / BAD / ERROR grades untouched.
"""

import json
import os
import sys
from datetime import datetime

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SCAN_PATH = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'data', 'scan_results.json')


def grade_strategy(r):
    """Return (grade, grade_reason) for a single scan result entry."""
    sharpe = float(r.get('sharpe') or 0.0)
    ret    = float(r.get('total_return') or 0.0)
    dd     = float(r.get('max_drawdown') or 0.0)
    trades = int(r.get('total_trades') or 0)
    pf_raw = r.get('profit_factor')

    pf_is_inf = pf_raw is None or (isinstance(pf_raw, (int, float)) and float(pf_raw) >= 99)
    pf        = 0.0 if pf_raw is None else float(pf_raw)

    # ── Hard overrides ────────────────────────────────────────────────────────
    if trades < 10:
        return 'BAD', f'Only {trades} trades — hard minimum not met (pure luck, nothing to tune)'
    if dd > 85:
        return 'BAD', f'MDD {dd}% > 85% — undeployable regardless of Sharpe'
    if pf == 0.0 and not pf_is_inf:
        return 'BAD', 'PF = 0 — every trade was a loser, no gross wins at all'

    # ── BAD criteria ──────────────────────────────────────────────────────────
    if sharpe < 0.3:
        return 'BAD', f'Sharpe {sharpe} < 0.3 — no meaningful edge'
    if ret < 0:
        return 'BAD', f'Negative total return ({ret}%) over scan period'
    if trades < 30:
        return 'BAD', f'Only {trades} trades — below CLT minimum of 30; metrics statistically unreliable'
    if dd > 70:
        return 'BAD', f'MDD {dd}% > 70% — catastrophic drawdown, no realistic position size'
    if not pf_is_inf and pf < 1.0 and ret < 10.0:
        return 'BAD', f'PF {pf:.2f} < 1.0 — fundamentally losing on every trade'

    # ── GOOD — all criteria must pass ─────────────────────────────────────────
    pf_ok = pf_is_inf or pf >= 1.2
    if sharpe >= 1.0 and dd <= 35 and trades >= 100 and pf_ok:
        pf_str = '∞' if pf_is_inf else f'{pf:.2f}'
        return 'GOOD', f'Sharpe {sharpe}, DD {dd}%, {trades} trades, PF {pf_str} — all thresholds met'

    # ── MEDIOCRE — has potential, worth tuning ────────────────────────────────
    weaknesses = []
    if sharpe < 1.0:
        weaknesses.append(f'Sharpe {sharpe} below 1.0')
    if trades < 100:
        weaknesses.append(f'only {trades} trades (need ≥ 100 for GOOD)')
    if dd > 35:
        weaknesses.append(f'MDD {dd}% above 35%')
    if not pf_is_inf and pf < 1.2:
        weaknesses.append(f'PF {pf:.2f} below 1.2 target')

    reason = ('; '.join(weaknesses) + ' — tuning may improve') if weaknesses else 'Within MEDIOCRE range — tuning recommended'
    return 'MEDIOCRE', reason


def main():
    if not os.path.exists(SCAN_PATH):
        print(f'✗ scan_results.json not found at {SCAN_PATH}')
        sys.exit(1)

    with open(SCAN_PATH) as f:
        scan = json.load(f)

    results = scan.get('results', [])
    pending = [r for r in results if r.get('grade') == 'PENDING']

    if not pending:
        print('No PENDING strategies found — nothing to classify.')
        return

    print(f'Classifying {len(pending)} PENDING strategies...\n')

    classified = 0
    for r in results:
        if r.get('grade') != 'PENDING':
            continue
        if r.get('error'):
            r['grade']        = 'ERROR'
            r['grade_reason'] = str(r['error'])[:120]
        else:
            grade, reason     = grade_strategy(r)
            r['grade']        = grade
            r['grade_reason'] = reason
        classified += 1
        g = r['grade']
        print(f"  ID {r['id']:>3} [{r.get('class','?')[:35]:<35}] → {g:8} | {r['grade_reason'][:65]}")

    # Recalculate top-level counts
    counts = {'GOOD': 0, 'MEDIOCRE': 0, 'BAD': 0, 'PENDING': 0, 'ERROR': 0}
    for r in results:
        g = r.get('grade', 'PENDING')
        if g in counts:
            counts[g] += 1
    scan.update(counts)
    if counts['PENDING'] == 0:
        scan['classified'] = True
    scan['classified_at'] = datetime.now().isoformat()

    with open(SCAN_PATH, 'w') as f:
        json.dump(scan, f, indent=2)

    print(f'\n✓ Classified {classified} strategies — scan_results.json updated.')
    print(f"  GOOD={counts['GOOD']}  MEDIOCRE={counts['MEDIOCRE']}  BAD={counts['BAD']}  ERROR={counts['ERROR']}  PENDING={counts['PENDING']}")
    if scan.get('classified'):
        print('  classified=true')


if __name__ == '__main__':
    main()
