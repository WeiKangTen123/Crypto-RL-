"""
Download historical BTC futures metrics from Binance bulk data portal.
Saves 1h-resampled parquet with OI, long/short ratio, top trader ratio.

Source: https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/
5-min granularity per day → resampled to 1h.
Available from ~2020-09-01 onwards. No API key required.
"""
from __future__ import annotations

import sys
import time
import zipfile
import io
from pathlib import Path
from datetime import date, timedelta

import requests
import pandas as pd
import numpy as np

ROOT    = Path(__file__).parent.parent.parent
OUT_5M  = ROOT / "dataset" / "BTC" / "1h" / "_metrics_5m_raw.parquet"
OUT_1H  = ROOT / "dataset" / "BTC" / "1h" / "futures_metrics.parquet"

BASE    = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT"
START   = date(2020, 9, 1)
END     = date.today()

COLS = {
    "create_time":                      "ts",
    "sum_open_interest":                "oi_contracts",
    "sum_open_interest_value":          "oi_usd",
    "count_long_short_ratio":           "ls_ratio",       # accounts long vs short
    "count_toptrader_long_short_ratio": "top_ls_ratio",   # top-trader long vs short
    "sum_taker_long_short_vol_ratio":   "taker_ls_vol",   # taker buy/sell vol ratio
}


def fetch_day(d: date) -> pd.DataFrame | None:
    url = f"{BASE}/BTCUSDT-metrics-{d}.zip"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            z   = zipfile.ZipFile(io.BytesIO(r.content))
            df  = pd.read_csv(z.open(z.namelist()[0]), usecols=list(COLS.keys()))
            df  = df.rename(columns=COLS)
            df["ts"] = pd.to_datetime(df["ts"])
            return df
        except Exception as e:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"  [skip] {d}: {e}")
                return None


def main():
    print(f"Downloading BTC futures metrics {START} → {END}")
    print(f"  Source: Binance Data Portal (5-min → resample to 1h)")

    # Load existing raw cache if present
    if OUT_5M.exists():
        existing = pd.read_parquet(OUT_5M)
        last_ts  = existing["ts"].max()
        resume   = last_ts.date() + timedelta(days=1)
        print(f"  Resuming from {resume} (existing: {len(existing):,} rows)")
        frames   = [existing]
    else:
        resume = START
        frames = []

    cur    = resume
    days   = (END - cur).days + 1
    done   = 0

    while cur <= END:
        df = fetch_day(cur)
        if df is not None and len(df) > 0:
            frames.append(df)
        done += 1
        if done % 100 == 0:
            pct = done / days * 100
            print(f"  {done}/{days} days ({pct:.0f}%)  last={cur}")
        cur += timedelta(days=1)
        time.sleep(0.05)   # ~20 req/s

    if not frames:
        print("No data downloaded.")
        sys.exit(1)

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.sort_values("ts").drop_duplicates("ts")
    raw.to_parquet(OUT_5M)
    print(f"\nRaw 5m cache: {len(raw):,} rows  ({raw['ts'].min()} → {raw['ts'].max()})")

    # Resample to 1h
    raw = raw.set_index("ts")
    # OI: take last value in each hour (end-of-period level)
    # Ratios: take mean (average sentiment over the hour)
    h1 = pd.DataFrame({
        "oi_contracts":  raw["oi_contracts"].resample("1h").last(),
        "oi_usd":        raw["oi_usd"].resample("1h").last(),
        "ls_ratio":      raw["ls_ratio"].resample("1h").mean(),
        "top_ls_ratio":  raw["top_ls_ratio"].resample("1h").mean(),
        "taker_ls_vol":  raw["taker_ls_vol"].resample("1h").mean(),
    })
    h1 = h1.ffill().bfill()
    h1.to_parquet(OUT_1H)

    print(f"1h resampled: {len(h1):,} rows  ({h1.index.min()} → {h1.index.max()})")
    print(h1.tail(3))
    print("\nDone →", OUT_1H)


if __name__ == "__main__":
    main()
