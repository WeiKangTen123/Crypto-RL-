# Phase 10 — Quantitative Pairs Trading System Flow
> Last updated: 2026-06-17 (pure Z-score formula, parameter optimisation, results.json updated)
> Statistical arbitrage across 10 BTC/ETH/BNB/SOL/XRP pairs using OLS hedge ratio + Z-score mean reversion

---

## OVERVIEW

Phase 10 answers a single question:
> *"When two cointegrated coins' price spread is statistically stretched, will it snap back?"*

It is **not** directional trading. It finds two coins that move together historically (cointegrated), sizes a dollar-neutral long/short spread between them, and exits when the spread mean-reverts. The strategy is market-direction agnostic — it profits from the spread closing, not from BTC going up or down.

**Core principle:**
- Find pairs where `log(Price_A) - β × log(Price_B)` is stationary (Augmented Dickey-Fuller test)
- When the spread Z-score diverges ≥ 2.5σ from its rolling mean → open a position
- When the Z-score crosses back through zero → close (pure mean reversion exit)

**This is NOT reverse-correlation trading.** Both coins trend in the same direction. The edge comes from the temporary over-extension of the ratio between them.

---

## SYSTEM ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 10 — PAIRS TRADING                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    Dashboard (phase_10/dashboard/index.html)           │  │
│  │                                                                        │  │
│  │  Backtest Control ── Run All / Run Single Pair / Stop                  │  │
│  │  Monitor window   ── live stdout progress stream                        │  │
│  │  Pairs table      ── 10 pairs, sortable, click for detail               │  │
│  │  Detail panel     ── 6 tabs per pair (Metrics / Equity / Pairs Dance /  │  │
│  │                       Z-Score / Trade Log / Per-Leg Breakdown)          │  │
│  └─────────────────────────────────┬──────────────────────────────────────┘  │
│                                    │ HTTP                                     │
│                                    ▼                                          │
│                  ┌─────────────────────────────────────┐                     │
│                  │       main_controller/main.py        │  Flask API          │
│                  │                                     │                     │
│                  │  POST /api/phase_10/run_backtest    │                     │
│                  │  GET  /api/phase_10/status          │                     │
│                  │  POST /api/phase_10/stop            │                     │
│                  │  GET  /api/phase_10/results         │                     │
│                  └──────────────┬──────────────────────┘                     │
│                                 │ subprocess                                  │
│                                 ▼                                             │
│                  ┌─────────────────────────────────────┐                     │
│                  │       phase_10/backtest.py           │  Runner             │
│                  │                                     │                     │
│                  │  for each pair in PAIRS:            │                     │
│                  │    run_pair_backtest()              │                     │
│                  │  save → phase_10/data/results.json  │                     │
│                  └──────────────┬──────────────────────┘                     │
│                                 │ calls                                       │
│                                 ▼                                             │
│                  ┌─────────────────────────────────────┐                     │
│                  │       phase_10/engine.py             │  Core Engine        │
│                  │                                     │                     │
│                  │  ① load_pair_data()                │                     │
│                  │  ② compute_rolling_hedge_and_spread │ OLS hedge ratio     │
│                  │  ③ adfuller()                       │ cointegration test  │
│                  │  ④ compute_half_life()              │ OU speed            │
│                  │  ⑤ compute_zscore_and_bands()       │ spread Z-score      │
│                  │  ⑥ bar-by-bar trade simulation      │ entry / exit logic  │
│                  │  ⑦ compute metrics + return dict    │                     │
│                  └─────────────────────────────────────┘                     │
│                                                                              │
│  Dataset: dataset/{COIN}/1h/spot_ohlcv.parquet  (5 coins × 1h bars)         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## KEY FILES

| File | Role |
|---|---|
| `phase_10/engine.py` | Core engine — OLS, ADF, Z-score, trade simulation, metrics |
| `phase_10/backtest.py` | CLI runner — loops all pairs, saves `results.json` |
| `phase_10/dashboard/index.html` | Full dashboard UI |
| `phase_10/dashboard/app.js` | Dashboard JS — fetch, render, charts |
| `phase_10/dashboard/styles.css` | Dashboard styles |
| `phase_10/data/results.json` | Latest backtest output (10 pairs) |
| `phase_10/data/optimize_results.json` | Grid search output (for reference) |
| `phase_10/optimize.py` | Grid search optimizer (OLS × ZSCORE × MIN_Z × STOP × HOLD) |
| `phase_10/_tune.py` | Targeted 9-config comparison around stop/R² variations |
| `phase_10/_tune2.py` | Hold period + extreme stop comparison |
| `main_controller/main.py` | Flask routes for Phase 10 API |

