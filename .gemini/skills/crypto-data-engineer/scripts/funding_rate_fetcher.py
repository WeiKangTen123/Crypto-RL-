"""
funding_rate_fetcher.py — fetches perpetual futures funding rate history from Binance
and saves to dataset/{COIN}/{TIMEFRAME}/funding_rate.parquet.

Binance publishes funding rates every 8h (00:00, 08:00, 16:00 UTC).
This script forward-fills them to the requested candle timeframe so strategies
can read a `funding_rate` column alongside OHLCV data.

Usage:
    python .gemini/skills/crypto-data-engineer/scripts/funding_rate_fetcher.py
    python .gemini/skills/crypto-data-engineer/scripts/funding_rate_fetcher.py --coins BTC ETH --timeframes 4h 1h
    python .gemini/skills/crypto-data-engineer/scripts/funding_rate_fetcher.py --date_from 2023-01-01
"""

import os
import sys
import time
import argparse
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR   = os.path.dirname(SCRIPT_DIR)
ROOT_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(AGENT_DIR)))
DATASET_DIR = os.path.join(ROOT_DIR, 'dataset')
LOG_FILE    = os.path.join(AGENT_DIR, 'logs', 'system_health.log')
ACTIVITY_LOG= os.path.join(AGENT_DIR, 'activity.log')

load_dotenv(os.path.join(ROOT_DIR, '.env'))

# ── Proxy ────────────────────────────────────────────────────────────────────
_proxy  = os.getenv('HTTPS_PROXY', '').strip()
PROXIES = {'https': _proxy, 'http': _proxy} if _proxy else None

# ── Binance futures endpoint ─────────────────────────────────────────────────
FAPI_BASE = 'https://fapi.binance.com'
FUNDING_ENDPOINT = f'{FAPI_BASE}/fapi/v1/fundingRate'

COIN_TO_SYMBOL = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'BNB': 'BNBUSDT',
    'SOL': 'SOLUSDT',
    'XRP': 'XRPUSDT',
    'AAVE': 'AAVEUSDT',
}

TIMEFRAME_FREQ = {
    '1m':  '1min',
    '5m':  '5min',
    '15m': '15min',
    '30m': '30min',
    '1h':  '1h',
    '4h':  '4h',
    '1d':  '1D',
}


# Shared logger
sys.path.insert(0, '/Users/weikangten/Desktop/Crypto-RL/.gemini/shared')
from logger import log_to_agent

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    log_to_agent('crypto-data-engineer', msg)



def fetch_funding_rates(symbol: str, start_ms: int, end_ms: int) -> list:
    """Fetch all funding rate records between start_ms and end_ms."""
    all_records = []
    cursor = start_ms

    while cursor < end_ms:
        params = {
            'symbol':    symbol,
            'startTime': cursor,
            'endTime':   end_ms,
            'limit':     1000,
        }
        for attempt in range(3):
            try:
                r = requests.get(FUNDING_ENDPOINT, params=params, timeout=20, proxies=PROXIES)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                log(f'  [RETRY {attempt+1}] {symbol}: {e}')
                time.sleep(3 * (attempt + 1))
                data = []

        if not data:
            break

        all_records.extend(data)
        if len(data) < 1000:
            break

        cursor = int(data[-1]['fundingTime']) + 1
        time.sleep(0.2)

    return all_records


