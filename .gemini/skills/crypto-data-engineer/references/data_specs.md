# Data Engineering Specifications

---

## Dataset Reference
Expected parquet path: `dataset/{COIN}/{TF}/spot_ohlcv.parquet`

**Scope**: Only the 5 crypto trading assets below. Macro data folders (DXY, JPY, SPY, VIX) are used exclusively for DRL model training — do NOT scan, repair, or escalate issues for them.

---

## Timeframe Availability Per Coin

Not all coins have all timeframes. Use this map — do NOT flag a missing folder as an error if it's not listed here.

| Coin | 1m | 5m | 15m | 30m | 1h | 4h | 1d | Notes |
|---|---|---|---|---|---|---|---|---|
| BTC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| ETH | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| BNB | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | No 15m |
| SOL | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | No 15m |
| XRP | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | No 15m |

---

## Expected Bar Counts (Gap Detection)

| Timeframe | Bars per day | Bars per 7 days |
|---|---|---|
| `1m` | 1440 | 10080 |
| `5m` | 288 | 2016 |
| `15m` | 96 | 672 |
| `30m` | 48 | 336 |
| `1h` | 24 | 168 |
| `4h` | 6 | 42 |
| `1d` | 1 | 7 |

---

## Gap Tolerance Rules

| Missing bars | Action |
|---|---|
| ≤ 3 bars in a day | **INFO only** — normal exchange downtime, do not escalate |
| 4–20 bars in a day | **WARN** — log to `activity.log`, do not send inbox |
| > 20 bars in a single day | **STALE** — escalate to `@crypto-fullstack` |
| Full day missing (crypto) | **STALE_CRITICAL** — escalate to `@crypto-fullstack` immediately |

---

## Freshness Rules (STALE_CRITICAL Threshold)

**Crypto assets (BTC, ETH, BNB, SOL, XRP) — 24/7 markets**:
- Latest bar should be within **24 hours** of current time
- If latest bar > 24h ago → `STALE_CRITICAL` → HIGH inbox to `@crypto-fullstack`

**Macro folders (DXY, JPY, SPY, VIX) — IGNORE**:
- Used only for DRL training, not strategy backtesting
- Do NOT scan, do NOT check freshness, do NOT escalate

---

## Column Specifications

### All crypto assets (BTC, ETH, BNB, SOL, XRP)

| Column | Expected dtype | Mandatory | Notes |
|---|---|---|---|
| `Open` | `float64` | ✓ | |
| `High` | `float64` | ✓ | |
| `Low` | `float64` | ✓ | |
| `Close` | `float64` | ✓ | |
| `Volume` | `float64` | ✓ | |
| `taker_buy_base_vol` | `float64` | ✓ | Used by taker-flow strategies |
| `num_trades` | `int64` or `float64` | ✓ | May be stored as float |

**dtype error**: any mandatory column stored as `object` or `StringDtype` → repair with `scripts/repair_dtypes.py` or escalate to `@crypto-fullstack`

---

## Common Numeric Columns Summary
- Mandatory for all crypto: `Open`, `High`, `Low`, `Close`, `Volume`, `taker_buy_base_vol`, `num_trades`
- All must be `float64` (or `int64` for `num_trades`)
- Macro folders (DXY/JPY/SPY/VIX): **out of scope** — do not check

---

## Funding Rate Dataset

### Path
```
dataset/{COIN}/{TF}/funding_rate.parquet
```

### Scope
All 5 crypto assets (BTC, ETH, BNB, SOL, XRP) at **4h** timeframe only.
Binance perpetual futures publish funding every 8h — forward-filled to 4h bars.

### Required Coverage
| Coin | Timeframe | Expected from |
|---|---|---|
| BTC | 4h | 2023-01-01 |
| ETH | 4h | 2023-01-01 |
| BNB | 4h | 2023-01-01 |
| SOL | 4h | 2023-01-01 |
| XRP | 4h | 2023-01-01 |

### Column Specification
| Column | dtype | Notes |
|---|---|---|
| `open_time` | `datetime64` | Aligned to 4h candle open times |
| `funding_rate` | `float64` | Forward-filled from 8h Binance settlements |

### Freshness Rule
- Latest bar must be within **24h** of current time
- If stale → run `scripts/funding_rate_fetcher.py` with VPN connected
- Escalate to `@crypto-fullstack` if VPN fails or fetch errors persist

### Fetcher Script
```
./venv/bin/python .gemini/skills/crypto-data-engineer/scripts/funding_rate_fetcher.py \
  --coins BTC ETH BNB SOL XRP --timeframes 4h \
  --date_from 2023-01-01 --date_to <today>
```
**Always connect VPN first via `scripts/vpn_manager.py connect` before running.**
