import os
import pandas as pd
import requests
from datetime import datetime
import time
from pathlib import Path

# Constants
TOP_5_TICKERS = ['AAVEUSDT']
TIMEFRAMES = ['1d', '1h', '4h', '30m', '15m', '5m', '1m']
# User requested data from 2021
START_DATE_GENERAL = int(datetime(2021, 1, 1).timestamp() * 1000)
START_DATE_1M = int(datetime(2021, 1, 1).timestamp() * 1000) 

def fetch_klines(symbol, interval, start_time):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "limit": 1000
    }
    
    for _ in range(3):
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {symbol} {interval}: {e}. Retrying...")
            time.sleep(2)
    return None

def fetch_and_save_data():
    project_root = Path(__file__).resolve().parent.parent
    dataset_root = project_root / 'dataset'
    
    spike_report = {}

    for interval in TIMEFRAMES:
        print(f"\n--- Processing Timeframe: {interval} ---")
        start_ts = START_DATE_1M if interval == '1m' else START_DATE_GENERAL
        
        for ticker in TOP_5_TICKERS:
            coin = ticker.replace('USDT', '')
            print(f"Fetching {interval} data for {ticker}...")
            
            all_klines = []
            current_start = start_ts
            
            # Fetch full history from start_ts
            while True:
                klines = fetch_klines(ticker, interval, current_start)
                if not klines or len(klines) == 0:
                    break
                    
                all_klines.extend(klines)
                if len(klines) < 1000:
                    break
                current_start = klines[-1][6] + 1
                time.sleep(0.05)
                
                if len(all_klines) % 5000 == 0:
                    print(f"  Downloaded {len(all_klines)} candles...")

            if not all_klines:
                continue
                
            df = pd.DataFrame(all_klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
            ])
            
            df['symbol'] = ticker
            df['interval'] = interval
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['ingested_at'] = datetime.now()
            
            # Simple Spike Detection: (High - Low) / Open > 5% for the candle
            df['pct_change'] = (df['high'] - df['low']) / df['open']
            spikes = df[df['pct_change'] > 0.05] # 5% move in a single candle
            
            if interval not in spike_report: spike_report[interval] = {}
            spike_report[interval][ticker] = len(spikes)

            save_dir = dataset_root / coin / interval
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / 'spot_ohlcv.parquet'
            df.drop(columns=['pct_change']).to_parquet(save_path, index=False)
            print(f"  Saved {len(df)} rows. Spikes (>5%): {len(spikes)}")

    print("\n--- Spike Summary ---")
    for tf, results in spike_report.items():
        print(f"Timeframe {tf}: {results}")

if __name__ == "__main__":
    fetch_and_save_data()