---

## ENGINE PARAMETERS (Current — Pure Z-Score Optimised)

These constants live at the top of `phase_10/engine.py`. All time windows are in **bars at 1h timeframe** — they scale automatically when using different timeframes.

### Core windows
| Constant | Value | Meaning |
|---|---|---|
| `OLS_WINDOW` | **120** bars (120h) | Rolling OLS lookback for hedge ratio β |
| `ZSCORE_WINDOW` | **48** bars (48h) | Rolling mean/std for Z-score normalisation |
| `BB_WINDOW` | 20 bars | Bollinger Band on Z (visualization only — not used in trading logic) |
| `BB_STD` | 2.0 | BB multiplier (visualization only) |

### Entry/Exit thresholds
| Constant | Value | Meaning |
|---|---|---|
| `MIN_ENTRY_Z` | **2.5** σ | Minimum Z-score to trigger entry |
| `MAX_ENTRY_Z` | **7.9** σ | Maximum Z-score at entry (= Z_STOP_LOSS − 0.10) |
| `Z_STOP_LOSS` | **8.0** σ | Hard exit if spread diverges to 8σ |
| `EXIT_ZSCORE` | 0.0 | Disabled — pure formula exits at Z=0, not earlier |
| `MIN_R2` | **0.80** | OLS R² quality gate — rejects weak hedge ratio fits |

### Timing & cooldown
| Constant | Value | Meaning |
|---|---|---|
| `COOLDOWN_BARS` | 6 bars (6h) | Minimum gap between trades |
| `MIN_HOLD_BARS` | 2 bars | Minimum hold before allowing mean-revert exit |
| Max hold | `half_life × 2` | Per-pair computed from OU half-life (~17–22h typically) |

### Enhancement flags
| Constant | Value | Meaning |
|---|---|---|
| `CONFIRM_TURN` | True | Entry only after Z starts moving back toward mean (turning point filter) |
| `REVERSAL_TRAIL_Z` | 0.5 | Trailing stop distance after Z crosses zero (locks in profit) |
| `ZSTOP_CIRCUIT_BREAKER` | 2 | Pause entries after 2 consecutive Z_STOP exits |
| `ZSTOP_PAUSE_BARS` | 360 bars (~15 days) | Duration of circuit-breaker pause |

### Other
| Constant | Value | Meaning |
|---|---|---|
| `CAPITAL_PER_LEG` | $1,000 USD | Capital allocated to each leg (A or B); $2,000 total per trade |
| `TRADING_FEE` | 0.05% | Taker fee per leg; 4 legs per round-trip = 0.20% total fee drag |
| `ADF_PVALUE_MAX` | 0.05 | ADF p-value threshold for initial cointegration test |
| `ROLLING_ADF_BARS` | 72 bars | Re-run ADF every 72 bars to detect regime breakdown |
| `ROLLING_ADF_PVAL` | 0.10 | ADF p-value threshold for rolling regime check |

---

## THE ALGORITHM — STEP BY STEP

### Step 1: Load & Align Data
```
load_pair_data(coin_a, coin_b, dataset_dir, date_from, date_to, tf='1h')
    ↓ load spot_ohlcv.parquet for each coin
    ↓ align on inner-join timestamps (both coins must have data at same bar)
    ↓ drop NaNs → merged DataFrame with Close_A, Close_B
```

### Step 2: Rolling OLS Hedge Ratio
```
compute_rolling_hedge_and_spread(log_A, log_B, window=120)
    ↓ For each bar i ≥ 120:
        log(P_A[i-120:i]) = α + β × log(P_B[i-120:i]) + ε   ← OLS regression
        spread[i] = log(P_A[i]) - (α + β × log(P_B[i]))      ← current residual
        r2[i] = R² of the in-window regression
    ↓ Returns: beta[], alpha[], spread[], r2[]
```

