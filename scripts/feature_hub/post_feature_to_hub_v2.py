import requests
import json

url = "http://localhost:5173/api/catalog/features"
def _load_cred(filename: str, key: str) -> str:
    """Read a credential from the git-ignored 'API & others/' folder."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "API & others" / filename
    if not p.exists():
        raise SystemExit(f"Missing credential file: {p}\nSee 'API & others/README.md'.")
    for line in p.read_text().splitlines():
        line = line.strip()
        if line.startswith(key):
            return line.split("=", 1)[-1].strip()
    return p.read_text().strip()

token = _load_cred("feature_hub_jwt.txt", "TOKEN")
payload = {
    "markdown_content": """---
name: BB-KC Squeeze
id: calc_bb_kc_squeeze
category: Technical
subcategory: Volatility
data_source: internal
status: live
tags: ["volatility", "breakout", "bollinger", "keltner"]
ml_paradigm: ["SL", "RL"]
suitable_coins: ["BTC", "ETH", "SOL"]
timeframes: ["15m", "1h", "4h", "1d"]
author: weikangten
date: 2026-07-17
---

# BB-KC Squeeze

## Description
This feature detects 'Squeeze' periods where Bollinger Bands are fully contained within Keltner Channels, indicating prolonged low volatility and a potential impending breakout.

## Formula

base      : {High, Low, Close}
matrix    : {Bollinger Bands inside Keltner Channels}
condition : {bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5}
output    : {squeeze}  →  {Boolean True/False}

## Suitable Coins
All major pairs (BTC, ETH, SOL)
Not suitable: Stablecoins

## Timeframe
15m, 1h, 4h, 1d

## ML Use
- SL : Predict volatility expansions / breakout direction.
- UL : Regime classification (Low volatility vs High volatility).
- RL : State observation for dynamic position sizing (reduce size during squeeze, increase on breakout).

## Trading Signal
| Condition | Meaning | Bias |
|-----------|---------|------|
| value == True | Squeeze (Coiling) | Watch (Wait for breakout) |

## Works Best
Periods of prolonged consolidation before a macro directional move.

## Avoid
Whipsawing chop markets on very low timeframes (1m, 5m).

## Implementation

```python
import talib

def calc_bb_kc_squeeze(df, bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5):
    upper_bb, mid_bb, lower_bb = talib.BBANDS(df['Close'], timeperiod=bb_period, nbdevup=bb_std, nbdevdn=bb_std)
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=kc_period)
    mid_kc = talib.EMA(df['Close'], timeperiod=kc_period)
    upper_kc = mid_kc + (atr * kc_mult)
    lower_kc = mid_kc - (atr * kc_mult)
    squeeze = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    return squeeze.shift(1)  # shift(1): prevents look-ahead bias
```
"""
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
