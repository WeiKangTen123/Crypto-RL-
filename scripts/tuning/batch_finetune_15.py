import subprocess
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET_IDS = [
    '106', '201', '68', '131', '63', '229', '238', '70', '44', '180', '212', '162', '232', '129', '140'
]

MAX_PARALLEL = 3  # Number of strategies to tune concurrently

def run_tuner(strat_id):
    print(f"\n🚀 [START] Finetuning Strategy ID: {strat_id}...")
    cmd = [
        "python", 
        ".gemini/skills/crypto-strategy-tuner/scripts/finetune.py",
        "--strategy_id", str(strat_id)
    ]
    
    try:
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            check=True,
            cwd="/Users/weikangten/Desktop/Crypto-RL",
            capture_output=True,
            text=True
        )
        print(f"✅ [DONE] Strategy {strat_id} tuning completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ [ERROR] Strategy {strat_id} failed. Return code: {e.returncode}")
        # Print the last few lines of stderr to help diagnose
        err_lines = e.stderr.strip().split('\n')[-5:]
        print(f"   Stderr snippet: {' | '.join(err_lines)}")
        return False
    except Exception as e:
        print(f"❌ [UNEXPECTED] Strategy {strat_id} error: {e}")
        return False

def main():
    print(f"Starting PARALLEL batch tuning for {len(TARGET_IDS)} strategies...")
    print(f"Running {MAX_PARALLEL} tuners concurrently to speed up the process.\n")
    
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        # Submit all tasks
        futures = {executor.submit(run_tuner, sid): sid for sid in TARGET_IDS}
        
        # Process as they complete
        for future in as_completed(futures):
            sid = futures[future]
            try:
                success = future.result()
            except Exception as exc:
                print(f"Strategy {sid} generated an exception: {exc}")

    print("\n🏁 ALL PARALLEL FINETUNING TASKS COMPLETE!")

if __name__ == "__main__":
    main()
