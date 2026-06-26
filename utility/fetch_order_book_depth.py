import os
import pandas as pd
import requests
import zipfile
import io
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

COINS = ['AAVE', 'ADA', 'AVAX', 'BNB', 'BTC', 'DOT', 'ETH', 'LINK', 'MATIC', 'SOL', 'XRP']
TICKERS = [c + 'USDT' for c in COINS]
TIMEFRAMES = {'1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1h', '4h': '4h', '1d': '1D'}
START_DATE = datetime(2021, 1, 1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / 'dataset'

def download_daily_depth(ticker, date):
    date_str = date.strftime('%Y-%m-%d')
    url = f"https://data.binance.vision/data/futures/um/daily/bookDepth/{ticker}/{ticker}-bookDepth-{date_str}.zip"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                filename = z.namelist()[0]
                with z.open(filename) as f:
                    df = pd.read_csv(f)
                    return df
    except Exception as e:
        pass
    return None

def process_coin(coin):
    ticker = coin + 'USDT'
    
    check_path = DATASET_ROOT / coin / '1d' / 'order_book_depth.parquet'
    if check_path.exists():
        print(f"Skipping {ticker}, already fully processed.")
        return
        
    print(f"Processing {ticker}...")
    
    end_date = datetime.now()
    dates = [START_DATE + timedelta(days=x) for x in range((end_date - START_DATE).days + 1)]
    
    dfs = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = executor.map(lambda d: download_daily_depth(ticker, d), dates)
        for i, res in enumerate(results):
            if i % 100 == 0:
                print(f"  Checked {i}/{len(dates)} days...", flush=True)
            if res is not None and not res.empty:
                dfs.append(res)
                
    if not dfs:
        print(f"No depth data found for {ticker}")
        return
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df['timestamp'] = pd.to_datetime(full_df['timestamp'])
    
    # Pivot so percentages become columns
    pivot_df = full_df.pivot_table(
        index='timestamp', 
        columns='percentage', 
        values=['depth', 'notional'],
        aggfunc='last'
    )
    
    # Flatten columns
    pivot_df.columns = [f"{col[0]}_{col[1]}" for col in pivot_df.columns]
    
    for tf_name, freq in TIMEFRAMES.items():
        print(f"  Resampling {ticker} to {tf_name}...")
        # Take the last snapshot in the period and forward-fill missing periods
        resampled = pivot_df.resample(freq).last().ffill()
        resampled = resampled.reset_index()
        
        save_dir = DATASET_ROOT / coin / tf_name
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / 'order_book_depth.parquet'
        
        resampled.to_parquet(save_path, index=False)
        print(f"  Saved {tf_name} for {ticker} ({len(resampled)} rows)")

if __name__ == "__main__":
    print("=== STARTING ORDER BOOK DEPTH FETCH ===")
    for coin in COINS:
        process_coin(coin)
    print("=== DONE ===")
