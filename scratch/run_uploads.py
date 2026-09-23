import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Import what we need
from Signal_Replay.submit_batch import process_strategy, load_api_key, SIGNAL_REPLAY_DIR
import Signal_Replay.submit_batch as sb

# Fix the API URL based on usage.MD
sb.API_URL = 'https://btest.abcz-tr.com/api/v1/signals'

TARGETS = ['20', '196', '1', '242', '184', '11', '135', '87', '150', '203']

original_build_payload = sb.build_payload

# We will use a global variable to pass the current sid to the patched function
current_sid = None

def patched_build_payload(cfg, events):
    payload = original_build_payload(cfg, events)
    if current_sid is not None:
        payload['name'] = f"strat_{current_sid}"
    return payload

sb.build_payload = patched_build_payload

def main():
    global current_sid
    results = []
    api_key = load_api_key()
    
    for sid in TARGETS:
        print(f"\n=== #{sid} ===")
        current_sid = sid
        
        try:
            res = process_strategy(sid, api_key, dry_run=False)
        except Exception as e:
            res = {'strategy_id': sid, 'status': 'ERROR', 'error': str(e)}
        print(json.dumps(res, indent=2, default=str))
        results.append(res)

    out_file = SIGNAL_REPLAY_DIR / f'batch_output_custom_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved batch output to {out_file}")

if __name__ == '__main__':
    main()
