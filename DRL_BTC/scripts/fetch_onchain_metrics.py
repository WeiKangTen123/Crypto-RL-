"""
Fetch on-chain / sentiment metrics for BTC.

Downloads:
  • Fear & Greed index  (alternative.me — free, no key)

MVRV proxy and cycle features are computed from existing OHLCV data inside
feature_builder._compute_onchain_features() — no extra download needed.

Output: dataset/BTC/1h/onchain_metrics.parquet
  Columns: fng_raw, fng_z60, fng_mom7
  (7-feature expansion happens inside feature_builder using OHLCV)

Usage:
  python -m DRL_BTC.scripts.fetch_onchain_metrics
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_ROOT   = Path(__file__).parent.parent.parent / "dataset" / "BTC" / "1h"
OUTPUT_PATH = DATA_ROOT / "onchain_metrics.parquet"


def _fetch_with_retry(url: str, max_tries: int = 4, pause: float = 3.0) -> dict:
    for attempt in range(max_tries):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == max_tries - 1:
                raise
            print(f"  [retry {attempt+1}/{max_tries}] {e}")
            time.sleep(pause)
    raise RuntimeError("unreachable")


def fetch_fear_greed() -> pd.Series:
    print("Fetching Fear & Greed index from alternative.me …")
    data = _fetch_with_retry("https://api.alternative.me/fng/?limit=3000&format=json")["data"]
    df = pd.DataFrame(data)
    # Convert to naive UTC (matching OHLCV index which is tz-naive)
    df["ts"]    = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.normalize()
    df["value"] = df["value"].astype(float) / 100.0
    s = df.set_index("ts")["value"].sort_index().rename("fng")
    print(f"  F&G: {len(s)} days  ({s.index[0].date()} → {s.index[-1].date()})")
    return s


def build_onchain_parquet() -> None:
    fng_daily = fetch_fear_greed()

    # rolling features on daily series
    fng_daily = fng_daily.to_frame()
    fng_daily["fng_z60"]  = (
        (fng_daily["fng"] - fng_daily["fng"].rolling(60, min_periods=30).mean())
        / fng_daily["fng"].rolling(60, min_periods=30).std().replace(0, np.nan)
    ).clip(-3, 3)
    fng_daily["fng_mom7"] = fng_daily["fng"].diff(7).clip(-0.5, 0.5)

    # shift +1 day: daily value visible only from next day (no lookahead)
    fng_daily = fng_daily.shift(1)

    # load 1h ohlcv index (tz-naive DatetimeIndex) to reindex onto
    ohlcv_path = DATA_ROOT / "spot_ohlcv.parquet"
    ohlcv      = pd.read_parquet(ohlcv_path, columns=["open_time"])
    ohlcv_idx  = pd.to_datetime(ohlcv["open_time"]).sort_values()

    hourly = fng_daily.reindex(ohlcv_idx, method="ffill").bfill()

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    hourly.to_parquet(OUTPUT_PATH)
    print(f"\nSaved {OUTPUT_PATH}")
    print(f"  Shape : {hourly.shape}")
    print(f"  NaN   : {hourly.isna().sum().to_dict()}")
    print(f"  fng sample: {hourly['fng'].describe().round(3).to_dict()}")


if __name__ == "__main__":
    build_onchain_parquet()