def build_funding_parquet(coin: str, timeframe: str, date_from: str, date_to: str, incremental: bool = False):
    symbol   = COIN_TO_SYMBOL.get(coin)
    if not symbol:
        log(f'[SKIP] Unknown coin: {coin}')
        return

    freq = TIMEFRAME_FREQ.get(timeframe)
    if not freq:
        log(f'[SKIP] Unsupported timeframe: {timeframe}')
        return

    out_dir  = os.path.join(DATASET_DIR, coin, timeframe)
    out_path = os.path.join(out_dir, 'funding_rate.parquet')

    # Incremental mode: start from last known bar instead of full re-fetch
    if incremental and os.path.exists(out_path):
        try:
            existing = pd.read_parquet(out_path)
            last_ts  = pd.to_datetime(existing['open_time']).max()
            date_from = last_ts.strftime('%Y-%m-%d')
            log(f'[INCREMENTAL] {coin}/{timeframe} — resuming from {date_from}')
        except Exception as e:
            log(f'[WARN] {coin}/{timeframe} — could not read existing parquet, doing full fetch: {e}')

    start_ms = int(pd.Timestamp(date_from, tz='UTC').timestamp() * 1000)
    end_ms   = int(pd.Timestamp(date_to,   tz='UTC').timestamp() * 1000)

    if start_ms >= end_ms:
        log(f'[OK] {coin}/{timeframe} funding_rate already up to date.')
        return

    log(f'[FETCH] {coin}/{timeframe} funding rates {date_from} → {date_to} ...')
    records = fetch_funding_rates(symbol, start_ms, end_ms)

    if not records:
        log(f'[WARN] No funding rate data returned for {symbol}')
        return

    # Build raw funding rate series (one point per 8h)
    raw = pd.DataFrame(records)
    raw['open_time']    = pd.to_datetime(raw['fundingTime'].astype(int), unit='ms', utc=True)
    raw['funding_rate'] = raw['fundingRate'].astype(float)
    raw = raw[['open_time', 'funding_rate']].sort_values('open_time').drop_duplicates('open_time')
    raw = raw.set_index('open_time')

    # Resample to candle timeframe via forward-fill
    # (funding rate published at T applies until next publication)
    idx = pd.date_range(
        start=pd.Timestamp(date_from, tz='UTC'),
        end=pd.Timestamp(date_to,     tz='UTC'),
        freq=freq,
    )
    aligned = raw.reindex(idx, method='ffill')
    # Also back-fill the very first bars before first funding event
    aligned = aligned.bfill()
    aligned.index.name = 'open_time'
    aligned = aligned.reset_index()

    # Remove timezone info to match spot_ohlcv.parquet convention
    aligned['open_time'] = aligned['open_time'].dt.tz_localize(None)

    os.makedirs(out_dir, exist_ok=True)

    # Merge with existing data if incremental
    if incremental and os.path.exists(out_path):
        try:
            existing = pd.read_parquet(out_path)
            aligned  = pd.concat([existing, aligned]).drop_duplicates('open_time').sort_values('open_time').reset_index(drop=True)
        except Exception:
            pass

    aligned.to_parquet(out_path, index=False)
    log(f'[SAVED] {out_path}  ({len(aligned):,} rows, '
        f'{aligned["open_time"].min().date()} → {aligned["open_time"].max().date()})')


def main(coins=None, timeframes=None, date_from='2023-01-01', date_to=None, incremental=False):
    if date_to is None:
        date_to = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    coins      = coins      or list(COIN_TO_SYMBOL.keys())
    timeframes = timeframes or ['4h']

    mode = 'INCREMENTAL' if incremental else 'FULL'
    log(f'=== FUNDING RATE FETCH START [{mode}] ===')
    for coin in coins:
        for tf in timeframes:
            try:
                build_funding_parquet(coin, tf, date_from, date_to, incremental=incremental)
            except Exception as e:
                log(f'[ERROR] {coin}/{tf}: {e}')
    log('=== FUNDING RATE FETCH COMPLETE ===')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch Binance perpetual futures funding rates')
    parser.add_argument('--coins',      nargs='+', default=['BTC'],
                        help='Coins to fetch (default: BTC)')
    parser.add_argument('--timeframes', nargs='+', default=['4h'],
                        help='Candle timeframes to resample into (default: 4h)')
    parser.add_argument('--date_from',   default='2023-01-01')
    parser.add_argument('--date_to',     default=None)
    parser.add_argument('--incremental', action='store_true',
                        help='Only fetch bars newer than the last bar in the existing parquet')
    args = parser.parse_args()
    main(args.coins, args.timeframes, args.date_from, args.date_to, incremental=args.incremental)
