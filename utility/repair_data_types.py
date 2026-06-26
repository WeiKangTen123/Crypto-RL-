import pandas as pd
import os
from pathlib import Path
import shutil
from datetime import datetime

DATASET_DIR = Path('dataset')
LOG_FILE = Path('.gemini/skills/crypto-data-engineer/logs/system_health.log')
CHANGES_LOG = Path('.gemini/skills/crypto-data-engineer/changes.log')

def log_message(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{ts}] {msg}\n')
    print(msg)

def log_change(file_path, action, reason):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(CHANGES_LOG, 'a') as f:
        f.write(f'[{ts}] {action} | {file_path} | {reason}\n')

def repair_dtypes():
    log_message("--- STARTING DTYPE REPAIR ---")
    
    for coin_dir in DATASET_DIR.iterdir():
        if not coin_dir.is_dir():
            continue
        
        for tf_dir in coin_dir.iterdir():
            if not tf_dir.is_dir():
                continue
            
            parquet_path = tf_dir / 'spot_ohlcv.parquet'
            if not parquet_path.exists():
                continue
            
            try:
                df = pd.read_parquet(parquet_path)
                modified = False
                
                # Check num_trades
                if 'num_trades' in df.columns and df['num_trades'].dtype != 'float64':
                    df['num_trades'] = df['num_trades'].astype('float64')
                    modified = True
                    log_message(f"  [REPAIR] {coin_dir.name}/{tf_dir.name}: Cast num_trades to float64")
                
                # Check quote_asset_volume
                if 'quote_asset_volume' in df.columns and (df['quote_asset_volume'].dtype == 'object' or isinstance(df['quote_asset_volume'].dtype, pd.StringDtype)):
                    df['quote_asset_volume'] = pd.to_numeric(df['quote_asset_volume'], errors='coerce')
                    modified = True
                    log_message(f"  [REPAIR] {coin_dir.name}/{tf_dir.name}: Cast quote_asset_volume to float64")
                
                if modified:
                    # Snapshot
                    bak_path = str(parquet_path) + '.bak'
                    shutil.copy2(parquet_path, bak_path)
                    log_change(str(parquet_path), "CREATED", "Backup before repair")
                    
                    # Save
                    df.to_parquet(parquet_path)
                    log_message(f"  [OK] Saved {coin_dir.name}/{tf_dir.name}")
                    log_change(str(parquet_path), "REPAIRED", "Cast dtypes to float64")
                    
            except Exception as e:
                log_message(f"  [ERROR] Failed to process {coin_dir.name}/{tf_dir.name}: {e}")

    log_message("--- DTYPE REPAIR COMPLETE ---")

if __name__ == "__main__":
    repair_dtypes()
