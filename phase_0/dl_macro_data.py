import os
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime

def download_macro_data():
    # Configuration
    tickers = {
        'DXY': 'DX-Y.NYB',
        'SPY': 'SPY',
        'VIX': '^VIX',
        'JPY': 'JPY=X'
    }
    
    time_interval = '4h'
    # Get range from existing BTC data to match timeline
    btc_path = Path('dataset/BTC/4h/spot_ohlcv.parquet')
    if not btc_path.exists():
        print("BTC 4h data not found. Cannot match timeline.")
        return
    
    btc_df = pd.read_parquet(btc_path)
    # Ensure open_time is datetime
    btc_df['open_time'] = pd.to_datetime(btc_df['open_time'])
    start_date = btc_df['open_time'].min()
    end_date = btc_df['open_time'].max()
    
    print(f"Target Timeline: {start_date} to {end_date}")
    
    # We use 1d data and forward-fill to match 4h crypto timestamps
    # since intraday Yahoo data is limited to 730 days.
    for coin, yf_ticker in tickers.items():
        print(f"Downloading {coin} ({yf_ticker})...")
        
        # Download 1d data for the full range
        data = yf.download(yf_ticker, start=start_date, end=end_date + pd.Timedelta(days=1), interval='1d')
        
        if data.empty:
            print(f"No data found for {yf_ticker}")
            continue
            
        # Standardize columns
        data = data.reset_index()
        # yfinance columns can be MultiIndex if using certain versions or multiple tickers, 
        # but here we download one by one.
        
        # Flatten columns if necessary
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        data = data.rename(columns={
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Set timestamp as index for reindexing
        data['timestamp'] = pd.to_datetime(data['timestamp']).dt.tz_localize(None)
        data = data.set_index('timestamp')
        
        # Reindex to match BTC 4h timestamps
        # This will create NaNs for non-market hours/days
        full_timeline = btc_df['open_time'].dt.tz_localize(None).unique()
        macro_4h = data.reindex(full_timeline)
        
        # Forward fill missing values (weekends, nights)
        macro_4h = macro_4h.ffill()
        # Backward fill for the very beginning if necessary
        macro_4h = macro_4h.bfill()
        
        # Reset index and prepare for parquet
        macro_4h = macro_4h.reset_index().rename(columns={'index': 'open_time'})
        macro_4h['symbol'] = f"{coin}USDT" # Matching the naming convention
        macro_4h['interval'] = '4h'
        
        # Add dummy columns to match Binance parquet format if needed
        macro_4h['quote_asset_volume'] = 0.0
        macro_4h['num_trades'] = 0
        macro_4h['taker_buy_base_vol'] = 0.0
        macro_4h['taker_buy_quote_vol'] = 0.0
        macro_4h['ingested_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to dataset/{coin}/4h/spot_ohlcv.parquet
        output_dir = Path(f'dataset/{coin}/4h')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'spot_ohlcv.parquet'
        
        macro_4h.to_parquet(output_path)
        print(f"Saved {coin} data to {output_path} ({len(macro_4h)} rows)")

if __name__ == "__main__":
    download_macro_data()