The hedge ratio β tells us how many dollars of coin B to short/long per dollar of coin A, ensuring the portfolio is dollar-neutral.

### Step 3: Cointegration Test (ADF)
```
in-sample spread = spread over first 60% of data
adfuller(is_spread, maxlag=1)  →  p-value
cointegrated = (p_value < 0.05)
```

ADF null hypothesis: "spread has a unit root (non-stationary)". Reject it (p < 0.05) = the spread is stationary = the pair is cointegrated.

Also computed: **Ornstein-Uhlenbeck half-life** — median half-life across overlapping 500-bar windows. Measures how fast the spread mean-reverts. Used to set `max_hold = half_life × 2`.

### Step 4: Z-Score
```
compute_zscore_and_bands(spread, zscore_window=48, bb_window=20, bb_std=2.0)
    ↓ For each bar i ≥ 48:
        mu  = mean(spread[i-48:i])
        sig = std(spread[i-48:i])
        Z[i] = (spread[i] - mu) / sig     ← how many σ from rolling mean
    ↓ BB bands computed on Z (for dashboard visualization only — NOT used in trading)
```

Z = 0 means spread is at its rolling mean.
Z = +2.5 means spread is 2.5 standard deviations ABOVE mean → coin A is expensive relative to B.
Z = −2.5 means spread is 2.5σ BELOW mean → coin B is expensive relative to A.

### Step 5: Rolling ADF Regime Filter
Every 72 bars, re-run ADF on the most recent `OLS_WINDOW` bars of spread.
If p-value ≥ 0.10 → set `regime_ok = False` → block new entries until cointegration is restored.
This protects against pairs that were cointegrated in-sample but break down out-of-sample.

### Step 6: Bar-by-Bar Trade Simulation

#### Entry conditions (ALL must be true):
```
1. not in_trade
2. current_regime_ok == True        (rolling ADF passed)
3. circuit_ok == True               (not in ZSTOP_CIRCUIT_BREAKER pause)
4. Z is not NaN
5. R² ≥ MIN_R2 (0.80)              (hedge ratio quality gate)
6. MIN_ENTRY_Z ≤ |Z| ≤ MAX_ENTRY_Z  (2.5σ to 7.9σ)
7. bars since last exit ≥ COOLDOWN_BARS (6 bars)
8. CONFIRM_TURN: Z already turning back toward 0
     (Z > 2.5 AND Z[i] < Z[i-1])   ← peaked and falling
     OR
     (Z < −2.5 AND Z[i] > Z[i-1])  ← bottomed and rising
```

#### Trade direction:
```
Z > 0  →  trade_side = −1  →  SHORT spread:  SHORT coin A,  LONG coin B
Z < 0  →  trade_side = +1  →  LONG spread:   LONG coin A, SHORT coin B
```

#### Position sizing:
```
size_a = CAPITAL_PER_LEG / price_A            # $1,000 worth of coin A
size_b = abs(β) × CAPITAL_PER_LEG / price_B  # β × $1,000 worth of coin B (hedge ratio sized)
```

The hedge ratio β makes the position dollar-neutral: gains on one leg are roughly offset by losses on the other when spread is NOT moving.

#### Exit conditions (first matching reason wins):
| Priority | Condition | Reason |
|---|---|---|
| 1 | `|Z| ≥ Z_STOP_LOSS (8.0)` | `Z_STOP` — spread diverged further |
| 2 | Reversal trail armed (Z over-shot mean by ≥ 0.5σ then snapped back) | `REVERSAL_TRAIL` — lock in profit |
| 3 | `hold ≥ min_hold_bars` AND `Z` crosses through zero | `MEAN_REVERT` — pure exit ← primary exit |
| 4 | `hold ≥ max_hold (half_life × 2)` | `TIME_STOP` — held too long |
| 5 | Z reverses past entry threshold on the wrong side | `REVERSAL` — spread went the other way |

**MEAN_REVERT is the primary exit** — this is the pure pairs trading formula. When Z crosses 0, the spread has returned to its rolling mean and the trade thesis has completed.

#### Fee model:
```
4 legs per round-trip:
  open:  fee_a = size_a × price_A × 0.05%
         fee_b = size_b × price_B × 0.05%
  close: exit_fee_a = size_a × exit_price_A × 0.05%
         exit_fee_b = size_b × exit_price_B × 0.05%
total_fee = fee_a + fee_b + exit_fee_a + exit_fee_b   ← ~0.20% drag per round-trip
```

