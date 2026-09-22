"""
Fetch historical Open Interest for BTCUSDT from Binance (public endpoint, no key needed).
Saves to dataset/BTC/1h/open_interest.parquet

Endpoint: GET https://fapi.binance.com/futures/data/openInterestHist
Max 500 rows per request, 1h period, paginate from 2020-12-01 to today.
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
import pandas as pd
import numpy as np

ROOT  = Path(__file__).parent.parent.parent
OUT   = ROOT / "dataset" / "BTC" / "1h" / "open_interest.parquet"

URL   = "https://fapi.binance.com/futures/data/openInterestHist"
SYM   = "BTCUSDT"
PERIOD = "1h"
LIMIT  = 500

START_MS = int(datetime(2020, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
END_MS   = int(datetime.now(timezone.utc).timestamp() * 1000)


def fetch_chunk(start_ms: int, end_ms: int) -> list[dict]:
    params = {
        "symbol":    SYM,
        "period":    PERIOD,
        "limit":     LIMIT,
        "startTime": start_ms,
        "endTime":   end_ms,
    }
    for attempt in range(5):
        try:
            r = requests.get(URL, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [retry {attempt+1}] {e}")
            time.sleep(2 ** attempt)
    return []


def main():
    print(f"Fetching BTC Open Interest (1h) from Binance...")
    print(f"  Range: {datetime.fromtimestamp(START_MS/1000)} → now")

    rows = []
    cur  = START_MS
    req  = 0

    while cur < END_MS:
        chunk = fetch_chunk(cur, END_MS)
        if not chunk:
            print("  Empty response — stopping.")
            break

        rows.extend(chunk)
        req += 1
        last_ts = chunk[-1]["timestamp"]
        last_dt = datetime.fromtimestamp(last_ts / 1000)

        if req % 10 == 0 or len(chunk) < LIMIT:
            print(f"  req={req:4d}  rows={len(rows):6d}  up to {last_dt}")

        if len(chunk) < LIMIT:
            break

        cur = last_ts + 3_600_000   # advance by 1h in ms
        time.sleep(0.08)            # ~12 req/s, well under rate limit

    if not rows:
        print("No data fetched. Check connectivity.")
        sys.exit(1)

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
    df["oi_contracts"] = pd.to_numeric(df["sumOpenInterest"],      errors="coerce")
    df["oi_usd"]       = pd.to_numeric(df["sumOpenInterestValue"], errors="coerce")
    df = df[["timestamp", "oi_contracts", "oi_usd"]].drop_duplicates("timestamp")
    df = df.sort_values("timestamp").set_index("timestamp")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT)

    print(f"\nSaved {len(df):,} rows → {OUT}")
    print(f"Date range: {df.index.min()} → {df.index.max()}")
    print(df.tail(3))


if __name__ == "__main__":
    main()
