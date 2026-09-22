"""
update_desc_from_scan.py
Reads scan_results.json and rewrites the 'desc' field in settings.py
for every strategy that has fresh metrics.

Usage:
    python scripts/update_desc_from_scan.py
"""

import json, os, re, sys

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_JSON   = os.path.join(ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'data', 'scan_results.json')
SETTINGS_PY = os.path.join(ROOT, 'strategy_backtest', 'settings.py')

# ── Load scan results ─────────────────────────────────────────────────────────
with open(SCAN_JSON) as f:
    scan = json.load(f)

scan_map = {}
for r in scan.get('results', []):
    if r.get('sharpe') is not None and r.get('grade') not in ('ERROR', None):
        scan_map[str(r['id'])] = r

print(f"Loaded {len(scan_map)} scan entries with valid metrics.")

# ── Read settings.py ──────────────────────────────────────────────────────────
with open(SETTINGS_PY) as f:
    lines = f.readlines()

# ── Metric suffix builder ─────────────────────────────────────────────────────
def build_suffix(r):
    s   = r['sharpe']
    ret = r['total_return']
    mdd = r['max_drawdown']
    t   = r['total_trades']
    pf  = r['profit_factor']
    g   = r['grade']
    sign = '+' if ret >= 0 else ''
    return f"Sharpe {s:+.2f}, ROI {sign}{ret:.1f}%, MDD {mdd:.1f}%, {t} trades ({g}). PF={pf:.2f}"

# Strip any existing metric tail from a desc string body
_STRIP_RE = re.compile(
    r'[.\s]*(?:FIXED[^.]*\.\s*)?'
    r'(?:Sharpe [+\-]?\d|sharpe [+\-]?\d).*',
    re.IGNORECASE | re.DOTALL
)

def clean_desc(body):
    return _STRIP_RE.sub('', body).rstrip('. ')

# ── Walk lines, track which strategy block we are in ─────────────────────────
# Settings looks like:
#     "123": {
#         "id": "...",
#         "desc": "...",   ← update this
#         ...
#     },

BLOCK_RE = re.compile(r'^\s+"(\d+)"\s*:\s*\{')
DESC_RE  = re.compile(r'^(\s+"desc"\s*:\s*")(.*)(",\s*)$')

updated = 0
current_sid = None
new_lines = []

for line in lines:
    # Detect strategy block start
    bm = BLOCK_RE.match(line)
    if bm:
        current_sid = bm.group(1)
        new_lines.append(line)
        continue

    # Detect desc line for current strategy
    if current_sid and current_sid in scan_map:
        dm = DESC_RE.match(line)
        if dm:
            prefix, body, trail = dm.group(1), dm.group(2), dm.group(3)
            suffix = build_suffix(scan_map[current_sid])
            new_body = clean_desc(body) + '. ' + suffix + '.'
            new_line = prefix + new_body + trail + '\n'
            if new_line.rstrip('\n') != line.rstrip('\n'):
                new_lines.append(new_line)
                updated += 1
                r = scan_map[current_sid]
                print(f"  [OK] id={current_sid:<5} {r['grade']:<9} {suffix[:65]}")
                continue

    new_lines.append(line)

# ── Write back ────────────────────────────────────────────────────────────────
with open(SETTINGS_PY, 'w') as f:
    f.writelines(new_lines)

print(f"\n[DONE] Updated {updated} desc fields in settings.py")
print(f"       GOOD={scan.get('GOOD',0)}  MEDIOCRE={scan.get('MEDIOCRE',0)}  "
      f"BAD={scan.get('BAD',0)}  ERROR={scan.get('ERROR',0)}")