---

## TRADING LOGIC FLOWCHART

```
Every 1h bar:
│
├─ ENTRY gate ──────────────────────────────────────────────────────────
│   regime_ok? ─── NO  → skip
│   circuit_ok? ── NO  → skip (ZSTOP circuit breaker active)
│   |Z| ≥ 2.5? ── NO  → skip (not stretched enough)
│   |Z| ≤ 7.9? ── NO  → skip (too close to stop, bad risk/reward)
│   R² ≥ 0.80? ── NO  → skip (hedge ratio not reliable)
│   cooldown ok? ─ NO  → skip
│   CONFIRM_TURN? ─ NO  → skip (spread still widening, wait for turn)
│   ALL PASS → OPEN TRADE
│       Z > 0: SHORT coin A, LONG  coin B
│       Z < 0: LONG  coin A, SHORT coin B
│
└─ EXIT gate (when in trade) ──────────────────────────────────────────
    Z ≥ +8 or Z ≤ −8? ──────────── Z_STOP (cut loss)
    Reversal trail triggered? ────── REVERSAL_TRAIL (lock profit)
    hold ≥ 2 AND Z crosses 0? ────── MEAN_REVERT ← TARGET exit
    hold ≥ half_life × 2? ─────────  TIME_STOP (forced close)
    Z flipped past entry threshold? ─ REVERSAL (wrong way, close)
```

---

## OPTIMISATION HISTORY

**`optimize.py` ran a narrow initial grid** (OLS=36/72h, ZSCORE=18/36h, STOP=2.5/3.0) — the optimal OLS=120h, ZSCORE=48h, STOP=8.0 were all outside that grid. The actual best config was found manually via `_tune.py` (testing stop values up to 7.0) and `_tune2.py` (pushing stop to 8.0–10.0 and comparing hold strategies).

**Key finding: `Z_STOP_LOSS` is the single biggest lever.**

| Z_STOP | ROI | Sharpe | Z_STOP exits |
|--------|-----|--------|--------------|
| 3.0 (original) | −5.3% | −0.018 | 2.8% |
| 5.0 | −5.3% | +0.018 | 2.8% |
| 6.0 | −2.2% | +0.203 | 0.8% |
| 7.0 | −1.5% | +0.242 | 0.0% |
| **8.0** | **+2.3%** | **+0.576** | **0.0%** |
| 9.0 | +2.3% | +0.576 | 0.0% |

With Z_STOP = 3.0, trades were being cut prematurely during normal spread noise, turning wins into losses. At 8.0, all exits are clean mean-reversion — the strategy works as designed.

**Why forcing a max hold period hurts:**
| Max hold | ROI |
|---|---|
| 24h fixed | −7.6% |
| 48h fixed | −3.8% |
| `half_life × 2` (natural) | **+2.3%** |

The OU half-life naturally computes to ~8–11h for these pairs, giving `max_hold ≈ 16–22h`. Forcing 24h cap cuts MEAN_REVERT exits that would have been clean, increasing TIME_STOP exits.

---

## FINAL BACKTEST RESULTS

**Period: 2023-01-01 → 2026-05-31 | Timeframe: 1h | Capital: $1,000 per leg ($2,000 per trade)**

| Pair | ROI% | Sharpe | Trades | Win Rate | Avg Hold | Half-Life |
|---|---|---|---|---|---|---|
| SOL-XRP | **+9.89%** | +5.754 | 23 | 73.9% | 17h | 17.3h |
| BTC-SOL | **+5.64%** | +2.936 | 41 | 68.3% | 20h | 20.2h |
| BNB-XRP | **+2.77%** | +4.040 | 13 | 76.9% | 16h | 19.2h |
| BNB-SOL | **+1.97%** | +1.232 | 28 | 64.3% | 21h | 21.4h |
| ETH-XRP | **+1.44%** | +0.949 | 23 | 47.8% | 16h | 19.7h |
| BTC-XRP | −0.48% | −0.500 | 22 | 59.1% | 16h | 19.4h |
| BTC-ETH | −3.60% | −2.160 | 45 | 55.6% | 22h | 22.4h |
| BTC-BNB | −4.34% | −1.884 | 31 | 58.1% | 21h | 21.3h |
| ETH-BNB | −4.99% | −2.789 | 31 | 35.5% | 20h | 20.6h |
| ETH-SOL | −6.04% | −1.819 | 30 | 60.0% | 21h | 20.2h |
| **TOTAL** | **+2.26%** | | **287** | **60%** | **~20h** | |

