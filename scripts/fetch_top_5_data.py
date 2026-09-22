import os
import pandas as pd
import requests
from datetime import datetime
import time
from pathlib import Path

# Constants
TOP_5_TICKERS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
TIMEFRAME = '4h'
# Binance klines limit is 1000 per request. 
# For 4h data from 2017, we need multiple requests.
START_TIMESTAMP = int(datetime(2017, 8, 1).timestamp() * 1000)

def fetch_klines(symbol, interval, start_time):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "limit": 1000
    }
    
    # Try multiple times with backoff
    for _ in range(3):
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {symbol}: {e}. Retrying...")
            time.sleep(2)
    return None

def fetch_and_save_data():
    project_root = Path(__file__).resolve().parent.parent
    dataset_root = project_root / 'dataset'
    
    for ticker in TOP_5_TICKERS:
        coin = ticker.replace('USDT', '')
        print(f"Fetching data for {ticker}...")
        
        all_klines = []
        current_start = START_TIMESTAMP
        
        while True:
            klines = fetch_klines(ticker, TIMEFRAME, current_start)
            if not klines or len(klines) == 0:
                break
                
            all_klines.extend(klines)
            
            # If we got less than 1000, we are at the end
            if len(klines) < 1000:
                break
                
            # Next start time is the close time of the last candle + 1ms
            current_start = klines[-1][6] + 1
            
            # Rate limiting
            time.sleep(0.1)
            
            if len(all_klines) % 5000 == 0:
                print(f"  Downloaded {len(all_klines)} candles...")

        if not all_klines:
            print(f"No data found for {ticker}")
            continue
            
        # Create DataFrame
        # Binance kline format:
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499644799999,      // Close time
        #     "2434.19055334",    // Quote asset volume
        #     308,                // Number of trades
        #     "1756.87402397",    // Taker buy base asset volume
        #     "28.46694368",      // Taker buy quote asset volume
        #     "17928899.62484339" // Ignore
        #   ]
        # ]
        df = pd.DataFrame(all_klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
        ])
        
        # Convert types
        df['symbol'] = ticker
        df['interval'] = TIMEFRAME
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['quote_asset_volume'] = df['quote_asset_volume'].astype(float)
        df['num_trades'] = df['num_trades'].astype(int)
        df['taker_buy_base_vol'] = df['taker_buy_base_vol'].astype(float)
        df['taker_buy_quote_vol'] = df['taker_buy_quote_vol'].astype(float)
        df['ingested_at'] = datetime.now()
        
        # Reorder columns
        cols = [
            'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades', 'taker_buy_base_vol', 
            'taker_buy_quote_vol', 'ingested_at'
        ]
        df = df[cols]
        
        # Create directory
        save_dir = dataset_root / coin / TIMEFRAME
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to parquet
        save_path = save_dir / 'spot_ohlcv.parquet'
        df.to_parquet(save_path, index=False)
        print(f"Successfully saved {len(df)} rows to {save_path}")

if __name__ == "__main__":
    fetch_and_save_data()
