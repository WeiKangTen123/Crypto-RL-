import json
import subprocess
import time
import os

SCAN_RESULTS = ".gemini/skills/crypto-strategy-tuner/data/scan_results.json"
FINETUNE_SCRIPT = ".gemini/skills/crypto-strategy-tuner/scripts/finetune.py"

def get_bad_strategies():
    if not os.path.exists(SCAN_RESULTS):
        return []
    with open(SCAN_RESULTS, "r") as f:
        data = json.load(f)
    bad_ids = []
    for item in data.get("results", []):
        if item.get("grade") == "BAD":
            bad_ids.append(item.get("id"))
    return bad_ids

def main():
    bad_ids = get_bad_strategies()
    print(f"Found {len(bad_ids)} BAD strategies.")
    
    for i, strat_id in enumerate(bad_ids):
        print(f"\n[{i+1}/{len(bad_ids)}] Finetuning Strategy ID: {strat_id} ...")
        cmd = ["python", FINETUNE_SCRIPT, "--strategy_id", strat_id]
        
        # Run finetune
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error finetuning {strat_id}: {e}")
            print(e.stdout)
            print(e.stderr)
            
        time.sleep(1) # brief pause

if __name__ == "__main__":
    main()