**Exit breakdown (aggregate):** 88.4% MEAN_REVERT · 11.3% REVERSAL_TRAIL · 0.0% Z_STOP

Average hold ≈ 20h → roughly **one trade per day per pair** naturally, without forcing a fixed hold.

**Star pairs:** SOL-XRP, BTC-SOL, BNB-XRP — highest Sharpe, highest win rates.
**Drag pairs:** ETH-BNB (35.5% WR — hedge ratio unstable), ETH-SOL (−6%), BTC-BNB (−4.3%).

---

## DATA PIPELINE

```
dataset/
  BTC/1h/spot_ohlcv.parquet   ← columns: open_time, open, high, low, close, volume, ...
  ETH/1h/spot_ohlcv.parquet
  BNB/1h/spot_ohlcv.parquet
  SOL/1h/spot_ohlcv.parquet
  XRP/1h/spot_ohlcv.parquet
```

The engine reads **Close** price only. `open_time` is parsed as the index. All 5 coins are inner-joined so only timestamps where all coins have data are used.

---

## MULTI-TIMEFRAME MODE (MTF)

`backtest.py` supports `--signal_timeframe 1h --timeframe 15m`:
- **Signal TF** (1h): OLS, Z-score, regime, half-life computed on hourly bars
- **Execution TF** (15m): price fills and P&L on 15m bars

`scaled_params()` auto-scales all bar-count parameters:
- `ols_window` → 120h × (60/15) = 480 bars at 15m
- `cooldown_bars` → 6 × (60/15) = 24 bars at 15m (keeps 6h cooldown)

---

## FLASK API ENDPOINTS

