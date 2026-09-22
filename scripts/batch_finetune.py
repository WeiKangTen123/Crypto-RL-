"""
batch_finetune.py
Run Optuna fine-tuning for all tunable BAD strategies at 400 trials each.

Groups:
  A  - First-time tune (never run through optimizer)
  B  - Re-tune (previously tuned, borderline metrics)
  C  - Hard re-tune (weak signal, try with roi_weight=0.5)

Flags used per strategy:
  force_trade=True   → soft trade penalty instead of hard cutoff
                       (used when baseline trades < 200 — avoids wasting
                        trials on an impossible 350-trade hard floor)
  roi_weight=0.5     → balanced Sharpe + log-ROI objective
                       (used for Group C where Sharpe is very weak and
                        any positive return is worth capturing)
  min_trades=30      → now the default (fixed from 350) — CLT minimum

Parallel workers: 4 (each runs a separate Optuna study)
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
LOG_FILE = os.path.join(_ROOT, 'utility', 'batch_finetune_log.jsonl')
TRIALS   = 400
WORKERS  = 4

# ── Strategy queue ────────────────────────────────────────────────────────────
# (sid, force_trade, roi_weight, note)
QUEUE = [
    # ── Group A: First-time tune — positive/near-zero Sharpe ─────────────────
    ("135",  True,  0.0, "CGS BTC/4h — 8 trades, chop-gated selective"),
    ("146",  True,  0.0, "OBFC BTC/4h — 46 trades, low MDD"),
    ("14",   True,  0.0, "MACDKDJ ETH/4h — 334 trades, MDD too high"),
    ("59",   True,  0.0, "EMARibbonRSI BTC/1h — 356 trades, borderline Sharpe"),
    ("11",   True,  0.0, "DualEMAVolatility BTC/1d — 13 trades, daily TF"),
    ("145",  True,  0.0, "MDVB BTC/4h — 114 trades, untested params"),
    ("18",   True,  0.0, "MACDKDJ BNB/4h — 157 trades"),
    ("61",   True,  0.0, "SupertrendPro ETH/4h — 101 trades"),
    ("20",   True,  0.0, "SupertrendPro BTC/4h — 101 trades"),
    ("109",  True,  0.0, "ZScoreStatArb BTC/1h — 2 trades, untested"),
    ("99",   True,  0.0, "RSIDivergenceReversal BTC/4h — 37 trades"),

    # ── Group A: First-time tune — medium confidence ──────────────────────────
    ("46",   True,  0.0, "ICTHolyTrinity ETH/1h — 164 trades, never tuned"),
    ("108",  True,  0.0, "InstMomentumBreakout BTC/1h — 128 trades"),
    ("57",   True,  0.0, "SupertrendPro SOL/4h — 47 trades"),
    ("154",  True,  0.0, "MicrostructureEnsemble BTC/1h — 103 trades, low MDD"),
    ("147",  True,  0.0, "HVE SOL/4h — 31 trades"),
    ("139",  True,  0.0, "DumpReversalPeakTrail BTC/4h — 69 trades"),

    # ── Group A: First-time tune — low confidence ─────────────────────────────
    ("56",   True,  0.3, "SupertrendPro ETH/4h — 55 trades, Sharpe -0.76"),
    ("6_30M",True,  0.3, "VRSI BTC/30m — 126 trades, test variant"),
    ("6_1H", True,  0.3, "VRSI BTC/1h — 76 trades, test variant"),
    ("6_15M",True,  0.3, "VRSI BTC/15m — 246 trades, test variant"),
    ("134",  True,  0.3, "KalmanMomentum BTC/4h — 309 trades, Sharpe -0.99"),
    ("140",  False, 0.3, "RSIMeanReversion BTC/4h — 544 trades, MDD 95%"),

    # ── Group B: Re-tune with fresh constraint (previously tuned) ────────────
    ("90",   True,  0.0, "ETHMomentumBreakout BTC/1h — 350 trades, Sharpe 0.29"),
    ("6",    True,  0.0, "VRSI BTC/5m — 45 trades, Sharpe 0.28 (reverted)"),
    ("30",   False, 0.0, "LiqSweepReversal BTC/4h — 576 trades, Sharpe 0.28"),
    ("34",   False, 0.0, "LiqSweepReversal XRP/4h — 569 trades, MDD 74%"),
    ("38",   True,  0.0, "FVGMitigationReversal BTC/4h — 132 trades"),
    ("31",   False, 0.0, "LiqSweepReversal ETH/4h — 666 trades, Sharpe 0.21"),
    ("75",   False, 0.0, "HarmonicDivergence BTC/4h — 556 trades"),
    ("35",   True,  0.0, "VWAPATRReversal BNB/4h — 64 trades"),

    # ── Group C: Hard re-tune — weak signal, roi_weight=0.5 ──────────────────
    ("100",  False, 0.5, "RSIReversion BTC/1h — 355 trades, Sharpe 0.08"),
    ("104",  False, 0.5, "VolPriceCorr BTC/4h — 858 trades, Sharpe 0.05"),
    ("153",  False, 0.5, "FRDS BTC/1h — 465 trades, Sharpe 0.05"),
    ("62",   True,  0.5, "SupertrendPro BNB/4h — 81 trades, Sharpe 0.02"),
    ("84",   True,  0.5, "RWAMomentum ETH/4h — 43 trades, Sharpe 0.02"),
    ("21",   True,  0.5, "KeltnerRSIReversion BTC/1h — 0 trades"),
]


def _worker(job):
    sid, force_trade, roi_weight, note = job
    start = time.time()

    # Import here so each process gets a fresh import (avoid shared state)
    sys.path.insert(0, _ROOT)
    sys.path.insert(0, os.path.join(_ROOT, '.gemini', 'shared'))

    # Dynamic import of finetune module
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
            # min_trades defaults to 30 inside run_finetune (the fix we applied)
        )
        elapsed = round(time.time() - start, 1)
        return {
            "sid":          sid,
            "note":         note,
            "status":       "ok",
            "sharpe":       result.get("best_sharpe"),
            "return":       result.get("total_return"),
            "mdd":          result.get("max_drawdown"),
            "trades":       result.get("total_trades"),
            "saved":        result.get("worth_saving"),
            "elapsed_s":    elapsed,
            "finished_at":  datetime.now().isoformat(),
        }
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        return {
            "sid":         sid,
            "note":        note,
            "status":      "error",
            "error":       str(e),
            "trace":       traceback.format_exc()[-500:],
            "elapsed_s":   elapsed,
            "finished_at": datetime.now().isoformat(),
        }


def main():
    print(f"=== Batch Fine-Tune: {len(QUEUE)} strategies × {TRIALS} trials ===")
    print(f"Workers: {WORKERS}  |  Started: {datetime.now().isoformat()}\n")
    print(f"{'ID':<8} {'Note':<50} force  roi_w")
    print("-" * 72)
    for sid, ft, rw, note in QUEUE:
        print(f"{sid:<8} {note:<50} {'Y' if ft else 'N'}      {rw}")
    print()

    done = 0
    good = mediocre = bad_improved = errors = 0

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_worker, job): job for job in QUEUE}
        for fut in as_completed(futures):
            r = fut.result()
            done += 1
            with open(LOG_FILE, 'a') as lf:
                lf.write(json.dumps(r) + '\n')

            if r["status"] == "error":
                errors += 1
                print(f"[{done:>2}/{len(QUEUE)}] ERROR  id={r['sid']:<6} — {r['error'][:60]}")
            else:
                sharpe = r.get("sharpe", 0) or 0
                trades = r.get("trades", 0) or 0
                mdd    = r.get("mdd", 0) or 0
                saved  = r.get("saved", False)
                if sharpe >= 1.0 and trades >= 100 and mdd <= 70:
                    tag = "GOOD   ✓"; good += 1
                elif sharpe >= 0.3 and trades >= 30:
                    tag = "MEDIOCRE✓"; mediocre += 1
                elif saved:
                    tag = "improved"; bad_improved += 1
                else:
                    tag = "no-save"
                print(
                    f"[{done:>2}/{len(QUEUE)}] {tag:<10} id={r['sid']:<6} "
                    f"sharpe={sharpe:+.2f} ret={r.get('return',0):+.1f}% "
                    f"mdd={mdd:.0f}% trades={trades}  ({r['elapsed_s']:.0f}s)"
                )

    print(f"\n=== DONE ===")
    print(f"GOOD={good}  MEDIOCRE={mediocre}  Improved={bad_improved}  Errors={errors}")
    print(f"Log: {LOG_FILE}")


if __name__ == '__main__':
    main()
