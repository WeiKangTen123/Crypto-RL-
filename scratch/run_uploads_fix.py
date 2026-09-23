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

TARGETS = ['47', '48', '149', '198', '114', '6_1H', '16', '145', '21', '219']

original_build_payload = sb.build_payload

# We will use a global variable to pass the current sid to the patched function
current_sid = None

import pandas as pd

def patched_build_payload(cfg, events):
    payload = original_build_payload(cfg, events)
    if current_sid is not None:
        # The correct field name according to the updated docs is 'strategy'
        payload['strategy'] = f"strat_{current_sid}"
        
    # Enforce API limits for high resolution candles
    res = payload.get('resolution', '').lower()
    if res in ['1m', '3m', '5m', '15m']:
        cutoff_date = '2025-06-01'
        payload['start'] = cutoff_date
        cutoff_ns = pd.to_datetime(cutoff_date).value
        payload['signals'] = [s for s in payload['signals'] if s['ts'] >= cutoff_ns]
    elif res in ['1h', '2h', '4h']:
        cutoff_date = '2023-06-01'  # Max ~3 years for hourly
        if pd.to_datetime(payload.get('start', '2021-01-01')) < pd.to_datetime(cutoff_date):
            payload['start'] = cutoff_date
            cutoff_ns = pd.to_datetime(cutoff_date).value
            payload['signals'] = [s for s in payload['signals'] if s['ts'] >= cutoff_ns]
            
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
        except requests.exceptions.HTTPError as e:
            res = {'strategy_id': sid, 'status': 'ERROR', 'error': str(e), 'body': getattr(e.response, 'text', '')}
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
