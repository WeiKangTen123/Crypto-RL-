import subprocess
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# IDs of the worst performing strategies, excluding the ones that hang or finished
TARGET_IDS = [
    '45', '123', '207', '65', '6_15M', '69', '92', '96', '199', '81', '58', '179', '141', '103', '136'
]

MAX_PARALLEL = 3  # Number of strategies to tune concurrently

def run_tuner(strat_id):
    print(f"\n🚀 [START] Finetuning Strategy ID: {strat_id}...")
    cmd = [
        "python3", 
        ".gemini/skills/crypto-strategy-tuner/scripts/finetune.py",
        "--strategy", str(strat_id)
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
