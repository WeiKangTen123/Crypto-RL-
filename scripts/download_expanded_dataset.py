#!/usr/bin/env python3
"""
download_expanded_dataset.py — Ingests 20 additional cryptocurrencies from Binance US
to expand the Crypto-RL backtesting universe to 30 coins.
Format matches dataset/{COIN}/4h/spot_ohlcv.parquet.
"""

import os
import time
import json
import urllib.request
import pandas as pd
from datetime import datetime

TARGET_COINS = [
    'DOGE', 'LTC', 'BCH', 'ATOM', 'XLM', 
    'UNI', 'ETC', 'VET', 'COMP', 'MKR', 
    'BAT', 'ZRX', 'NEO', 'QTUM', 'ONT', 
    'KNC', 'ONE', 'BAND', 'STORJ', 'EGLD'
]

START_TS = 1609430400000  # 2020-12-31 16:00:00 UTC
END_TS = int(time.time() * 1000)

DATASET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dataset'))

def fetch_klines(symbol, interval='4h', start_time=START_TS, end_time=END_TS):
    all_candles = []
    current_start = start_time
    
    print(f"--> Ingesting {symbol} from {datetime.utcfromtimestamp(start_time/1000)}...")
    while True:
        url = f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&startTime={current_start}&limit=1000"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"    [WARN] Error fetching {symbol} at {current_start}: {e}. Retrying in 2s...")
            time.sleep(2)
            continue
            
        if not data:
            break
            
        all_candles.extend(data)
        last_close_time = data[-1][6]
        current_start = last_close_time + 1
        
        if len(data) < 1000 or current_start >= end_time:
            break
            
        time.sleep(0.08)  # Rate limiting
        
    return all_candles

def process_and_save(coin, candles):
    if not candles:
        print(f"    [FAIL] No data for {coin}")
        return False
        
    df = pd.DataFrame(candles, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    
    # Cast types
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['num_trades'] = df['num_trades'].astype(int)
    df['symbol'] = f"{coin}USDT"
    df['interval'] = '4h'
    df['ingested_at'] = pd.Timestamp.utcnow()
    
    # Sort and drop duplicates
    df = df.drop_duplicates(subset=['open_time']).sort_values('open_time').reset_index(drop=True)
    
    out_dir = os.path.join(DATASET_ROOT, coin, '4h')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'spot_ohlcv.parquet')
    
    df.to_parquet(out_path, index=False)
    print(f"    [OK] Saved {len(df)} candles for {coin} to {out_path} ({df['open_time'].min()} to {df['open_time'].max()})")
    return True

def main():
    print(f"=== EXPANDING DATASET TO 30 COINS ===")
    print(f"Destination: {DATASET_ROOT}")
    
    success_count = 0
    for coin in TARGET_COINS:
        symbol = f"{coin}USDT"
        candles = fetch_klines(symbol)
        if process_and_save(coin, candles):
            success_count += 1
            
    print(f"\nFinished: Successfully downloaded {success_count}/{len(TARGET_COINS)} coins.")

if __name__ == '__main__':
    main()
