"""
retune_supertrend.py
Re-tune all 4 SupertrendPro strategies after the multiplier revert and finetune bug fixes.
Uses proper search space via OPTIMIZATION_RANGES on the strategy class.
"""

import os, sys, time, json, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, '.gemini', 'shared'))

FINETUNE_SCRIPT = os.path.join(
    _ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'scripts', 'finetune.py'
)
LOG_FILE = os.path.join(_ROOT, 'utility', 'retune_supertrend_log.jsonl')
TRIALS   = 500
WORKERS  = 4

QUEUE = [
    # (sid, force_trade, roi_weight, note)
    ("20", False, 0.0, "SupertrendPro BTC/4h — reverted to clean defaults"),
    ("56", False, 0.0, "SupertrendPro ETH/4h V1 — reverted to clean defaults"),
    ("57", False, 0.0, "SupertrendPro SOL/4h — reverted to clean defaults"),
    ("61", False, 0.0, "SupertrendPro ETH/4h V2 — reverted to clean defaults"),
]


def _worker(job):
    sid, force_trade, roi_weight, note = job
    start = time.time()

    sys.path.insert(0, _ROOT)
    sys.path.insert(0, os.path.join(_ROOT, '.gemini', 'shared'))

    import importlib.util
    spec = importlib.util.spec_from_file_location("finetune", FINETUNE_SCRIPT)
    ft   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ft)

    try:
        result = ft.run_finetune(
            strategy_id = sid,
            n_trials    = TRIALS,
            force_trade = force_trade,
            roi_weight  = roi_weight,
        )
        elapsed = round(time.time() - start, 1)
        return {
            "sid":         sid,
            "note":        note,
            "status":      "ok",
            "sharpe":      result.get("best_sharpe"),
            "return":      result.get("total_return"),
            "mdd":         result.get("max_drawdown"),
            "trades":      result.get("total_trades"),
            "saved":       result.get("worth_saving"),
            "best_params": result.get("best_params"),
            "elapsed_s":   elapsed,
            "finished_at": datetime.now().isoformat(),
        }
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        return {
            "sid":         sid,
            "note":        note,
            "status":      "error",
            "error":       str(e),
            "trace":       traceback.format_exc()[-800:],
            "elapsed_s":   elapsed,
            "finished_at": datetime.now().isoformat(),
        }


def main():
    print(f"=== SupertrendPro Re-tune: {len(QUEUE)} strategies × {TRIALS} trials ===")
    print(f"Workers: {WORKERS}  |  Started: {datetime.now().isoformat()}")
    print(f"Fixes applied: ret_bonus capped at 500%, auto-expand floor = lo/2, OPTIMIZATION_RANGES enforced\n")

    done = 0
    good = mediocre = errors = 0

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_worker, job): job for job in QUEUE}
        for fut in as_completed(futures):
            r = fut.result()
            done += 1
            with open(LOG_FILE, 'a') as lf:
                lf.write(json.dumps(r) + '\n')

            if r["status"] == "error":
                errors += 1
                print(f"[{done}/{len(QUEUE)}] ERROR   id={r['sid']} — {r['error'][:70]}")
            else:
                s = r.get("sharpe") or 0
                m = r.get("mdd") or 0
                t = r.get("trades") or 0
                ret = r.get("return") or 0
                if s >= 1.0 and t >= 100 and m <= 70:
                    tag = "GOOD ✓"; good += 1
                elif s >= 0.3 and t >= 30:
                    tag = "MEDIOCRE"; mediocre += 1
                else:
                    tag = "BAD"
                print(
                    f"[{done}/{len(QUEUE)}] {tag:<10} id={r['sid']}  "
                    f"sharpe={s:+.2f}  ret={ret:+.1f}%  mdd={m:.1f}%  trades={t}  ({r['elapsed_s']:.0f}s)"
                )
                if r.get("best_params"):
                    print(f"           best_params: {r['best_params']}")

    print(f"\n=== DONE === GOOD={good} MEDIOCRE={mediocre} ERR={errors}")
    print(f"Log: {LOG_FILE}")


if __name__ == '__main__':
    main()
