"""
sync_phase6_backtest_reports.py
Refresh every alpha_forge_v2/backtest_report/*.md with post-fix metrics
from results/technical_backtest.csv, then update backtest_with_slippage.csv.

Status rules (applied only to transitional states; ELITE left untouched):
  sharpe >= 1.0  → GOOD
  sharpe >= 0.0  → MEDIOCRE
  sharpe <  0.0  → BAD
  no match found → PENDING
"""

import os, re, sys
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from strategy_backtest.settings import STRATEGY_LIBRARY

RESULTS_CSV    = os.path.join(_ROOT, 'results', 'technical_backtest.csv')
REPORTS_DIR    = os.path.join(_ROOT, 'phase_6_agent_monitor', 'alpha_forge_v2', 'backtest_report')
SLIPPAGE_CSV   = os.path.join(_ROOT, 'strategy_backtest', 'results', 'backtest_with_slippage.csv')
CANONICAL_CSV  = RESULTS_CSV

# ── Build key → strategy_id mapping from settings ────────────────────────────
# key_class_map: (pure_numeric_key, class_name) → strategy_id
# key_map:       pure_numeric_key → [strategy_id, ...]
key_class_map = {}
key_map = {}
for k, v in STRATEGY_LIBRARY.items():
    pure_k = k.split('_')[0]
    if not pure_k.isdigit():
        continue
    cls = v['class']
    sid = v['id']
    key_class_map[(pure_k, cls)] = sid
    key_map.setdefault(pure_k, []).append(sid)

# ── Load fresh results ────────────────────────────────────────────────────────
if not os.path.exists(RESULTS_CSV):
    print(f'[ERROR] Results CSV not found: {RESULTS_CSV}')
    sys.exit(1)

results_df = pd.read_csv(RESULTS_CSV)
results_map = results_df.set_index('strategy_id').to_dict('index')

# ── Determine status from sharpe ──────────────────────────────────────────────
PROTECTED_STATUSES = {'ELITE'}  # never overwrite these

def _status(sharpe):
    if sharpe >= 1.0:
        return 'GOOD'
    elif sharpe >= 0.0:
        return 'MEDIOCRE'
    else:
        return 'BAD'

# ── Parse / update YAML frontmatter (no pyyaml required) ─────────────────────
FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL | re.MULTILINE)

def _get_fm_field(fm_text, key):
    """Case-insensitive field lookup; returns (matched_key, value) or (None, None)."""
    for line in fm_text.splitlines():
        m = re.match(rf'^\s*({re.escape(key)})\s*:\s*(.*)$', line, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2).strip()
    return None, None

def _set_fm_field(fm_text, key, value):
    """Replace or add a field (case-insensitive key match)."""
    pattern = re.compile(rf'^(\s*{re.escape(key)}\s*:\s*).*$', re.IGNORECASE | re.MULTILINE)
    if pattern.search(fm_text):
        return pattern.sub(rf'\g<1>{value}', fm_text)
    else:
        return fm_text.rstrip('\n') + f'\n{key}: {value}'

