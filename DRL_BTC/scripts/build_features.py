"""
CLI to precompute the multi-TF feature matrix.

Run once before training:
  cd /Users/weikangten/Desktop/Crypto-RL
  python DRL_BTC/scripts/build_features.py

Saves to DRL_BTC/data/features/features.parquet  and  close.parquet.
Re-running overwrites the cache.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.features.feature_builder import save_features

if __name__ == "__main__":
    t0 = time.time()
    feats, close = save_features()
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"Feature columns ({feats.shape[1]}):")
    for i, col in enumerate(feats.columns):
        print(f"  {i+1:3d}. {col}")
    print(f"\nDate range: {feats.index[0]} → {feats.index[-1]}")
    print(f"NaN rows  : {feats.isnull().any(axis=1).sum()} / {len(feats)}")
