"""
check_registration.py
=====================
Audit that every BaseStrategy subclass in strategy_backtest/strategies/
has at least one entry registered in settings.py STRATEGY_LIBRARY.

Exit code 0 = all registered.
Exit code 1 = unregistered classes found (prints them so the agent can act).

Usage:
    python check_registration.py           # just audit
    python check_registration.py --fix     # auto-stub unregistered classes into settings.py
"""
import os, re, sys, ast, textwrap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
STRAT_DIR   = os.path.join(ROOT, 'strategy_backtest', 'strategies')
SETTINGS_PY = os.path.join(ROOT, 'strategy_backtest', 'settings.py')

SKIP_CLASSES = {
    # Templates, scaffolding, freqtrade-format strategies (not compatible with BacktestEngine)
    'BaseStrategy', 'SampleStrategy', 'SimpleTestStrategy', 'TemplateStrategy',
    'GeminiTestStrategy', 'ObSmcReversal', 'LorentzianClassificationMomentumStrategy',
    'IStrategy',
}

# ── 1. Collect all class names from strategy files ──────────────────────────
file_classes: dict[str, str] = {}   # class_name → filename
for fname in sorted(os.listdir(STRAT_DIR)):
    if not fname.endswith('.py') or fname.startswith('__'):
        continue
    fpath = os.path.join(STRAT_DIR, fname)
    for m in re.finditer(r'^class (\w+)', open(fpath).read(), re.MULTILINE):
        cls = m.group(1)
        if cls not in SKIP_CLASSES:
            file_classes[cls] = fname

# ── 2. Collect registered classes from settings.py ──────────────────────────
settings_content = open(SETTINGS_PY).read()
registered_classes: set[str] = set(re.findall(r'"class"\s*:\s*"(\w+)"', settings_content))

# ── 3. Report ────────────────────────────────────────────────────────────────
unregistered = {c: f for c, f in file_classes.items() if c not in registered_classes}

if not unregistered:
    print("✓ All strategy classes are registered in settings.py")
    sys.exit(0)

print(f"✗ {len(unregistered)} unregistered strategy class(es) found:\n")
for cls, fname in sorted(unregistered.items()):
    print(f"  {cls}  ←  {fname}")

if '--fix' not in sys.argv:
    print("\nRun with --fix to auto-stub these into settings.py, then edit the params.")
    sys.exit(1)

# ── 4. Auto-stub mode ────────────────────────────────────────────────────────
# Find the highest existing ID
ids_in_file = [int(x) for x in re.findall(r'^\s{4}"(\d+)"\s*:\s*\{', settings_content, re.MULTILINE)]
next_id = max(ids_in_file) + 1 if ids_in_file else 1

stubs = []
for cls, fname in sorted(unregistered.items()):
    sid = str(next_id)
    stub_id = cls.upper().replace('STRATEGY', '').strip('_') + '_BTC_4H'
    stub = textwrap.dedent(f'''\
        "{sid}": {{
            "id":   "{stub_id}",
            "desc": "AUTO-REGISTERED — update description",
            "class": "{cls}",
            "data": {{"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"}},
            "risk": {{"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                     "trading_fee": 0.0005, "maintenance_margin_rate": 0.005}},
            "params": {{}},
        }},''')
    stubs.append(stub)
    print(f"  → Stubbing {cls} as ID {sid}")
    next_id += 1

# Insert before the closing `}` of STRATEGY_LIBRARY
closing = '\n    }\n'
insert_point = settings_content.rfind(closing)
if insert_point == -1:
    print("ERROR: Could not find STRATEGY_LIBRARY closing brace. Edit settings.py manually.")
    sys.exit(1)

indent = '    '
stub_block = '\n' + '\n'.join(indent + line for stub in stubs for line in stub.splitlines()) + '\n'
new_content = settings_content[:insert_point] + stub_block + settings_content[insert_point:]

# Guard: new content must not have fewer IDs than current
old_ids = set(re.findall(r'^\s{4}"(\d+)"\s*:\s*\{', settings_content, re.MULTILINE))
new_ids = set(re.findall(r'^\s{4}"(\d+)"\s*:\s*\{', new_content, re.MULTILINE))
dropped = old_ids - new_ids
if dropped:
    print(f"ERROR: write aborted — would drop IDs: {sorted(dropped, key=int)}")
    sys.exit(1)

import shutil, time, glob
snap_dir = os.path.join(os.path.dirname(SETTINGS_PY), '.settings_snapshots')
os.makedirs(snap_dir, exist_ok=True)
snap = os.path.join(snap_dir, f'settings_{int(time.time())}.py')
shutil.copy2(SETTINGS_PY, snap)
snaps = sorted(glob.glob(os.path.join(snap_dir, 'settings_*.py')))
for old in snaps[:-5]:
    os.remove(old)

with open(SETTINGS_PY, 'w') as f:
    f.write(new_content)

print(f"\n✓ {len(stubs)} stub(s) added to settings.py — edit params, then run scan_all.py")
sys.exit(0)