def update_report(path, row):
    """Update a single backtest report .md with values from the results row."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    m = FM_RE.search(content)
    if not m:
        return False  # no frontmatter

    fm_text  = m.group(1)
    rest     = content[m.end():]

    # Read current status — protect ELITE
    _, cur_status = _get_fm_field(fm_text, 'status')
    if cur_status in PROTECTED_STATUSES:
        return False

    sharpe  = round(float(row.get('Sharpe Ratio',  0.0)), 2)
    ret     = round(float(row.get('Total Return',  0.0)), 1)
    mdd     = round(float(row.get('Max Drawdown %', 0.0)), 1)
    wr      = round(float(row.get('Win Rate',       0.0)), 1)
    trades  = int(  float(row.get('Total Trades',   0  )))
    pf      = round(float(row.get('Profit Factor',  1.0)), 2)
    new_status = _status(sharpe)

    fm_text = _set_fm_field(fm_text, 'status',   new_status)
    fm_text = _set_fm_field(fm_text, 'sharpe',   sharpe)
    fm_text = _set_fm_field(fm_text, 'return',   ret)
    # Handle both lowercase and uppercase MDD/PF variants
    if re.search(r'^\s*MDD\s*:', fm_text, re.IGNORECASE | re.MULTILINE):
        fm_text = _set_fm_field(fm_text, 'MDD', mdd)
    else:
        fm_text = _set_fm_field(fm_text, 'mdd', mdd)
    fm_text = _set_fm_field(fm_text, 'win_rate', wr)
    fm_text = _set_fm_field(fm_text, 'trades',   trades)
    if re.search(r'^\s*PF\s*:', fm_text, re.IGNORECASE | re.MULTILINE):
        fm_text = _set_fm_field(fm_text, 'PF', pf)
    else:
        fm_text = _set_fm_field(fm_text, 'pf', pf)

    # Update Performance Table block in body
    perf_pattern = re.compile(
        r'(## Performance Table\s*\n)(.*?)(\n## |\Z)', re.DOTALL
    )
    new_perf = (
        f'## Performance Table\n'
        f'- Sharpe: {sharpe}\n'
        f'- Return: {ret}%\n'
        f'- MDD: {mdd}%\n'
        f'- Win Rate: {wr}%\n'
        f'- Trades: {trades}\n'
        f'- Profit Factor: {pf}\n'
    )
    if perf_pattern.search(rest):
        rest = perf_pattern.sub(
            lambda mo: new_perf + (mo.group(3) if mo.group(3) != '\Z' else ''),
            rest, count=1
        )

    new_content = f'---\n{fm_text}\n---{rest}'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


# ── Main: iterate all report files ───────────────────────────────────────────
updated = skipped = no_match = 0

for fname in sorted(os.listdir(REPORTS_DIR)):
    if not fname.endswith('_backtest.md'):
        continue

    path = os.path.join(REPORTS_DIR, fname)

    # Extract numeric key and class from filename: "{key}_{ClassName}_backtest.md"
    parts = fname.replace('_backtest.md', '').split('_', 1)
    if len(parts) != 2 or not parts[0].isdigit():
        skipped += 1
        continue

    pure_key   = parts[0]
    class_hint = parts[1]  # e.g. "MACDKDJStrategy" or "FORGE_ETH_FVG_TAKER_WR_ATR"

    # Try (key, class_hint) exact match first, then key-only
    sid = key_class_map.get((pure_key, class_hint))
    if sid is None:
        # class_hint might have underscores between words — try the key-only list
        candidates = key_map.get(pure_key, [])
        if len(candidates) == 1:
            sid = candidates[0]
        elif len(candidates) > 1:
            # Pick the first whose class appears in the hint
            for candidate_sid in candidates:
                cfg = next((v for v in STRATEGY_LIBRARY.values() if v['id'] == candidate_sid), None)
                if cfg and cfg['class'].lower() in class_hint.lower():
                    sid = candidate_sid
                    break
            if sid is None:
                sid = candidates[0]  # fallback: first

    if sid is None or sid not in results_map:
        no_match += 1
        continue

    row = results_map[sid]
    if update_report(path, row):
        updated += 1
        print(f'  [OK]   {fname}  →  Sharpe {round(float(row["Sharpe Ratio"]),2):+.2f}  '
              f'Return {round(float(row["Total Return"]),1):+.1f}%')
    else:
        skipped += 1

print(f'\n[FINISH] Updated {updated}  |  Skipped {skipped}  |  No-match {no_match}')

# ── Also overwrite backtest_with_slippage.csv ─────────────────────────────────
import shutil
shutil.copy2(CANONICAL_CSV, SLIPPAGE_CSV)
print(f'[OK] Replaced backtest_with_slippage.csv with fresh results ({len(results_df)} rows)')
