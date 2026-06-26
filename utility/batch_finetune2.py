"""
batch_finetune2.py
Second batch — all 60 BAD strategies not covered by batch_finetune.py.

Covers:
  Phase-1 carry-overs  (4)  — tweaked but still BAD, now run Optuna
  Group E  (27)             — MDD < 70%, some signal worth tuning
  Group D  (29)             — MDD > 70%, structural issues but try anyway

Workers set to 3 so total load with batch 1 stays manageable.
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
LOG_FILE = os.path.join(_ROOT, 'utility', 'batch_finetune2_log.jsonl')
TRIALS   = 400
WORKERS  = 3

# ── Strategy queue ────────────────────────────────────────────────────────────
# (sid, force_trade, roi_weight, note)
QUEUE = [
    # ── Phase-1 carry-overs still BAD — now Optuna ────────────────────────────
    ("1",    True,  0.0, "MACDKDJStrategy BTC/1d — 16 trades, Sharpe +1.19 but too few"),
    ("13",   True,  0.0, "MacroTakerFlow BTC/4h — 25 trades, Phase 1 partial fix"),
    ("36",   True,  0.0, "VWAPATRReversal SOL/4h — 28 trades, near CLT floor"),
    ("106",  True,  0.0, "MTFSupportSniper BTC/5m — 3 trades, extreme selective"),

    # ── Group E: MDD < 70% — recoverable signal ──────────────────────────────
    ("87",   True,  0.0, "VWAPATRReversal BTC/1h — 6 trades, MDD 0.2%"),
    ("79",   False, 0.3, "GridTradingBTC BTC/4h — 125 trades, MDD 2.6%"),
    ("65",   True,  0.3, "MultiTFRSIDivergence BTC/1h — 11 trades, MDD 7.4%"),
    ("8",    True,  0.3, "VRSI BTC/1h — 24 trades, MDD 14.8%"),
    ("149",  False, 0.3, "TIPBreakout ETH/1h — 787 trades, MDD 15.2%"),
    ("131",  False, 0.3, "ForgeStrategy ETH/15m — 543 trades, MDD 18.2%"),
    ("12",   True,  0.3, "VWAPATRReversal BTC/4h — 80 trades, MDD 20.8%"),
    ("7",    True,  0.3, "VRSI BTC/4h — 21 trades, MDD 21.5%"),
    ("157",  False, 0.3, "DVAS SOL/1h — 511 trades, MDD 32.8%"),
    ("71",   False, 0.3, "MeanReversionFunding BNB/4h — 372 trades, MDD 35.8%"),
    ("150",  True,  0.3, "EFRMRStrategy BTC/4h — 33 trades, MDD 37.6%"),
    ("151",  False, 0.3, "LERStrategy BTC/4h — 152 trades, MDD 45.0%"),
    ("73",   False, 0.3, "MeanReversionFunding XRP/4h — 436 trades, MDD 48.3%"),
    ("111",  False, 0.3, "ETHMomentumSqueeze ETH/1h — 282 trades, MDD 55.3%"),
    ("69",   False, 0.3, "VWAPRSIReversion BTC/1h — 429 trades, MDD 58.9%"),
    ("103",  False, 0.5, "DynamicVWAPATRScalper BTC/1h — 374 trades, MDD 58.7%"),
    ("98",   False, 0.3, "ETHMomentumBreakout ETH/1h — 358 trades, MDD 67.2%"),
    ("105",  False, 0.3, "TripleConfirmFVMA BTC/4h — 1058 trades, MDD 64.0%"),
    ("63",   False, 0.3, "OrderBlockSMC BTC/4h — 425 trades, MDD 64.0%"),
    ("158",  False, 0.5, "DVAS BNB/1h — 858 trades, MDD 66.4%"),
    ("10",   False, 0.5, "TIPBreakout BTC/1h — 892 trades, MDD 69.1%"),
    ("143",  False, 0.5, "VRSI SOL/1h — 144 trades, MDD 70.9%"),

    # ForgeStrategy variants — low MDD but deeply negative Sharpe
    ("130",  True,  0.5, "ForgeStrategy BTC/15m — 196 trades, MDD 6.9%, Sharpe -2.99"),
    ("126",  True,  0.5, "ForgeStrategy BTC/5m — 156 trades, MDD 6.8%, Sharpe -9.53"),
    ("127",  False, 0.5, "ForgeStrategy BTC/5m — 355 trades, MDD 13.1%, Sharpe -11.08"),
    ("132",  False, 0.5, "ForgeStrategy BTC/15m — 1716 trades, MDD 53.6%, Sharpe -6.03"),
    ("133",  False, 0.5, "ForgeStrategy BTC/5m — 648 trades, MDD 26.3%, Sharpe -13.87"),

    # ── Group D: MDD > 70% — structural, likely won't pass cap but try ────────
    ("33",   False, 0.5, "LiqSweepReversal SOL/4h — 837 trades, MDD 83.9%"),
    ("3",    True,  0.5, "MACDKDJ_ADX_ATR BTC/4h — 83 trades, MDD 93.9%"),
    ("45",   False, 0.5, "ICTHolyTrinity BTC/1h — 253 trades, MDD 82.4%"),
    ("5",    True,  0.5, "FVGRecovery BTC/1d — 48 trades, MDD 78.4%"),
    ("19",   True,  0.5, "ETHMomentumSqueeze ETH/4h — 60 trades, MDD 79.9%"),
    ("74",   False, 0.5, "HarmonicDivergence BTC/4h — 851 trades, MDD 84.3%"),
    ("72",   False, 0.5, "MeanReversionFunding SOL/4h — 448 trades, MDD 88.9%"),
    ("54",   False, 0.5, "WaveTrendMFI XRP/1h — 1308 trades, MDD 86.5%"),
    ("91",   False, 0.5, "ChoppinessKeltnerBreakout BTC/1h-A — 1015 trades, MDD 83.8%"),
    ("95",   False, 0.5, "ChoppinessKeltnerBreakout BTC/1h-B — 1015 trades, MDD 83.8%"),
    ("67",   False, 0.5, "T3NexusStiff BTC/1h — 510 trades, MDD 96.3%"),
    ("40",   True,  0.5, "DMIADXStrategy SOL/4h — 82 trades, MDD 97.8%"),
    ("39",   False, 0.5, "DMIADXStrategy BNB/4h — 256 trades, MDD 98.5%"),
    ("41",   False, 0.5, "DMIADXStrategy XRP/4h — 398 trades, MDD 99.9%"),
    ("47",   False, 0.5, "AroonRSI BTC/4h — 628 trades, MDD 90.1%"),
    ("43",   False, 0.5, "DynamicSwingVWAP BTC/1h — 833 trades, MDD 87.4%"),
    ("53",   False, 0.5, "WaveTrendMFI BNB/1h — 1384 trades, MDD 91.5%"),
    ("86",   False, 0.5, "TIPBreakout ETH/1h — 2177 trades, MDD 96.0%"),
    ("48",   False, 0.5, "WaveTrendMFI BTC/1h — 1331 trades, MDD 90.4%"),
    ("29",   False, 0.5, "VWAPATRReversal XRP/4h — 1495 trades, MDD 99.3%"),
    ("110",  False, 0.5, "TakerBuyIntensityMomentum BTC/1h — 1317 trades, MDD 91.8%"),
    ("26",   False, 0.5, "EnvelopeMeanReversion BTC/1h — 2663 trades, MDD 98.4%"),
    ("52",   False, 0.5, "WaveTrendMFI ETH/1h — 2517 trades, MDD 99.7%"),
    ("58",   False, 0.5, "ZScoreStatArb BTC/1h — 2672 trades, MDD 99.3%"),
    ("137",  False, 0.5, "ForgeStrategy BTC/15m-B — 1716 trades, MDD 95.6%"),
    ("138",  False, 0.5, "ForgeStrategy BTC/5m-B — 648 trades, MDD 70.6%"),
    ("60",   False, 0.5, "FisherTransform BTC/1h — 8729 trades, MDD 100%"),
    ("107",  False, 0.5, "LorentzianClassification BTC/1h-A — 3664 trades, MDD 100%"),
    ("112",  False, 0.5, "LorentzianClassification BTC/1h-B — 3664 trades, MDD 100%"),
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
            "trace":       traceback.format_exc()[-500:],
            "elapsed_s":   elapsed,
            "finished_at": datetime.now().isoformat(),
        }


def main():
    print(f"=== Batch Fine-Tune 2: {len(QUEUE)} strategies × {TRIALS} trials ===")
    print(f"Workers: {WORKERS}  |  Started: {datetime.now().isoformat()}\n")
    print(f"{'ID':<8} {'Note':<55} force  roi_w")
    print("-" * 78)
    for sid, ft, rw, note in QUEUE:
        print(f"{sid:<8} {note:<55} {'Y' if ft else 'N'}      {rw}")
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
                print(f"[{done:>2}/{len(QUEUE)}] ERROR   id={r['sid']:<8} — {r['error'][:60]}")
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
                    f"[{done:>2}/{len(QUEUE)}] {tag:<10} id={r['sid']:<8} "
                    f"sharpe={sharpe:+.2f} ret={r.get('return',0):+.1f}% "
                    f"mdd={mdd:.0f}% trades={trades}  ({r['elapsed_s']:.0f}s)"
                )

    print(f"\n=== DONE ===")
    print(f"GOOD={good}  MEDIOCRE={mediocre}  Improved={bad_improved}  Errors={errors}")
    print(f"Log: {LOG_FILE}")


if __name__ == '__main__':
    main()
