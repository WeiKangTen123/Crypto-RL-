"""
Incremental Fetcher for Crypto-RL
Author: @crypto-data-engineer
Description: Loads existing OHLCV parquets, finds the latest timestamp, and fetches missing bars from Binance.
            Includes safety backups and data validation.
"""

import os
import sys
import pandas as pd
import requests
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
TOP_5_TICKERS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
# Using Futures klines endpoint — same OHLCV format as spot, not geo-blocked
BASE_URL = "https://fapi.binance.com/fapi/v1/klines"

# Optional proxy — set HTTPS_PROXY in .env if Binance is geo-blocked
_proxy = os.getenv('HTTPS_PROXY', '').strip()
PROXIES = {'https': _proxy, 'http': _proxy} if _proxy else None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(AGENT_DIR)))
DATASET_DIR = os.path.join(ROOT_DIR, 'dataset')
LOG_FILE = os.path.join(AGENT_DIR, 'logs', 'system_health.log')
ACTIVITY_LOG = os.path.join(AGENT_DIR, 'activity.log')

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')
    with open(ACTIVITY_LOG, 'a') as f:
        f.write(line + '\n')

def fetch_klines(symbol, interval, start_time, limit=1000):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "limit": limit
    }
    for attempt in range(3):
        try:
            response = requests.get(BASE_URL, params=params, timeout=20, proxies=PROXIES)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log(f"  [RETRY] {symbol} {interval} @ {start_time}: {e}")
            time.sleep(2 * (attempt + 1))
    return None

def repair_coin_tf(coin, tf):
    ticker = f"{coin}USDT"
    parquet_path = os.path.join(DATASET_DIR, coin, tf, 'spot_ohlcv.parquet')
    
    if not os.path.exists(parquet_path):
        log(f"  [SKIP] No existing data for {coin}/{tf} at {parquet_path}")
        return False

    log(f"  [REPAIRING] {coin}/{tf} ...")
    
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        log(f"  [ERROR] Failed to read {parquet_path}: {e}")
        return False

    # Ensure open_time is datetime and sorted
    if 'open_time' not in df.columns:
        log(f"  [ERROR] 'open_time' column missing in {coin}/{tf}")
        return False
        
    df['open_time'] = pd.to_datetime(df['open_time'])
    df = df.sort_values('open_time')
    
    last_ts_ms = int(df['open_time'].iloc[-1].timestamp() * 1000)
    current_ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    # 1. Check if we actually need more data
    # (Allow some buffer based on timeframe)
    tf_ms = {
        '1m': 60000, '5m': 300000, '15m': 900000, '30m': 1800000,
        '1h': 3600000, '4h': 14400000, '1d': 86400000
    }
    
    if current_ts_ms - last_ts_ms < tf_ms.get(tf, 60000) * 1.5:
        log(f"  [OK] {coin}/{tf} is already up to date.")
        return True

    # 2. Start Incremental Fetching
    new_klines = []
    fetch_start = last_ts_ms + tf_ms.get(tf, 60000)
    
    log(f"  [FETCHING] Starting from {pd.to_datetime(fetch_start, unit='ms')} ...")
    
    while fetch_start < current_ts_ms:
        klines = fetch_klines(ticker, tf, fetch_start)
        if not klines:
            break
        
        new_klines.extend(klines)
        if len(klines) < 1000:
            break
            
        fetch_start = klines[-1][0] + tf_ms.get(tf, 60000)
        time.sleep(0.1) # Respect rate limits
        
        if len(new_klines) % 5000 == 0:
            log(f"    Downloaded {len(new_klines)} new bars...")

    if not new_klines:
        log(f"  [INFO] No new bars found for {coin}/{tf}")
        return True

    # 3. Process New Data
    new_df = pd.DataFrame(new_klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    
    new_df['open_time'] = pd.to_datetime(new_df['open_time'], unit='ms')
    new_df['close_time'] = pd.to_datetime(new_df['close_time'], unit='ms')
    
    # Cast types to match existing or standard
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 
                    'taker_buy_base_vol', 'taker_buy_quote_vol']
    for col in numeric_cols:
        new_df[col] = new_df[col].astype(float)
    new_df['num_trades'] = new_df['num_trades'].astype(float) # as per Directive 3 and activity log
    
    # 4. Merge and Deduplicate
    final_df = pd.concat([df, new_df]).drop_duplicates(subset=['open_time']).sort_values('open_time')
    
    # 5. Snapshot / Backup
    bak_path = parquet_path + '.bak'
    shutil.copy2(parquet_path, bak_path)
    log(f"  [SNAPSHOT] Created {bak_path}")
    
    # 6. Save
    try:
        final_df.to_parquet(parquet_path, index=False)
        log(f"  [RESULT] Successfully updated {coin}/{tf}. Added {len(new_df)} rows. Total: {len(final_df)} rows.")
        return True
    except Exception as e:
        log(f"  [ERROR] Failed to save {parquet_path}: {e}")
        log(f"  [ROLLBACK] Restoring from backup...")
        shutil.copy2(bak_path, parquet_path)
        return False

def main():
    log("--- INCREMENTAL FETCH START ---")
    for coin in [t.replace('USDT', '') for t in TOP_5_TICKERS]:
        for tf in TIMEFRAMES:
            success = repair_coin_tf(coin, tf)
            if not success:
                log(f"  [FAILED] Could not update {coin}/{tf}")
    log("--- INCREMENTAL FETCH COMPLETE ---")

if __name__ == "__main__":
    main()
