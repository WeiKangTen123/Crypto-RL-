"""
retune_supertrend2.py
Re-tune all 4 SupertrendPro strategies using subprocess (avoids macOS multiprocessing hang).
Runs them sequentially to keep it simple and stable.
"""

import os, sys, subprocess, json, time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINETUNE_SCRIPT = os.path.join(
    _ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'scripts', 'finetune.py'
)
LOG_FILE = os.path.join(_ROOT, 'utility', 'retune_supertrend_log.jsonl')
TRIALS   = 500

QUEUE = [
    ("20", "SupertrendPro BTC/4h"),
    ("56", "SupertrendPro ETH/4h V1"),
    ("57", "SupertrendPro SOL/4h"),
    ("61", "SupertrendPro ETH/4h V2"),
]

python = sys.executable

print(f"=== SupertrendPro Re-tune: {len(QUEUE)} strategies × {TRIALS} trials (sequential) ===")
print(f"Python: {python}")
print(f"Started: {datetime.now().isoformat()}\n")

for sid, note in QUEUE:
    print(f"\n>>> [{sid}] {note}")
    start = time.time()
    cmd = [
        python, FINETUNE_SCRIPT,
        '--strategy_id', sid,
        '--trials', str(TRIALS),
    ]
    result = subprocess.run(cmd, capture_output=False, cwd=_ROOT)
    elapsed = round(time.time() - start, 1)
    print(f"<<< [{sid}] done in {elapsed}s  exit_code={result.returncode}")

print(f"\n=== ALL DONE === {datetime.now().isoformat()}")