All routes in `main_controller/main.py`.

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/phase_10/run_backtest` | Start backtest subprocess. Body: `{pair?, date_from, date_to, timeframe, signal_timeframe?}` |
| `GET` | `/api/phase_10/status` | Returns `{is_running, logs[], last_run}` |
| `POST` | `/api/phase_10/stop` | Send SIGTERM to running backtest |
| `GET` | `/api/phase_10/results` | Returns `phase_10/data/results.json` (full output) |

Server state block:
```python
_p10 = {
    'proc':       None,
    'logs':       [],      # rolling stdout (most recent 300 lines)
    'is_running': False,
    'last_run':   None,
}
```

A background thread `_p10_stdout_reader` drains stdout into `_p10['logs']` and sets `is_running = False` on process exit.

---

## RESULTS JSON SCHEMA

`phase_10/data/results.json`

```json
{
  "generated_at": "2026-06-17T...",
  "date_from": "2023-01-01",
  "date_to":   "2026-05-31",
  "timeframe": "1h",
  "signal_timeframe": "1h",
  "execution_timeframe": "1h",
  "pairs": [
    {
      "pair": "BTC-ETH",
      "coin_a": "BTC",
      "coin_b": "ETH",
      "cointegrated": true,
      "adf_pvalue": 0.0,
      "half_life_bars": 22.4,
      "median_hedge_ratio": 1.23,
      "initial_balance": 2000.0,
      "final_balance": 1928.0,
      "roi": -3.60,
      "sharpe": -2.160,
      "calmar": -0.42,
      "max_drawdown": -12.3,
      "total_trades": 45,
      "win_rate": 55.6,
      "profit_factor": 0.84,
      "avg_hold_bars": 22.4,
      "total_fees": 18.50,
      "exit_mr_pct":    88.9,
      "exit_ts_pct":    11.1,
      "exit_rev_pct":    0.0,
      "exit_trail_pct":  0.0,
      "exit_zstop_pct":  0.0,
      "coin_a_roi": -1.80,
      "coin_b_roi": -1.80,
      "is_pnl": -18.50,   "is_trades": 27,    // IS  = first 60% of bars
      "oos1_pnl": -12.30, "oos1_trades": 12,  // OOS1 = 60–80%
      "oos2_pnl": -41.20, "oos2_trades": 6,   // OOS2 = 80–100%
      "price_series":  [...],
      "zscore_series": [...],
      "equity_curve":  [...],
      "equity_curve_a": [...],
      "equity_curve_b": [...],
      "trades": [
        {
          "entry_time":  "2023-02-15 08:00:00",
          "exit_time":   "2023-02-16 04:00:00",
          "side":        "SHORT_SPREAD",
          "side_a":      "SHORT",
          "side_b":      "LONG",
          "coin_a":      "BTC",
          "coin_b":      "ETH",
          "entry_pa":    24300.0,
          "entry_pb":    1650.0,
          "exit_pa":     24100.0,
          "exit_pb":     1660.0,
          "hedge_ratio": 1.2340,
          "entry_z":     2.8,
          "exit_z":      0.1,
          "hold_bars":   20,
          "pnl_a":       8.23,
          "pnl_b":      -7.40,
          "fee_a":       2.43,
          "fee_b":       4.11,
          "net_pnl_a":   5.80,
          "net_pnl_b":  -11.51,
          "net_pnl":    -5.71,
          "mfe":         12.30,
          "mae":         -8.40,
          "reason":      "MEAN_REVERT"
        }
      ],
      "params": {
        "engine_version":    "v3",
        "ols_window":        120,
        "zscore_window":     48,
        "min_entry_z":       2.5,
        "z_stop_loss":       8.0,
        "min_r2":            0.80,
        "confirm_turn":      true,
        "trading_fee":       0.0005,
        "capital_per_leg":   1000
      }
    }
  ]
}
```

---

## DASHBOARD FEATURES

### Page Header — Summary Bar
Five stat chips always visible at the top of the page:
- **Best Pair** — pair with highest Sharpe
- **Best Sharpe** — Sharpe of best pair
- **Cointegrated** — count of pairs that passed ADF test
- **Total Trades** — sum across all pairs
- **Period** — date range from the loaded results

### Backtest Controls
- **Pair Inspector** dropdown — select a pair to view its detail panel
- **Signal TF** select (default: 1h)
- **Execution TF** select (default: 15m in UI, but engine runs 1h unless changed)
- **▶ Run All Pairs** button — triggers full 10-pair backtest via `/api/phase_10/run_backtest`
- **■ Stop** button — terminates the active subprocess
- Live progress bar + log block shown while backtest is running

### Metrics Grid (always visible when a pair is selected)
Three cards side-by-side — NOT tabs, always shown:

**Pair Statistics card:**
- Sharpe (combined), Calmar Ratio, Profit Factor, Max Drawdown
- ADF p-value, Half-Life (bars), Hedge Ratio β, Total Trades, Avg Hold, Total Fees
- Exit Breakdown badges: `MR` (green) · `TS` (blue) · `REV` (red) · `ZSTOP` (purple)

**Coin A Account card (🔵):**
- Starting Capital: $1,000
- Gross PnL, Total Fees, Fee Drag, Net PnL, ROI, Sharpe (A leg), Profit Factor, Win Rate

**Coin B Account card (🟠):**
- Same fields as Coin A for the B leg

Above the metrics grid: **Validation Split bar** — visual bar showing IS/OOS1/OOS2 split (60%/20%/20%) and trade counts per segment.

### Analytics Tabs (6 tabs)

| Tab | Content |
|---|---|
| 🌊 **Pairs Chart** | Both coin prices normalised to base=100. Continuous execution-time series. Trade entry markers: ▲ Long Entry (green), ▼ Short Entry (red). Exit markers: ◆ Mean Revert (white), ✕ Time Stop (yellow), + Reversal (purple) |
| 📉 **Z-Score** | Z-score time-series with dynamic Bollinger Bands and regime filter overlay |
| 📈 **Equity Curve** | Combined account equity from $2,000 start over full backtest period |
| 🎯 **MFE / MAE** | Two scatter plots side-by-side: MFE vs Net PnL ("high MFE + low realized = exiting too late") and MAE vs Net PnL ("large MAE = entry timing or margin risk") |
| 📅 **Periodic** | Monthly Net PnL bar chart + Yearly Net PnL bar chart |
| 📋 **Trade Log** | Search box + exit-reason filter dropdown (All / Mean Revert / Time Stop / Reversal / Reversal Trail / Z-Stop). Sub-tabs inside: **🔵 Coin A Trades** / **🟠 Coin B Trades** — each showing: #, Entry/Exit Time, Side, Entry/Exit Price, Hold, Entry Z, R², Exit Z, Gross PnL, Fee, Net PnL, MFE, MAE, Reason |

### All Pairs Ranking Table
Full-page table below the detail panel. Sorted by Sharpe by default. Click any row to load that pair into the detail panel. Shows ROI, Sharpe, Trades, Win Rate, Max DD, Cointegrated badge.

---

## HOW TO RUN

```bash
# Full backtest — all 10 pairs (updates results.json)
python phase_10/backtest.py

