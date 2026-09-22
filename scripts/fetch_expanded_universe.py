import os
import pandas as pd
import requests
from datetime import datetime, timezone
import time
from pathlib import Path

# Configuration
NEW_COINS = ['LINK', 'AVAX', 'DOT', 'MATIC', 'ADA']
NEW_TICKERS = [f"{c}USDT" for c in NEW_COINS]
TIMEFRAMES = ['1d', '4h', '1h', '30m', '15m', '5m', '1m']
START_DATE = int(datetime(2021, 1, 1).timestamp() * 1000)


# Endpoints
SPOT_BASE_URL = "https://api.binance.com/api/v3/klines"
FUTURES_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / 'dataset'

def fetch_klines(symbol, interval, start_time):
    params = {"symbol": symbol, "interval": interval, "startTime": start_time, "limit": 1000}
    for _ in range(3):
        try:
            r = requests.get(SPOT_BASE_URL, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Error fetching klines {symbol} {interval}: {e}. Retrying...")
            time.sleep(2)
    return None

def fetch_funding_rates(symbol, start_time):
    params = {"symbol": symbol, "startTime": start_time, "limit": 1000}
    for _ in range(3):
        try:
            r = requests.get(FUTURES_FUNDING_URL, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Error fetching funding {symbol}: {e}. Retrying...")
            time.sleep(2)
    return None

def download_ohlcv():
    print("\n=== DOWNLOADING OHLCV DATA ===")
    for ticker in NEW_TICKERS:
        coin = ticker.replace('USDT', '')
        for interval in TIMEFRAMES:
            print(f"Processing {coin} {interval}...")
            save_dir = DATASET_ROOT / coin / interval
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / 'spot_ohlcv.parquet'
            
            current_start = START_DATE
            existing_df = None
            
            if save_path.exists():
                try:
                    existing_df = pd.read_parquet(save_path)
                    if not existing_df.empty:
                        print(f"  Existing data starts from {existing_df['open_time'].min()}")
                        # If existing data already covers from START_DATE, we only need to fetch forward
                        if existing_df['open_time'].min() <= pd.Timestamp(START_DATE, unit='ms'):
                            last_ts = int(existing_df['open_time'].max().timestamp() * 1000)
                            current_start = last_ts + 1
                            print(f"  Resuming from forward {existing_df['open_time'].max()}")
                        else:
                            print(f"  Existing data starts LATER than requested. Fetching full range to fill gap.")
                except Exception as e:
                    print(f"  Error reading existing parquet: {e}")
            
            all_klines = []
            while True:
                klines = fetch_klines(ticker, interval, current_start)
                if not klines or len(klines) == 0: break
                all_klines.extend(klines)
                if len(klines) < 1000: break
                current_start = klines[-1][6] + 1
                time.sleep(0.1)
                if len(all_klines) % 5000 == 0: print(f"  Downloaded {len(all_klines)} new candles...")

            if not all_klines:
                print("  No new data found.")
                continue
                
            new_df = pd.DataFrame(all_klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
            ])
            new_df['symbol'] = ticker
            new_df['interval'] = interval
            new_df['open_time'] = pd.to_datetime(new_df['open_time'], unit='ms')
            new_df['close_time'] = pd.to_datetime(new_df['close_time'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                new_df[col] = new_df[col].astype(float)
            
            if existing_df is not None and not existing_df.empty:
                final_df = pd.concat([existing_df, new_df]).drop_duplicates('open_time').sort_values('open_time')
            else:
                final_df = new_df
                
            final_df.to_parquet(save_path, index=False)
            print(f"  Saved {len(final_df)} total rows to {coin}/{interval}/spot_ohlcv.parquet")

def download_funding():
    print("\n=== DOWNLOADING FUNDING RATE DATA ===")
    TIMEFRAME_FREQ = {
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '30m': '30min',
        '1h': '1h',
        '4h': '4h',
        '1d': '1D'
    }
    
    for ticker in NEW_TICKERS:
        coin = ticker.replace('USDT', '')
        print(f"Fetching funding rates for {ticker}...")
        all_funding = []
        current_start = START_DATE
        while True:
            rates = fetch_funding_rates(ticker, current_start)
            if not rates or len(rates) == 0: break
            all_funding.extend(rates)
            if len(rates) < 1000: break
            current_start = int(rates[-1]['fundingTime']) + 1
            time.sleep(0.1)

        if not all_funding: continue
        
        raw = pd.DataFrame(all_funding)
        raw['open_time'] = pd.to_datetime(raw['fundingTime'].astype(int), unit='ms', utc=True)
        raw['funding_rate'] = raw['fundingRate'].astype(float)
        raw = raw[['open_time', 'funding_rate']].sort_values('open_time').drop_duplicates('open_time')
        raw = raw.set_index('open_time')

        for tf in TIMEFRAMES:
            freq = TIMEFRAME_FREQ.get(tf)
            if not freq: continue
            
            # Resample and forward-fill
            idx = pd.date_range(start=raw.index.min(), end=pd.Timestamp.now(tz=timezone.utc), freq=freq)
            aligned = raw.reindex(idx, method='ffill').bfill()
            aligned.index.name = 'open_time'
            aligned = aligned.reset_index()
            aligned['open_time'] = aligned['open_time'].dt.tz_localize(None)
            
            save_dir = DATASET_ROOT / coin / tf
            save_dir.mkdir(parents=True, exist_ok=True)
            aligned.to_parquet(save_dir / 'funding_rate.parquet', index=False)
            print(f"  Saved funding data for {coin} {tf}")

if __name__ == "__main__":
    download_ohlcv()
    download_funding()
    print("\n=== ALL DATA DOWNLOADED SUCCESSFULLY ===")
