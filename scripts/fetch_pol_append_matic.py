"""
fetch_pol_append_matic.py

MATIC was rebranded to POL in Sep 2024. MATICUSDT was delisted on Binance.
This script fetches POLUSDT bookDepth from 2024-09-04 onwards and appends
it to the existing MATIC order_book_depth.parquet files for all timeframes.
"""
import io
import zipfile
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

POL_TICKER   = 'POLUSDT'
POL_START    = datetime(2024, 9, 5)   # day after MATIC data ends
POL_END      = datetime(2026, 6, 18)

TIMEFRAMES   = {'1m': '1min', '5m': '5min', '15m': '15min',
                '30m': '30min', '1h': '1h', '4h': '4h', '1d': '1D'}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATIC_DIR    = PROJECT_ROOT / 'dataset' / 'MATIC'


def download_daily_depth(date: datetime):
    date_str = date.strftime('%Y-%m-%d')
    url = (f"https://data.binance.vision/data/futures/um/daily/bookDepth/"
           f"{POL_TICKER}/{POL_TICKER}-bookDepth-{date_str}.zip")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    return pd.read_csv(f)
    except Exception:
        pass
    return None


def fetch_pol_raw() -> pd.DataFrame:
    dates = [POL_START + timedelta(days=x)
             for x in range((POL_END - POL_START).days + 1)]
    print(f"Fetching {len(dates)} days of POLUSDT bookDepth...")
    dfs = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(download_daily_depth, dates))
    for i, res in enumerate(results):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(dates)} days...", flush=True)
        if res is not None and not res.empty:
            dfs.append(res)
    if not dfs:
        print("No POLUSDT data found.")
        return pd.DataFrame()
    full = pd.concat(dfs, ignore_index=True)
    full['timestamp'] = pd.to_datetime(full['timestamp'])
    return full


def build_pivot(raw: pd.DataFrame) -> pd.DataFrame:
    pivot = raw.pivot_table(
        index='timestamp',
        columns='percentage',
        values=['depth', 'notional'],
        aggfunc='last',
    )
    pivot.columns = [f"{c[0]}_{c[1]}" for c in pivot.columns]
    return pivot


def append_to_matic(pivot: pd.DataFrame):
    for tf_name, freq in TIMEFRAMES.items():
        parquet_path = MATIC_DIR / tf_name / 'order_book_depth.parquet'
        if not parquet_path.exists():
            print(f"  [{tf_name}] MATIC parquet not found — skipping")
            continue

        existing = pd.read_parquet(parquet_path)
        existing['timestamp'] = pd.to_datetime(existing['timestamp'])
        cutoff = existing['timestamp'].max()

        resampled = pivot.resample(freq).last().ffill().reset_index()
        new_rows  = resampled[resampled['timestamp'] > cutoff]

        if new_rows.empty:
            print(f"  [{tf_name}] No new rows to append")
            continue

        # Align columns — fill any new columns with NaN in existing, and vice versa
        combined = pd.concat([existing, new_rows], ignore_index=True)
        combined = combined.sort_values('timestamp').reset_index(drop=True)
        combined.to_parquet(parquet_path, index=False)
        print(f"  [{tf_name}] Appended {len(new_rows)} rows "
              f"({new_rows['timestamp'].min().date()} → {new_rows['timestamp'].max().date()})")


if __name__ == '__main__':
    print("=== POLUSDT → MATIC append ===")
    raw = fetch_pol_raw()
    if raw.empty:
        print("Nothing to append.")
    else:
        pivot = build_pivot(raw)
        append_to_matic(pivot)
    print("=== DONE ===")