# Single pair
python phase_10/backtest.py --pair SOL-XRP

# Custom date range
python phase_10/backtest.py --date_from 2024-01-01 --date_to 2026-05-31

# Multi-timeframe: 1h signals, 15m execution
python phase_10/backtest.py --signal_timeframe 1h --timeframe 15m

# Grid search (takes ~30-60 min)
python phase_10/optimize.py
```

---

## KNOWN BEHAVIOURS

- **This is NOT HFT**: Phase 10 is low-frequency statistical arbitrage. With `MIN_ENTRY_Z=2.5` and `CONFIRM_TURN=True`, a 2.5σ-turning event for a given pair is rare — SOL-XRP sees only ~23 entries over 3.5 years (~1 trade every 7.5 weeks). Trade gaps of 5–7 months between entries are normal. The ~1 trade/day figure is across *all 10 pairs combined* (287 trades / 1278 days), not per pair.

- **Win rate counts combined net P&L**: The reported `win_rate` asks "did both legs together produce positive net P&L after all 4 fees?" — this is the correct pairs-trading metric. Per-leg win rates (`coin_a_win_rate`, `coin_b_win_rate`) are diagnostic: they show which leg is carrying the trade (e.g. SOL-XRP: A=47.8%, B=73.9%, combined=73.9%). Averaging the two leg rates (60.9%) would be meaningless because the legs are not independent positions.

- **Hedge ratio drift**: β changes during the hold period. Even when Z reverts to 0, dollar P&L may differ from Z-score expectation because β(t_exit) ≠ β(t_entry). This is an inherent limitation — mitigated by longer OLS windows (120h) for more stable hedge ratios.
- **ETH-BNB 35.5% win rate**: Abnormally low — lowest of all 10 pairs. The ETH-BNB hedge ratio is particularly unstable, causing the position sizing to mismatch during the hold period. Candidate for pair-specific tuning or exclusion.
- **Fee drag asymmetry**: With 4 legs per trade, fee drag is 4× the single-trade fee. Pairs with small spread moves (BTC-ETH, BTC-BNB) frequently earn less than fees even when Z reverts cleanly.
- **CONFIRM_TURN filter**: Prevents entering at the absolute peak/trough of the spread (which often keeps widening). The slight delay costs some edge cases but dramatically reduces entries that immediately go against the position.
- **BB bands preserved**: Bollinger Bands on Z-score are computed and stored in `results.json` / shown in dashboard for context. They do NOT gate entries or exits in the current engine (pure Z-score formula).

---

## CURRENT STATUS (as of 2026-06-17)

| Metric | Value |
|---|---|
| Strategy type | Pure Z-score pairs trading (v3 engine) |
| Pairs traded | 10 (BTC/ETH/BNB/SOL/XRP combinations) |
| Timeframe | 1h signal + execution |
| Date coverage | 2023-01-01 → 2026-05-31 |
| Total ROI (all pairs) | +2.26% |
| Total Sharpe (avg) | +0.576 |
| Total trades | 287 |
| Win rate | 60% |
| Avg hold | ~20h (~1 trade/day/pair) |
| Z_STOP exits | 0.0% (stop at 8σ is rarely hit) |
| MEAN_REVERT exits | 88.4% (strategy working as intended) |
| Parameters optimised | 2026-06-17 (OLS=120, Z=48, MinZ=2.5, Stop=8.0, R2=0.80) |
| Last results.json update | 2026-06-17 |
