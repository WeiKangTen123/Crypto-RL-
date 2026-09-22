#!/usr/bin/env python3
"""
ingest_macro_and_etf.py — Lead Architect / Crypto-RL
Downloads, synchronizes, and aligns cross-asset macro market map data and
institutional Spot Bitcoin ETF data with crypto 4h candles (2020-12-31 to 2026-09-15).

Assets Ingested:
1. SPY: S&P 500 Equity Index ETF (Equity Lead & Risk-On Proxy)
2. DXY: US Dollar Index (DX-Y.NYB / UUP currency strength)
3. VIX: CBOE Volatility Index (^VIX market panic gauge)
4. JPY: USD/JPY Forex (JPY=X carry-trade unwind detector)
5. IBIT: BlackRock iShares Bitcoin Trust (Post-Jan 2024 Institutional Volume & Flow Proxy)
6. FBTC: Fidelity Wise Origin Bitcoin Fund (Post-Jan 2024 Institutional Volume & Flow Proxy)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
DATASET_DIR = ROOT / 'dataset'

MACRO_TICKERS = {
    'SPY': 'SPY',
    'DXY': 'DX-Y.NYB',
    'VIX': '^VIX',
    'JPY': 'JPY=X',
    'IBIT': 'IBIT',
    'FBTC': 'FBTC'
}

def sync_macro_and_etf():
    btc_path = DATASET_DIR / 'BTC' / '4h' / 'spot_ohlcv.parquet'
    if not btc_path.exists():
        raise FileNotFoundError(f"BTC 4h anchor missing at {btc_path}")

    btc_df = pd.read_parquet(btc_path)
    btc_df['open_time'] = pd.to_datetime(btc_df['open_time']).dt.tz_localize(None)
    full_timeline = pd.DatetimeIndex(sorted(btc_df['open_time'].unique()))
    
    start_date = full_timeline.min()
    end_date = full_timeline.max() + pd.Timedelta(days=2)
    
    print(f"Aligning Macro & ETF data to BTC 4h timeline: {start_date} to {end_date} ({len(full_timeline)} bars)")

    for name, ticker in MACRO_TICKERS.items():
        print(f"--> Fetching {name} ({ticker}) from Yahoo Finance...")
        try:
            raw = yf.download(ticker, start='2020-12-20', end=end_date, interval='1d', progress=False)
        except Exception as e:
            print(f"    [WARN] Failed to fetch {ticker}: {e}")
            continue

        if raw.empty:
            print(f"    [WARN] Empty dataset for {ticker}")
            continue

        # Flatten MultiIndex columns if present
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw = raw.reset_index()
        date_col = 'Date' if 'Date' in raw.columns else raw.columns[0]
        raw[date_col] = pd.to_datetime(raw[date_col]).dt.tz_localize(None)
        raw = raw.rename(columns={
            date_col: 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        raw = raw.drop_duplicates('timestamp').sort_values('timestamp').set_index('timestamp')

        # Compute ETF-specific or Macro-specific institutional turnover & dollar volume
        raw['dollar_volume'] = raw['close'] * raw['volume']
        range_span = (raw['high'] - raw['low']).replace(0, np.nan)
        # Flow proxy: directional signed flow scaled by intraday candle body
        raw['flow_proxy'] = ((raw['close'] - raw['open']) / (range_span.fillna(raw['close'] * 0.01))) * raw['dollar_volume']

        # Reindex onto full 4h crypto timeline
        # First reindex to daily dates then forward fill onto 4h timeline
        resampled_4h = raw.reindex(raw.index.union(full_timeline)).sort_index()
        # Forward fill across intraday crypto bars and weekends/holidays
        resampled_4h = resampled_4h.ffill()
        # For ETFs before their launch date (Jan 2024), fill NaNs with 0.0
        if name in ['IBIT', 'FBTC']:
            resampled_4h['volume'] = resampled_4h['volume'].fillna(0.0)
            resampled_4h['dollar_volume'] = resampled_4h['dollar_volume'].fillna(0.0)
            resampled_4h['flow_proxy'] = resampled_4h['flow_proxy'].fillna(0.0)
            resampled_4h['open'] = resampled_4h['open'].fillna(0.0)
            resampled_4h['high'] = resampled_4h['high'].fillna(0.0)
            resampled_4h['low'] = resampled_4h['low'].fillna(0.0)
            resampled_4h['close'] = resampled_4h['close'].fillna(0.0)
        else:
            # Backfill initial days if needed for macro tickers
            resampled_4h = resampled_4h.bfill()

        # Slice strictly to the full_timeline
        aligned_4h = resampled_4h.loc[full_timeline].copy()
        aligned_4h = aligned_4h.reset_index().rename(columns={'index': 'open_time'})
        aligned_4h['symbol'] = f"{name}USDT"
        aligned_4h['interval'] = '4h'
        aligned_4h['quote_asset_volume'] = aligned_4h['dollar_volume']
        aligned_4h['num_trades'] = 0
        aligned_4h['taker_buy_base_vol'] = 0.0
        aligned_4h['taker_buy_quote_vol'] = 0.0
        aligned_4h['ingested_at'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        out_dir = DATASET_DIR / name / '4h'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / 'spot_ohlcv.parquet'
        aligned_4h.to_parquet(out_file)
        print(f"    [OK] Saved {name}: {len(aligned_4h)} bars ({aligned_4h['open_time'].min()} -> {aligned_4h['open_time'].max()}) to {out_file}")

if __name__ == '__main__':
    sync_macro_and_etf()
