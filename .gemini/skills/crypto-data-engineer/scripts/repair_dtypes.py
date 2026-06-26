import os
import shutil
import pandas as pd
import json
from datetime import datetime

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(AGENT_DIR)))
FULLSTACK_INBOX = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-fullstack', 'inbox')
RESEARCHER_INBOX = os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-researcher', 'inbox')

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}')

def repair_file(file_path):
    if not os.path.exists(file_path):
        log(f'File not found: {file_path}')
        return False
    
    bak_path = file_path + '.bak'
    if not os.path.exists(bak_path):
        shutil.copy2(file_path, bak_path)
        log(f'Created backup: {bak_path}')
    
    try:
        df = pd.read_parquet(file_path)
        changed = False
        
        # Target columns for correction
        targets = ['taker_buy_base_vol', 'num_trades', 'taker_buy_quote_vol']
        for col in targets:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    log(f'  Correcting {col} in {os.path.basename(file_path)}')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    changed = True
        
        if changed:
            df.to_parquet(file_path)
            log(f'  Successfully repaired {file_path}')
            return True
        else:
            log(f'  No correction needed for {file_path}')
            return False
            
    except Exception as e:
        log(f'  Error repairing {file_path}: {e}')
        return False

def run_repair():
    # Find the latest integrity issue message
    messages = sorted([f for f in os.listdir(FULLSTACK_INBOX) if 'DATA_INTEGRITY_ISSUE' in f])
    if not messages:
        log('No integrity issue messages found in fullstack inbox.')
        return
    
    latest_msg = os.path.join(FULLSTACK_INBOX, messages[-1])
    with open(latest_msg) as f:
        data = json.load(f)
    
    errors = data.get('context', {}).get('errors', [])
    log(f'Found {len(errors)} files to repair.')
    
    repaired_count = 0
    for err in errors:
        fpath = err.get('file')
        if repair_file(fpath):
            repaired_count += 1
    
    log(f'Repaired {repaired_count} files.')
    
    # Notify agents
    if repaired_count > 0:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        notify_payload = {
            'from': 'crypto-data-engineer',
            'priority': 'LOW',
            'topic': 'DATA_REPAIRED',
            'message': f'Auto-repaired {repaired_count} parquet files with DTYPE_ERROR (cast to numeric).',
            'context': {
                'count': repaired_count,
                'repaired_files': [e.get('file') for e in errors]
            }
        }
        
        for agent in ['crypto-fullstack', 'alpha-researcher']:
            path = os.path.join(ROOT_DIR, '.gemini', 'skills', agent, 'inbox', f'{ts}_from_data-engineer_DATA_REPAIRED.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(notify_payload, f, indent=2)

        log('Sent DATA_REPAIRED notifications to fullstack and researcher agents.')
        
        # Delete the original error message since it's handled
        os.remove(latest_msg)
        log('Removed handled integrity issue message.')

if __name__ == '__main__':
    run_repair()
