"""
Download OHLCV data for new coins using ccxt (public Binance, no API key needed).
Saves to dataset/{COIN}/{TIMEFRAME}/spot_ohlcv.parquet in the same schema as existing data.

Usage:
  python phase_11/download_coins.py
  python phase_11/download_coins.py --coins LINK AVAX DOT --timeframes 15m 1h
"""

import os
import sys
import time
import argparse
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(_ROOT, 'dataset')

NEW_COINS   = ['LINK', 'AVAX', 'DOT', 'MATIC', 'ADA']
TIMEFRAMES  = ['1h', '15m']
DATE_FROM   = '2023-01-01'
DATE_TO     = '2026-06-16'


def fetch_ohlcv_ccxt(symbol, timeframe, since_str, until_str):
    import ccxt
    exchange = ccxt.binance({'enableRateLimit': True})

    since = exchange.parse8601(since_str + 'T00:00:00Z')
    until = exchange.parse8601(until_str + 'T00:00:00Z')

    all_bars = []
    ts = since
    retries = 0

    while ts < until:
        try:
            bars = exchange.fetch_ohlcv(f'{symbol}/USDT', timeframe, since=ts, limit=1000)
        except Exception as e:
            retries += 1
            if retries > 5:
                raise
            print(f'    Retry {retries} after error: {e}')
            time.sleep(2 ** retries)
            continue

        if not bars:
            break

        retries = 0
        all_bars.extend(bars)
        ts = bars[-1][0] + 1

        last_dt = pd.Timestamp(bars[-1][0], unit='ms').strftime('%Y-%m-%d %H:%M')
        print(f'  {symbol} {timeframe}: {len(all_bars):,} bars → {last_dt}', end='\r', flush=True)

    print()
    df = pd.DataFrame(all_bars, columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df[df['open_time'] < pd.Timestamp(until_str)].copy()
    df['symbol']       = symbol
    df['interval']     = timeframe
    df['ingested_at']  = pd.Timestamp.utcnow()
    return df


def save_parquet(df, coin, timeframe):
    out_dir = os.path.join(DATASET_DIR, coin, timeframe)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'spot_ohlcv.parquet')
    df.to_parquet(path, index=False)
    print(f'  Saved {len(df):,} rows → {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coins',      nargs='+', default=NEW_COINS)
    parser.add_argument('--timeframes', nargs='+', default=TIMEFRAMES)
    parser.add_argument('--date_from',  default=DATE_FROM)
    parser.add_argument('--date_to',    default=DATE_TO)
    args = parser.parse_args()

    print(f'Downloading {len(args.coins)} coins × {len(args.timeframes)} timeframes')
    print(f'Period: {args.date_from} → {args.date_to}')
    print(f'Coins: {args.coins}')
    print(f'Timeframes: {args.timeframes}')
    print('─' * 50)

    errors = []
    for coin in args.coins:
        for tf in args.timeframes:
            out_path = os.path.join(DATASET_DIR, coin, tf, 'spot_ohlcv.parquet')
            if os.path.exists(out_path):
                existing = pd.read_parquet(out_path)
                print(f'[SKIP] {coin}/{tf} already exists ({len(existing):,} rows)')
                continue

            print(f'[{coin}/{tf}] Fetching from Binance...')
            try:
                df = fetch_ohlcv_ccxt(coin, tf, args.date_from, args.date_to)
                if df.empty:
                    print(f'  WARNING: no data returned for {coin}/{tf}')
                    errors.append(f'{coin}/{tf}: empty response')
                    continue
                save_parquet(df, coin, tf)
            except Exception as e:
                print(f'  ERROR: {e}')
                errors.append(f'{coin}/{tf}: {e}')

    print('\n' + '─' * 50)
    if errors:
        print('Errors:')
        for e in errors:
            print(f'  {e}')
    else:
        print('All downloads complete.')


if __name__ == '__main__':
    main()
