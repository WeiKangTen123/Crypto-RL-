import requests
import json

# Replace this with the actual base URL of the Feature Hub API
FEATURE_HUB_API_URL = "http://localhost:8000/api/v1/features"
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

API_TOKEN = _load_cred("factorhub_api.txt", "API_TOKEN")
markdown_payloads = [
    """---
name: Volume-Weighted RSI (VRSI)
id: calc_vrsi
category: Technical
tags: [momentum, volume, rsi, exhaustion]
ml_paradigm: [SL, UL, RL]
author: weikangten
date: 2026-07-16
---

# Volume-Weighted RSI (VRSI)

## Formula

base      : {Close, Volume}
matrix    : {Volume-weighted price changes smoothed over period}
condition : {period=14}
output    : {vrsi}  →  {0 to 100}

## Suitable Coins
BTC, ETH, and high-volume large-cap altcoins.
Not suitable: Low volume or illiquid coins with erratic volume spikes.

## Timeframe
15m, 1H, 4H, 1D

## ML Use
- SL : Use as a feature to predict mean-reversion probabilities or volume-exhaustion.
- UL : Clustering market regimes (e.g., high vs low volume momentum).
- RL : Continuous state observation representing overbought/oversold conditions scaled by volume.

## Trading Signal
| Condition | Meaning | Bias |
|-----------|---------|------|
| value > 80 | Overbought (Volume exhaustion) | Short / Watch |
| value < 20 | Oversold (Volume exhaustion) | Long / Watch |

## Works Best
Trending markets that are reaching exhaustion, or well-defined mean-reverting ranges.

## Avoid
Low liquidity environments or immediately after news events with abnormal volume anomalies.

## Implementation

```python
# calc_vrsi | inputs: Close, Volume | output: 0 to 100
def calc_vrsi(df, period=14):
    price_chg = df['Close'].diff()
    U = df['Volume'] * price_chg.clip(lower=0)
    D = df['Volume'] * (-price_chg).clip(lower=0)
    sma_u = U.rolling(window=period, min_periods=period).mean()
    sma_d = D.rolling(window=period, min_periods=period).mean()
    rs = sma_u / (sma_d + 1e-10)
    result = 100.0 - (100.0 / (1.0 + rs))
    return result.shift(1)  # shift(1): prevents look-ahead bias
```
""",
    """---
name: BB-KC Squeeze
id: calc_bb_kc_squeeze
category: Technical
tags: [volatility, breakout, bollinger, keltner]
ml_paradigm: [SL, RL]
author: weikangten
date: 2026-07-16
---

# BB-KC Squeeze

## Formula

base      : {High, Low, Close}
matrix    : {Bollinger Bands inside Keltner Channels}
condition : {bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5}
output    : {squeeze}  →  {Boolean True/False}

## Suitable Coins
All major pairs (BTC, ETH, SOL, AVAX)
Not suitable: Stablecoins

## Timeframe
1H, 4H, 1D

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
# calc_bb_kc_squeeze | inputs: High, Low, Close | output: Boolean
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
]

def post_feature():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "text/plain"
    }

    for idx, payload in enumerate(markdown_payloads):
        try:
            response = requests.post(FEATURE_HUB_API_URL, headers=headers, data=payload.encode('utf-8'))
            print(f"Feature {idx+1} -> Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error posting feature {idx+1}: {e}")


if __name__ == "__main__":
    post_feature()
