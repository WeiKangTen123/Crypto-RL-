# DRL BTC Agent — Full Architecture Overview

> Last updated: 2026-07-17 (Session 12 — on-chain features, ROI-focused fixes, aggressive config, training running)
> Session 8: complete — `sac_best_s42_session8.pt` saved
> Session 9 (TIA v2): built, superseded by TIA v3 (never deployed to server)
> Session 10 (TIA v3.1): trained on 47.250.37.200 (seed=42, 600K steps, G_STEPS=10) — crashed at step 350K; best checkpoint minSharpe=+0.626 at ~step 260K → `sac_best_s42.pt`
> Session 11 (TIA v3.1 + futures metrics): complete — 216 features, 11 encoder groups, LSTM input 352; failed due to OOD permanent BLOCK + logπ saturation
> Session 12 (TIA v3.1 + on-chain features): **running** — 223 features, 12 encoder groups, LSTM input 384, 7 ROI fixes applied; started 2026-07-17 11:38 CST; step 40K best: avgSharpe=+1.438 minSharpe=+0.323
> Session 7 OOS result: −6.81% return, Sharpe −0.99, MDD 8.89% (2025-01-01 → 2026-07-15)

---

## Table of Contents

1. [Data Pipeline](#1-data-pipeline)
2. [Feature Engineering — 223 Features](#2-feature-engineering--223-features)
3. [Composite Signals — Strategy Combinations](#3-composite-signals--strategy-combinations)
4. [What the Agent Sees (Observation)](#4-what-the-agent-sees-observation)
5. [Network Architecture](#5-network-architecture) — 5a Session 12 / TIA v3.1 (current) · 5b Session 11 · 5c Session 10 · 5d Session 9 · 5e Session 8
6. [Action Space](#6-action-space)
7. [Trade Mechanics](#7-trade-mechanics)
8. [Reward Structure](#8-reward-structure)
9. [Training Process](#9-training-process)
10. [Validation & Checkpoints](#10-validation--checkpoints)
11. [Config Reference](#11-config-reference)

---

## 1. Data Pipeline

```
Raw BTC-USDT historical data  (Binance)
        │
        ├── 1h  OHLCV  →  base timeframe  (35,035 bars, 2021–2024)
        ├── 4h  OHLCV  →  context TF (forward-filled to 1h grid)
        ├── 1d  OHLCV  →  macro TF   (forward-filled to 1h grid)
        ├── 1h  Funding rate  →  auxiliary (6 features)
        ├── 1h  Order book depth  →  auxiliary (8 features, from 2023)
        ├── 1h  Futures metrics  →  NEW (Session 11): OI / L/S ratio / taker vol
        │        Source: Binance bulk data portal (5-min → resampled to 1h)
        │        Coverage: 2020-09-01 → present  (51,456h raw)
        │        Columns: oi_contracts, oi_usd, ls_ratio, top_ls_ratio, taker_ls_vol
        └── On-chain / cycle  →  NEW (Session 12): Fear & Greed + MVRV proxy + cycle
                 Source: alternative.me API (F&G 3000-day history, no key required)
                 Coverage: 2020-12-31 → 2026-06-16  (47,810h after hourly reindex)
                 Parquet cols: fng_raw, fng_z60, fng_mom7
                 +4 OHLCV-derived features computed inside feature_builder.py

Stored at: dataset/BTC/{tf}/spot_ohlcv.parquet
           dataset/BTC/1h/futures_metrics.parquet        ← Session 11
           dataset/BTC/1h/onchain_metrics.parquet        ← Session 12 new
Cache at:  DRL_BTC/data/features/features.parquet        (223 cols × 47,810 rows)   ← was 216
```

**Date splits:**

| Split | Range | Bars | Purpose |
|---|---|---|---|
| Train | 2021-01-01 → 2024-12-31 | 35,035 | Agent training |
| Val — Regime 1 | 2022-01-01 → 2022-12-31 | 8,737 | Bear year (BTC −66%) |
| Val — Regime 2 | 2023-07-01 → 2023-12-31 | 4,392 | Recovery / bull (+100% H2 2023) |
| Val — Regime 3 | 2021-06-01 → 2021-12-31 | 4,392 | Mid-cycle bull (post-crash → ATH $67K) ← **Session 12 change** |
| OOS | 2025-01-01 → present | ~13,000+ | Never touched during training |

> **TIA v2 change:** Single 2022 val replaced by 3 regime-diverse windows.
> Early-stop criterion: **min Sharpe** across all 3 regimes (robustness — must perform in every regime, not just average).

---

## 2. Feature Engineering — 223 Features

Each of the 3 timeframes contributes ~60 indicators, all normalised to `[-1, 1]`.
4h and 1d features are **shift(1) then forward-filled** to 1h — no lookahead leakage.

### Trend Group (~13 features per TF)
| Feature | Indicator | Signal |
|---|---|---|
| `ema9_ret`, `ema21_ret`, `ema50_ret`, `ema200_ret` | EMA distance from price | Trend direction & strength |
| `ema9_slope`, `ema21_slope`, `ema50_slope`, `ema200_slope` | EMA slope | Acceleration |
| `ema9_21_cross`, `ema21_50_cross` | EMA crossover | Trend change signal |
| `st_dir`, `st_dist` | Supertrend | Trend direction + proximity |
| `adx`, `di_diff` | ADX/DMI | Trend strength + direction |
| `psar_dir` | Parabolic SAR | Short-term trend |
| `vortex_diff` | Vortex | Directional movement |
| `hma_slope` | Hull MA | Smooth momentum |
| `ichimoku_dir` | Ichimoku cloud | Price vs cloud |

### Momentum Group (~14 features per TF)
| Feature | Indicator | Signal |
|---|---|---|
| `rsi14`, `rsi7`, `rsi14_slope` | RSI | Overbought/oversold + speed |
| `macd_hist`, `macd_above` | MACD | Momentum crossover |
| `kdj_j` | KDJ | Fast stochastic momentum |
| `wt1`, `wt2`, `wt_cross` | WaveTrend | Oscillator crossover |
| `mfi` | Money Flow Index | Volume-weighted momentum |
| `cci` | CCI | Mean reversion signal |
| `williams_r` | Williams %R | Overbought/oversold |
| `stoch_k`, `stoch_d`, `stoch_kd_cross` | Stochastic | Momentum crossover |
| `srsi_k` | Stochastic RSI | Fast momentum |
| `fisher` | Fisher Transform | Price cycle extremes |
| `tsi` | True Strength Index | Double-smoothed momentum |
| `aroon_diff` | Aroon | Trend direction + age |

### Volatility Group (~8 features per TF)
| Feature | Indicator | Signal |
|---|---|---|
| `atr_pct` | ATR % of price | Volatility magnitude |
| `bb_width`, `bb_pct` | Bollinger Bands | Squeeze + price position |
| `squeeze` | BB vs KC squeeze | Low-volatility breakout setup |
| `hist_vol` | Historical volatility | Realised vol regime |
| `choppiness` | Choppiness Index | Trend vs range market |
| `atr_regime` | ATR vs 50-bar MA | Vol expanding or contracting |

### Volume / Flow Group (~6 features per TF)
| Feature | Indicator | Signal |
|---|---|---|
| `vol_z` | Volume z-score | Unusual activity |
| `taker_ratio`, `taker_ratio_z` | Taker buy ratio | Aggressive buying/selling |
| `vwap_z` | VWAP z-score | Price vs fair value |
| `cvd_z` | Cumulative Volume Delta z | Net buying vs selling pressure |
| `obv_slope` | OBV slope | Volume trend |
| `vol_regime` | Fast/slow vol MA ratio | Volume expansion |

### Structure Group (~9 features per TF)
| Feature | Indicator | Signal |
|---|---|---|
| `price_z20` | Price z-score 20-bar | Mean reversion signal |
| `vs_ema200` | Price vs EMA200 % | Long-term trend position |
| `fvg_bull`, `fvg_bear` | Fair Value Gap | SMC supply/demand zones |
| `imb_bull`, `imb_bear` | Imbalance Zone | Price inefficiency |
| `swing_hi`, `swing_lo` | Swing pivots | Market structure |
| `candle` | Engulfing/Hammer/Star | Price action patterns |
| `order_block` | Order Block | Institutional footprint |

### Auxiliary Features (no TF suffix)
| Feature | Source | Signal |
|---|---|---|
| `funding_raw`, `funding_z20`, `funding_mom8h` | Binance funding rate | Crowding / longs-pay pressure |
| `funding_ma24`, `funding_cumsum8h`, `funding_vol20` | Binance funding rate | Carry cost + uncertainty |
| `ob_imb_1pct`, `ob_imb_3pct`, `ob_imb_5pct` | Order book | Bid/ask depth imbalance |
| `ob_ba_ratio` | Order book | Whole-book directional bias |
| `ob_bid_z`, `ob_ask_z` | Order book | Unusual depth vs history |
| `ob_bid_slope`, `ob_ask_slope` | Order book | Front-heavy vs back-heavy |

### Futures Metrics Features — NEW Session 11 (15 features, no TF suffix)

Derived from `futures_metrics.parquet` (Binance bulk portal, 5-min → 1h resample).

**Open Interest — 7 features** → PerspectiveEncoder group: `openinterest`
| Feature | Signal |
|---|---|
| `oi_chg_1h` | 1-bar OI change normalised by 20-bar std — immediate flow |
| `oi_chg_4h` | 4-bar OI change — medium-term accumulation / distribution |
| `oi_z20` | 20-bar z-score of OI_USD — positioning vs recent history |
| `oi_vol_ratio` | OI change / volume — smart-money footprint (high ratio = quiet accumulation) |
| `oi_confirm` | OI aligned with price trend (+1 = OI rising with price, −1 = diverging) |
| `oi_extreme` | OI > ±2σ — over-extended positioning, mean-reversion signal |
| `oi_mom` | 8-bar EMA of oi_z20 slope — momentum in positioning |

**L/S Ratio Sentiment — 5 features** → PerspectiveEncoder group: `sentiment`
| Feature | Signal |
|---|---|
| `ls_ratio_z20` | Retail long/short ratio 20-bar z-score — crowd positioning |
| `ls_extreme` | L/S ratio > ±1.5σ — crowded longs/shorts, fade signal |
| `top_ls_z20` | Top-trader L/S ratio z-score — institutional positioning |
| `top_retail_div` | Top-trader vs retail divergence — smart money vs dumb money |
| `taker_ls_z20` | Taker buy/sell volume ratio z-score — aggressive order flow |

**Spot-Futures Basis — 3 features** → PerspectiveEncoder group: `funding` (existing)
| Feature | Signal |
|---|---|
| `basis_raw` | (futures_price − spot_price) / spot_price — contango / backwardation |
| `basis_z20` | 20-bar z-score of basis — elevated vs normal carry cost |
| `basis_trend` | 8-bar EMA of basis_z20 — basis expanding or collapsing |

### On-Chain / Cycle Features — NEW Session 12 (7 features, no TF suffix)

Derived from `onchain_metrics.parquet` (F&G) and OHLCV (MVRV proxy, cycle momentum).

**Fetch:** `python -m DRL_BTC.scripts.fetch_onchain_metrics`

→ PerspectiveEncoder group: `onchain` (new 12th group)

| Feature | Source | Computation | Signal |
|---|---|---|---|
| `fng_raw` | alternative.me API | daily F&G index / 100 → ffill to 1h | Market sentiment 0–1 (0=fear, 1=greed) |
| `fng_z60` | derived | 60-day rolling z-score of fng, clip ±3 | Sentiment deviation from recent baseline |
| `fng_mom7` | derived | 7-day diff of fng, clip ±0.5 | Momentum in sentiment shift |
| `mvrv_proxy` | OHLCV close | (close / ewm(span=17520) − 1) / 4.0, clip [0,1] | Realised-value proxy (high = expensive vs long-term avg) |
| `mvrv_z` | derived | rolling 8760-bar z-score of mvrv_proxy, clip ±3 | Cycle position (z > 2 = historically overvalued) |
| `yr1_mom` | OHLCV close | log(close / close.shift(8760)).clip(-2,2) / 2.0 | 1-year price momentum (bull/bear cycle signal) |
| `ath_draw` | OHLCV close | (rolling_max(35040) − close) / rolling_max(35040), clip [0,1] | Distance from 4-year ATH (0 = at ATH, 1 = 100% below) |

All 7 features shift-aligned: no lookahead. span=17520 ≈ 2 years of hourly bars.

---

## 3. Composite Signals — Strategy Combinations

These are computed AFTER all raw features are assembled and appended as 4 extra columns.
Formulas updated in Session 11 to incorporate OI and sentiment signals (safe `_gc()` fallback to zero if column missing).

### `macro_score` — Big-Picture Trend Direction
```
Formula:
  ema_cross   = avg(ema9_21_cross across 1h, 4h, 1d)
  st_align    = avg(st_dir across 1h, 4h, 1d)
  fund_sig    = -funding_raw × 0.5
  oi_conf     = oi_confirm                      ← NEW Session 11
  oi_crowd    = -oi_extreme.clip(-1,1) × 0.5   ← NEW Session 11 (fade over-extended OI)
  macro_score = 0.40 × ema_cross + 0.30 × st_align + 0.15 × fund_sig
              + 0.10 × oi_conf + 0.05 × oi_crowd
Range: [-1, +1]
```

### `swing_score` — Medium-Term Setup Quality
```
Formula (4h + smart money):
  swing_score = 0.30 × macd_hist_4h
              + 0.25 × (rsi14_4h − 0.5) × 2
              + 0.20 × aroon_diff_4h
              + 0.10 × (kdj_j_4h − 0.5) × 2
              + 0.15 × top_retail_div            ← NEW Session 11 (smart money vs retail)
Range: [-1, +1]
```

### `entry_score` — 1h Microstructure Entry Timing
```
Formula (1h microstructure + taker flow):
  entry_score = 0.25 × ob_ba_ratio
              + 0.25 × taker_ratio_z_1h
              + 0.20 × cvd_z_1h
              + 0.15 × taker_ls_z20              ← NEW Session 11 (taker L/S from futures)
              + 0.15 × rsi14_slope_1h
Range: [-1, +1]
```

### `regime_score` — Market Tradeability Gate
```
Formula:
  anti_chop  = 1 − avg(choppiness_1h, choppiness_4h)
  adx_str    = adx_4h
  vol_ok     = 1 − atr_regime_1h.clip(0, 1)
  oi_build   = oi_chg_4h.clip(-1,1).abs()        ← NEW Session 11 (OI conviction)
  regime_raw = 0.30 × anti_chop + 0.40 × adx_str + 0.15 × vol_ok + 0.15 × oi_build
  regime_score = (regime_raw × 2) − 1
Range: [-1, +1]
```

### Direction Decision Rule (rule-based, not actor-controlled)
```
combined = 0.65 × macro_score + 0.35 × swing_score

if   combined > +0.10  AND  regime_score > 0:  → LONG
elif combined < −0.10  AND  regime_score > 0:  → SHORT
else:                                           → FLAT

Approximate long/short/flat: 15% / 26% / 60%
Exits: SL / TP / direction_change / 96-bar timeout (all rule-based)
```

---

## 4. What the Agent Sees (Observation)

```
Shape: (48 timesteps × 231 values)   ← Session 12: was 224 (S11) / 217 (S10)

For each of the 48 bars:
  ├── 223 market features  (all indicators above, normalised)   ← was 216 (S11)
  └──   8 portfolio state features:
         [0] position          (-1 = short, 0 = flat, +1 = long)
         [1] pos_size          (actual position size as fraction of equity)
         [2] sl_dist           ((cur_px − sl_price) / cur_px × position)
         [3] hold_bars / 48   (how long in current trade)
         [4] equity log-growth (log10(equity / initial))
         [5] negative DD       (−drawdown)
         [6] unrealised PnL    (current open trade P&L fraction)
         [7] is_holding        (1 = in trade, 0 = flat)
```

---

## 5. Network Architecture

### 5a. Session 12 — TIA v3.1 + On-chain Features (current)

**Status: Training started 2026-07-17 11:38 CST — seed=42, 400K steps, ALPHA_FIXED=0.05.**
**Key changes from S11: 223 features, 12 encoder groups, LSTM input 384, 7 ROI fixes, LOG_STD_MAX=-0.5.**

```
obs: (batch, 48, 231)   ← was (batch, 48, 224) in S11
               │
  ┌─ PerspectiveEncoder ──────────────────────────────────────────────┐
  │  Phase 1: 12 semantic groups → Linear projection → 32-dim each   │
  │           (was 11 groups in Session 11)                           │
  │                                                                   │
  │  Groups and their feature sets:                                   │
  │    trend        (~13 cols/TF × 3 TF)                             │
  │    momentum     (~14 cols/TF × 3 TF)                             │
  │    volatility   (~8  cols/TF × 3 TF)                             │
  │    volume       (~6  cols/TF × 3 TF)                             │
  │    structure    (~9  cols/TF × 3 TF)                             │
  │    funding      (6 funding + 3 basis = 9 cols)                   │
  │    orderbook    (8 ob_* cols)                                     │
  │    portfolio    (8 portfolio state features)                      │
  │    signal       (4 composite signals)                             │
  │    openinterest (7 OI cols)                                       │
  │    sentiment    (5 L/S ratio cols)                                │
  │    onchain      (7 on-chain/cycle cols)   ← NEW Session 12       │
  │                                                                   │
  │  Phase 2: Cross-group MHA (4 heads, d=32) — "cross-perspective"  │
  │  Phase 3: LSTM(input=384, hidden=256, 2L, dropout=0.1)           │
  │           input = 12 groups × 32-dim = 384   (was 11×32=352)     │
  │                    → z (FC_HIDDEN = 256)                          │
  └───────────────────────────────────────────────────────────────────┘
               │
     ┌─────────┼────────────────────────┬──────────────────────────┐
     │         │                        │                          │
BetaEngine  AlphaEngine      MarketDiagnostics          KnowledgeMemory
     │         │                        │                          │
  embed(32)  ret_pred(1)    ood_score ∈ [0,1]      5K ring buffer
  regime(3)  ret_p50(1)     EMA z-dist detector     cosine-sim retrieval
  vol_class  tp_prob(1)                             OOD-gated k:
  vol_pred   sl_prob(1)        ↓ → DriftManager      ood≤0.6 → k=20
  trend_conf mfe_pred(1)    get_beta_temperature()   ood≤0.8 → k=10
  stability  mae_pred(1)    (calibration drift)      ood≤0.9 → k=5
  trans_prob alpha_conf(1)  get_memory_k(ood)        ood>0.9  → zeros
  calib_conf exp_variance   NORMAL/WARNING/BLOCK      │
             tail_risk                                │
             exp_max_dd      ↓ T (temperature)        ↓
                                                   memory_feat (10-dim)

     │         │                 │                    │
     └─────────┴─────────────────┴────────────────────┘
               │
  extract_beta_context(beta_out, ood_score, temperature=T) → 39-dim
  extract_alpha_feat(alpha_out) → 10-dim
  Rule Engine (obs last-bar signal cols) → rule_feat: 3-dim
  Risk Budget Controller → risk_budget: 1-dim

               │
  ┌─ DecisionFusionLayer ─────────────────────────────────────────────┐
  │  Input: z(256) + beta(39) + alpha(10) + ood(1)                   │
  │         + rule(3) + memory(10) + risk_budget(1) = 320-dim        │
  │  Network: 256→128→64 ReLU                                         │
  │  Output: gate_decision EXECUTE/REDUCE/SKIP + size_mult + conf    │
  └───────────────────────────────────────────────────────────────────┘
               │
  ┌─ Policy Net (Actor) ──────────────────────────────────────────────┐
  │  Enriched = [z(256) | beta(39) | alpha(10) | ood(1)             │
  │              gate_probs(3) | size_mult(1) | gate_conf(1) |       │
  │              rule(3) | memory(10) | risk_budget(1)]              │
  │           = FC_HIDDEN + 69 dims                                  │
  │  FC(FC_HIDDEN+70)→ReLU→FC(FC_HIDDEN//2)→ReLU → 4D Gaussian      │
  │  (70 = 69 + 1 opp_score from OpportunityScorer)                 │
  │                                                                   │
  │  action[0]  pos_size   0% – 60% of equity  ← was 25% in S11      │
  │  action[1]  sl_atr_mult  1.0× – 3.0× ATR  ← floor raised S12   │
  │  action[2]  tp_atr_mult  1.5× – 3.0× ATR  ← tighter range S12  │
  │  action[3]  trail_on   bool                                       │
  └───────────────────────────────────────────────────────────────────┘
               │
  ┌─ Twin Critics ────────────────────────────────────────────────────┐
  │  Two independent PerspectiveEncoders + concat(z, action) → Q     │
  │  Critics compiled with torch.compile(backend="aot_eager")        │
  │  AMP: torch.autocast("cuda", float16) + GradScaler               │
  └───────────────────────────────────────────────────────────────────┘
```

**PerspectiveEncoder group dimensions (Session 12):**

| Group | Features | In-dim | → D_ATTN |
|---|---|---|---|
| trend | ~13/TF × 3 TF | varies | 32 |
| momentum | ~14/TF × 3 TF | varies | 32 |
| volatility | ~8/TF × 3 TF | varies | 32 |
| volume | ~6/TF × 3 TF | varies | 32 |
| structure | ~9/TF × 3 TF | varies | 32 |
| funding | 6 funding + 3 basis | 9 | 32 |
| orderbook | 8 ob_* | 8 | 32 |
| portfolio | 8 portfolio | 8 | 32 |
| signal | 4 composite | 4 | 32 |
| openinterest | 7 OI features | 7 | 32 |
| sentiment | 5 L/S features | 5 | 32 |
| **onchain** | **7 on-chain/cycle** | **7** | **32** ← NEW S12 |
| **Total** | | | **12 × 32 = 384 LSTM input** |

**Dimension evolution:**

| Component | TIA v1 (S8) | TIA v2 (S9) | TIA v3 (S10) | TIA v3.1 (S10.1) | S11 | **S12 (current)** |
|---|---|---|---|---|---|---|
| Market features | 209 | 209 | 209 | 209 | 216 | **223** |
| Obs shape | (48,217) | (48,217) | (48,217) | (48,217) | (48,224) | **(48,231)** |
| Encoder groups | 9 | 9 | 9 | 9 | 11 | **12** |
| LSTM input | 9×32=288 | 9×32=288 | 9×32=288 | 9×32=288 | 11×32=352 | **12×32=384** |
| BETA_FEAT_DIM | 5 | 7 | **39** | 39 | 39 | 39 |
| ALPHA_FEAT_DIM | 5 | 7 | **10** | 10 | 10 | 10 |
| MEMORY_FEAT_DIM | — | — | — | **10** | 10 | 10 |
| _FUSED_IN_DIM | z+14 | z+20 | z+59 | **z+69** | z+69 | z+69 |
| ALPHA_FIXED | 0.3 | 0.3 | 0.3 | 0.3 | 0.10 | **0.05** |
| LOG_STD_MAX | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **−0.5** |

---

### 5b. Session 11 — TIA v3.1 + Futures Metrics

**Status: Complete. Failed — OOD permanent BLOCK + logπ saturation. Best checkpoint saved.**
216 features, 11 encoder groups, LSTM input 352, ALPHA_FIXED=0.10, parallel val.

Key fixes attempted: ALPHA_FIXED 0.3→0.10, real OI/basis/L/S features.
Root failures: `DriftManager [BLOCK] ood_ema=1.000` (BC pretrain shifted z-space, OOD_EMA_ALPHA=0.01 too slow to recover); LOG_STD_MAX=0.0 allowed σ_max=1.0 → policy saturation.

---

### 5c. Session 10 — TIA v3.1 (previous run)

**Status: Crashed at step 350K/600K. Best: `sac_best_s42.pt` (minSharpe=+0.626, ~step 260K).**
Architecture identical to Session 11 except: 209 features, 9 encoder groups, LSTM input 288, ALPHA_FIXED=0.3.

---

### 5d. Session 9 — TIA v2

```
Features: (batch, 48, 217)
   PerspectiveEncoder: 9 groups → MHA(4h, d=32) → LSTM(512, 2L) → z(512)
   BetaEngine / AlphaEngine / MarketDiagnostics / ConfidenceGate
   Actor FC(z+20) → 4D Gaussian
```

---

### 5e. Session 8

```
Features: (batch, 48, 217)
   PerspectiveEncoder: 9 groups → MHA(4h, d=32) → LSTM(512, 2L) → z(512)
   BetaHead + AlphaHead → Actor FC(526) → 4D Gaussian
```

---

## 6. Action Space

**4D risk-management controls. Direction and EXIT are NOT actor actions.**

| Dim | Name | Decoding | Range | Session 12 change |
|---|---|---|---|---|
| `action[0]` | pos_size | `0.00 + 0.60 × (a + 1.0) / 2.0` | **0%** – 60% of equity | ↑ was 25% (S11) |
| `action[1]` | sl_atr_mult | `1.0 + 2.0 × (a + 1.0) / 2.0` | 1.0× – 3.0× ATR | floor ↑ from 0.5× |
| `action[2]` | tp_atr_mult | `1.5 + 1.5 × (a + 1.0) / 2.0` | 1.5× – 3.0× ATR | tighter range (was 1.0–6.0×) |
| `action[3]` | trail_on | `sigmoid(a × 3) > 0.5` | On / Off | unchanged |

`exit_signal` removed in Session 7. Root cause of Q-cycling: binary exit created two Q attractors.

**Trade skip:** `pos_size < 0.001` → position not opened. Actor can soft-veto a direction signal it disagrees with.

---

## 7. Trade Mechanics

### Opening a Trade
```
Conditions: currently flat AND new_dir ≠ 0 AND pos_size_act ≥ 0.001

At entry:
  sl_price  = entry_px × (1 − direction × sl_mult × atr_frac)
  tp_price  = entry_px × (1 + direction × tp_mult × atr_frac)
  Entry fee = 0.04% × pos_size × equity
  Leverage  = 1.0× (fixed)
```

### Holding
```
Per bar while in position:
  Funding cost  = 0.01%/8h × pos_size
  Unrealised PnL = (cur_px/entry_px − 1) × direction × pos_size
  If trail_on: sl_price follows trail_peak (SL ratchets in favorable direction)
```

### Closing
```
Rule-based exits (actor cannot control):
  (A) SL hit       (B) TP hit
  (C) Direction reverses — blocked during first MIN_HOLD_BARS=8 bars ← NEW Session 12
  (D) 96-bar timeout (MAX_HOLD_BARS)
  Exit fee = 0.04% × pos_size × equity
```

### Flat Penalty (Session 12 NEW)
```
When position == 0 AND new_dir ≠ 0 AND actor outputs pos_size < 0.001:
  step_reward -= 0.002
  → penalises the actor for soft-skipping a signal (reduces excessive flat time)
```

### Kill Switch
```
If drawdown from peak ≥ 50%: force-close, reward = −1.0, episode ends.
```

---

## 8. Reward Structure

All terms are fractions of equity.

```
Per bar when holding:
  + bar_pnl_pct      = (next_px / cur_px − 1) × position × leverage × pos_size
  − funding_cost     = FUNDING_PER_BAR (0.0000125) × leverage × pos_size
  + trend bonus      = +0.0015 / bar  when position == macro_dir AND regime > 0.2
  − counter-trend    = −0.0010 / bar  when position != macro_dir AND regime > 0.2
  + hold patience    = +0.0001 / bar  when bar_pnl_pct > 0.002  ← NEW Session 12
                       (small bonus for each bar the trade is actively profitable)

At entry:
  − entry_fee        = FEE_RATE (0.0004) × leverage × pos_size
  − chop_penalty     = −0.02  if choppiness_1h > 0.7

At close  (rule-based: SL / TP / direction_change / 96-bar timeout):
  − exit_fee         = FEE_RATE (0.0004) × leverage × pos_size
  + TP bonus         = +0.005 if exit_reason == "tp"  ← NEW Session 12
                       (explicit incentive to let winners hit full profit target)

When flat but signal fires and actor skips (pos_size < 0.001):
  − flat penalty     = −0.002  ← NEW Session 12  (see §7 Flat Penalty)

Drawdown penalty (every bar, applied after PnL):
  if current_dd > 0.05:
    step_reward -= current_dd × DD_PENALTY_SCALE (3.0) × 0.1

Kill switch  (DD >= MAX_DRAWDOWN_KILL = 50%):
  Force-close at cur_px × (1 − 0.01 × leverage)
  step_reward -= 1.0
  episode truncated
```

**Trade-level replay** (Sessions 7+): buffer stores one transition per closed trade:
`(obs_at_entry, action_at_entry, total_trade_pnl, obs_after_exit)`

---

## 9. Training Process

### Stage 0 — SharedModel Supervised Pretrain

Three sub-stages using forward-looking labels from the training window:

```
Stage 1 — BetaEngine (30 epochs, 6 heads):
  Labels: regime (BULL/BEAR/RANGE), vol_class (LOW/MED/HIGH), fwd_vol,
          trend_str, regime_stability, transition_prob
  Loss: CE(regime) + 0.3×CE(vol_class) + 0.5×MSE(vol) + 0.5×MSE(trend_conf)
      + 0.5×BCE(stability) + 0.3×BCE(transition_prob)

Stage 2 — AlphaEngine (30 epochs, 11 heads):
  Labels (oracle trade sim, SL=1.5×ATR, TP=3×ATR):
    trade_return, mfe, mae, tp_hit, hold_bars, sl_hit, exp_vol,
    exp_variance, tail_risk, exp_max_dd
  Loss: MSE(ret) + Pinball(p10/p50/p90) + MSE(mfe/mae) + BCE(tp/sl)
      + MSE(exp_vol/exp_var/tail/maxdd) + 0.1×MSE(hold)

Stage 3 — Joint fine-tune (10 epochs at 0.3× LR):
  All heads + DecisionFusionLayer + encoder together.
```

Then: `shared_model.copy_encoder_to(actor)` → encoder weights warm-start the Actor.

> **Session 12 fix — OOD diagnostics hard-reset after pretrain:**
> BC+supervised pretrain shifts the encoder z-space; `running_mean/std` seeded during pretrain
> don't match the RL distribution → ood_ema≈1.0 on every RL batch → DriftManager permanent BLOCK.
> Fix (in train.py after `pretrain_actor()`):
> ```python
> agent.actor.diagnostics.n_updates.zero_()
> agent.actor.diagnostics.running_mean.zero_()
> agent.actor.diagnostics.running_std.fill_(1.0)
> agent.drift_manager._ood_ema = 0.0
> ```
> Result: ood_ema=0.107 at step 20K (NORMAL) — DriftManager functioning correctly.

---

### Stage 1 — BC Risk Pretraining (~2 min)

```
Oracle risk labels at entry bars:
  pos_size = 0.05 + 0.20 × max(0, regime_score)
  sl_atr   = 1.5 − vol_z × 0.5   (clamped [0.5, 3.0])
  tp_atr   = 3.0 + adx × 2.0     (clamped [1.0, 6.0])
  trail_on = 1.0 if adx > 0.5 else 0.0
Loss: MSE(pos_size) + MSE(sl_atr) + MSE(tp_atr) + BCE(trail_on)
```

### Stage 2 — Warmup (300 complete trades)

Random actions fill trade-level replay buffer.
After warmup: `agent.set_drift_baseline()` sets DriftManager baseline.

### Stage 3 — SAC Learning (400K env steps, Session 12)

```
Every closed trade → 10 gradient updates (G_STEPS=10):
  Critic: MSE(Q, r + γ × (Q_target − α × logπ))  [PER weighted]
  Actor:  mean(α × logπ − min(Q1, Q2))
  Alpha:  FROZEN at 0.05  ← was 0.10 (S11); tighter entropy → faster convergence
  Weight decay: 1e-4

AMP: torch.autocast("cuda", float16) + GradScaler (already in sac_agent.py)
Critics: torch.compile(backend="aot_eager")  (already in sac_agent.py)
CPU inference copy: batch=1 env steps run on CPU; GPU reserved for training
```

### Validation (Session 11+ — parallelised)

```
Val every 20,000 steps  (was 10K)
3 regime windows run in parallel via ThreadPoolExecutor(max_workers=3)
  Each thread: deepcopy(actor_cpu), own env → deterministic rollout
  KnowledgeMemory + DriftManager: shared read-only refs across threads
  _last_actor_info: per-thread copy → no race

Expected speedup:
  Old (S10): val ~18 min sequential + training ~21 min = ~39 min / 10K steps
  New (S11+): val ~6 min parallel + training ~42 min = ~48 min / 20K steps
  → ~38% faster wall-clock for full 400K run
```

### Full Training Pipeline

```
Stage 0: SharedModel Supervised Pretrain (BetaEngine + AlphaEngine + Joint)
  ↓ copy_encoder_to(Actor)

Stage 1: BC Risk Pretraining (~2 min)

Stage 2: Random Warmup (300 trades)
  ↓ set_drift_baseline() → DriftManager calibrated

Stage 3: SAC Learning (400K steps)
  ↓ Val every 20K steps (parallel across 3 regime windows)
  ↓ Best checkpoint: avg_sharpe × max(ret_pct, 0) → sac_best_s42.pt

OOS Evaluation (never touched during training)
  ↓ sac_best_s42.pt → 2025-01-01 → present
```

---

## 10. Validation & Checkpoints

### Checkpoint Evaluator — Multi-Regime Validation

```
Checkpoint Evaluator (3 windows, parallel — Session 11+)
  │
  ├── [2022-Bear]     2022-01-01 → 2022-12-31  (8,737 bars, BTC −66%)
  ├── [2023-Bull]     2023-07-01 → 2023-12-31  (4,392 bars, +100% H2 2023)
  └── [2021-H2-Bull]  2021-06-01 → 2021-12-31  (4,392 bars, post-crash → ATH $67K)
      ← Session 12 change: replaced 2024-Consol (2024-01-01→06-30) with 2021-H2
        Reason: 2021-H2 is a distinct mid-cycle bull unseen during training; adds
        generalization pressure; 2024 was partially in-sample vicinity
                │
                ↓
  min_sharpe   = min(bear, bull, h2_bull)  ← early-stop criterion
  avg_sharpe   = mean(...)
  worst_dd     = max(...)
  best_ckpt    = highest (avg_sharpe × max(ret_pct/100, 0))
```

Val runs every **20,000** steps (was 10K in Sessions 8–10).

### Checkpoint Saves
```
sac_best_s42.pt                           → best composite score (current training)
sac_step{N}_s42.pt                        → snapshot every 50,000 steps
sac_best_s42_session7.pt                  → Session 7 best
sac_best_s42_session8.pt                  → Session 8 best
sac_best_s42_session12_step40k.pt         → Session 12 step 40K (avgSharpe=+1.438)
```
All files in: `/root/wkang/DRL_BTC/data/checkpoints/`
Local copy: `DRL_BTC/data/checkpoints/sac_best_s42_session12_step40k.pt` (63MB, downloaded via scp)

To use with evaluate.py: `--tag best_s42_session12_step40k`

### Session Results History

**Session 7 OOS result:**

| Window | Period | Return | Sharpe | MDD |
|---|---|---|---|---|
| Val | 2022-01-01 → 2022-12-31 | +4.82% | +0.73 | 4.5% |
| OOS | 2025-01-01 → 2026-07-15 | **−6.81%** | **−0.99** | **8.89%** |

**Session 10 / TIA v3.1 val checkpoints:**

| Val step | minSharpe | avgSharpe | avg_ret | worstDD | Notes |
|---|---|---|---|---|---|
| ~step 260K | **+0.626** | — | — | — | **best checkpoint** |
| step 300K | −0.795 | −0.106 | −0.32% | 2.6% | degraded after best |
| step 350K | −0.052 | +1.531 | +1.91% | 2.5% | last before crash |

**Session 11 val checkpoints:**

| Val step | minSharpe | avgSharpe | avg_ret | worstDD | Notes |
|---|---|---|---|---|---|
| — | — | — | — | — | Failed — OOD BLOCK + logπ saturation; training aborted |

**Session 11 failure modes:**
- `DriftManager [BLOCK]  ood_ema=1.000` on every RL batch — BC pretrain shifted z-space; OOD_EMA_ALPHA=0.01 too slow to recalibrate
- `LOG_STD_MAX=0.0` allowed σ_max=1.0 → policy saturated at tanh ±1 boundaries
- Both issues prevented policy convergence

**Session 12 val checkpoints (running — started 2026-07-17 11:38 CST):**

| Val step | minSharpe | avgSharpe | avg_ret | worstDD | Notes |
|---|---|---|---|---|---|
| 20K | −0.896 | +0.048 | — | — | ood_ema=0.107 (NORMAL ✓); logπ=−2.3 (healthy ✓); avg_hold=9-10b ✓ |
| **40K** | **+0.323** | **+1.438** | — | — | **NEW BEST** — all 3 regimes positive; ood_ema=1.000 again (BLOCK returned) |

Key Session 12 training metrics at step 40K (EP2):
- ROI: +10.7% (EP2), last-20 eps avg +6.0% — 10-30% target approached ✓
- Win rate: 59-74% (was 43% in S10/S11)
- tp_rate: 1-3% (was 0% in S10)
- flat_pct: 67-72% (was 79%)

**Session 12 fixes applied:**
- OOD diagnostics hard-reset after BC pretrain → ood_ema recovers (0.107 at step 20K)
- `LOG_STD_MAX: 0.0 → −0.5` — σ_max=0.6 prevents policy saturation
- `ALPHA_FIXED: 0.10 → 0.05` — tighter entropy floor
- `MIN_HOLD_BARS=8` — blocks direction-change exits before 8 bars; avg_hold 4b→9-10b
- `POS_SIZE_MAX: 0.25 → 0.60` — enables 10-30% ROI targets
- Flat penalty −0.002 — reduces excessive flat time
- TP bonus +0.005 — incentivises letting winners run to target
- Hold patience +0.0001/bar when profitable
- `VAL_REGIMES[2]: 2024-consol → 2021-H2-bull` — better out-of-training-distribution window
- `OOD_EMA_ALPHA: 0.05 → 0.15` — faster OOD adaptation

**Session 10 confirmed failure modes:**
- `DriftManager [BLOCK]  ood_ema=1.000` from step 300K → intelligence stack disabled
- `tp_rate=1–3%` → median trade PnL = −0.10% after fees → net loser
- `ALPHA_FIXED=0.3` → logπ=−2.7 constant, no entropy decline

---

## 11. Config Reference

### Session 12 Changes

```python
# ── Training / policy ──────────────────────────────────────────────────────────
ALPHA_FIXED        = 0.05             # was 0.10 (S11) — tighter entropy floor
ENTRY_THRESHOLD    = 0.10             # same as S11 — lowered to allow more trades

# ── Action space ───────────────────────────────────────────────────────────────
POS_SIZE_MAX       = 0.60             # was 0.25 (S11) — enables 10-30% ROI targets
SL_ATR_MULT_MIN    = 1.0              # was 0.5 — prevents hair-trigger stop losses
TP_ATR_MULT_MIN    = 1.5              # was 1.0 — ensures positive R:R on every trade
TP_ATR_MULT_MAX    = 3.0              # was 6.0 — tighter realistic target range

# ── Min hold ───────────────────────────────────────────────────────────────────
MIN_HOLD_BARS      = 8                # NEW — blocks direction-change exits for 8h

# ── OOD detection ──────────────────────────────────────────────────────────────
OOD_EMA_ALPHA      = 0.15             # was 0.05 (S11) / 0.01 (S10) — faster adaptation

# ── Validation regimes ──────────────────────────────────────────────────────────
VAL_REGIMES = [
    ("2022-01-01", "2022-12-31"),     # bear year (BTC -66%)
    ("2023-07-01", "2023-12-31"),     # recovery/bull (+100% H2 2023)
    ("2021-06-01", "2021-12-31"),     # mid-cycle bull (post-crash → ATH $67K) ← NEW
]                                     # replaced ("2024-01-01", "2024-06-30")
```

New data source:
```python
# dataset/BTC/1h/onchain_metrics.parquet
# Columns: fng_raw, fng_z60, fng_mom7  (3 cols from alternative.me; 4 more computed in feature_builder)
# 47,810 rows (2020-12-31 → 2026-06-16)
# Fetch: python -m DRL_BTC.scripts.fetch_onchain_metrics
```

New actor_critic.py changes:
```python
LOG_STD_MAX = -0.5    # was 0.0 — σ_max=0.6 prevents policy saturation at tanh ±1

# _INDICATOR_GROUPS additions (Session 12):
"fng_raw":    "onchain",
"fng_z60":    "onchain",
"fng_mom7":   "onchain",
"mvrv_proxy": "onchain",
"mvrv_z":     "onchain",
"yr1_mom":    "onchain",
"ath_draw":   "onchain",

# _GROUP_OUT addition:
"onchain": 10,   # 7 on-chain cols → 10-dim projection
```

### Session 11 Changes

```python
ALPHA_FIXED    = 0.10      # was 0.3 — critical fix for entropy collapse
WARMUP_TRADES  = 300       # was 500 — faster warmup (pretrained model needs less random data)
TOTAL_STEPS    = 400_000   # was 600K — pretrained model converges faster
VAL_EVERY      = 20_000    # was 10K  — paired with parallel val for same monitoring density
```

New data source:
```python
# dataset/BTC/1h/futures_metrics.parquet
# Columns: oi_contracts, oi_usd, ls_ratio, top_ls_ratio, taker_ls_vol
# 51,456 rows (2020-09-01 → 2026-07-15)
# Fetch: python -m DRL_BTC.scripts.fetch_futures_metrics
```

New encoder groups in `actor_critic.py`:
```python
# _INDICATOR_GROUPS additions:
"oi_chg":       "openinterest",   # oi_chg_1h + oi_chg_4h both strip to this base
"oi_z20":       "openinterest",
"oi_vol_ratio": "openinterest",
"oi_confirm":   "openinterest",
"oi_extreme":   "openinterest",
"oi_mom":       "openinterest",
"basis_raw":    "funding",        # basis cols added to existing funding group
"basis_z20":    "funding",
"basis_trend":  "funding",
"ls_ratio_z20": "sentiment",
"ls_extreme":   "sentiment",
"top_ls_z20":   "sentiment",
"top_retail_div":"sentiment",
"taker_ls_z20": "sentiment",

# _GROUP_OUT additions:
"openinterest": 12,   # 7 OI features → 12-dim projection
"sentiment":    12,   # 5 L/S features → 12-dim projection
```

### Full Config (Session 12 — current)

```python
# ── Data splits ────────────────────────────────────────────────────────────────
TRAIN_END   = "2024-12-31"
TEST_START  = "2025-01-01"   # OOS — never touched
VAL_REGIMES = [
    ("2022-01-01", "2022-12-31"),     # bear year
    ("2023-07-01", "2023-12-31"),     # recovery/bull
    ("2021-06-01", "2021-12-31"),     # mid-cycle bull ← S12 change (was 2024-01-01→06-30)
]

# ── Environment ────────────────────────────────────────────────────────────────
SEQ_LEN            = 48
INITIAL_CAPITAL    = 100_000.0
FEE_RATE           = 0.0004
FUNDING_PER_BAR    = 0.0001 / 8.0
MAX_DRAWDOWN_KILL  = 0.50
ENTRY_THRESHOLD    = 0.10
MIN_HOLD_BARS      = 8                # ← NEW S12 (was absent)
MAX_HOLD_BARS      = 144              # 6 days max (unchanged)

# ── Action space ───────────────────────────────────────────────────────────────
POS_SIZE_MIN     = 0.00
POS_SIZE_MAX     = 0.60              # ← S12 (was 0.25 in S11, was 0.30 in S10.1)
SL_ATR_MULT_MIN  = 1.0              # ← S12 (was 0.5)
SL_ATR_MULT_MAX  = 3.0
TP_ATR_MULT_MIN  = 1.5              # ← S12 (was 1.0)
TP_ATR_MULT_MAX  = 3.0              # ← S12 (was 6.0 in S11)

# ── SAC ────────────────────────────────────────────────────────────────────────
BUFFER_SIZE         = 100_000
BATCH_SIZE          = 512
LR_ACTOR            = 3e-4
LR_CRITIC           = 3e-4
LR_ALPHA            = 0.0            # alpha frozen
ALPHA_FIXED         = 0.05           # ← S12 (was 0.10 in S11, 0.3 in S10)
GAMMA               = 0.99
TAU                 = 0.005
UPDATE_EVERY_TRADES = 1
G_STEPS             = 10
WARMUP_TRADES       = 300
TOTAL_STEPS         = 400_000
WEIGHT_DECAY        = 1e-4

# ── Model ──────────────────────────────────────────────────────────────────────
LSTM_HIDDEN    = 256
LSTM_LAYERS    = 2
LSTM_DROPOUT   = 0.1
FC_HIDDEN      = 256
ACTION_DIM     = 4
# S12: LSTM input = 12 groups × D_ATTN(32) = 384  (was 11×32=352 in S11)

# ── Validation ─────────────────────────────────────────────────────────────────
VAL_EVERY  = 20_000
CKPT_EVERY = 50_000

# ── OOD detection ──────────────────────────────────────────────────────────────
OOD_EMA_ALPHA    = 0.15              # ← S12 (was 0.05 in S11, 0.01 in S10)
OOD_WARN_THRESH  = 3.0
OOD_BLOCK_THRESH = 0.9

# ── Knowledge Memory ───────────────────────────────────────────────────────────
KNOWLEDGE_MEMORY_SIZE = 5_000
KNOWLEDGE_MEMORY_K    = 20
MEMORY_FEAT_DIM       = 10

# ── Risk Budget ────────────────────────────────────────────────────────────────
RISK_BUDGET_DD_10 = 0.70
RISK_BUDGET_DD_20 = 0.50
RISK_BUDGET_DD_30 = 0.25
RISK_BUDGET_MIN   = 0.25
```

### Session Comparison Table

| Parameter | S7 | S8 | S9/TIA v2 | S10/TIA v3.1 | S11 | **S12 (current)** |
|---|---|---|---|---|---|---|
| Market features | 209 | 209 | 209 | 209 | 216 | **223** |
| Obs shape | (48,217) | (48,217) | (48,217) | (48,217) | (48,224) | **(48,231)** |
| Encoder groups | 9 | 9 | 9 | 9 | 11 | **12** |
| LSTM input dim | 288 | 288 | 288 | 288 | 352 | **384** |
| LSTM_HIDDEN | 256 | 512 | 512 | 256 | 256 | 256 |
| FC_HIDDEN | 256 | 512 | 512 | 256 | 256 | 256 |
| LOG_STD_MAX | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **−0.5** |
| BATCH_SIZE | 64 | 512 | 512 | 512 | 512 | 512 |
| G_STEPS | 1 | 10 | 10 | 10 | 10 | 10 |
| TOTAL_STEPS | 300K | 600K | 600K | 600K | 400K | 400K |
| WARMUP_TRADES | 500 | 500 | 500 | 500 | 300 | 300 |
| ALPHA_FIXED | 0.3 | 0.3 | 0.3 | 0.3 | 0.10 | **0.05** |
| POS_SIZE_MAX | 0.25 | 0.25 | 0.25 | 0.30 | 0.25 | **0.60** |
| SL_ATR_MULT_MIN | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | **1.0** |
| TP_ATR_MULT range | 1–6 | 1–6 | 1–6 | 1–6 | 1–6 | **1.5–3.0** |
| MIN_HOLD_BARS | — | — | — | — | — | **8** |
| OOD_EMA_ALPHA | — | — | — | 0.01 | 0.05 | **0.15** |
| VAL_EVERY | 10K | 10K | 10K | 10K | 20K | 20K |
| Val regime 3 | 2022 | 2022 | 2022 | 2022 | 2024-consol | **2021-H2-bull** |
| Parallel val | No | No | No | No | Yes (3 workers) | same |
| OI features | — | — | — | 7 (zeros) | 7 (real) | same |
| Basis features | — | — | — | 3 (zeros) | 3 (real) | same |
| L/S sentiment | — | — | — | — | 5 (new) | same |
| On-chain/cycle | — | — | — | — | — | **7 (new)** |
| Flat penalty | — | — | — | — | — | **−0.002** |
| TP bonus | — | — | — | — | — | **+0.005** |
| Hold patience rwd | — | — | — | — | — | **+0.0001/bar** |
| OOD diagnostics reset | — | — | — | — | — | **Yes (after BC pretrain)** |
| OOD detection | — | — | MarketDiag | +DriftManager | same | same |
| KnowledgeMemory | — | — | — | live path | same | same |
| AMP (FP16) | — | — | — | Yes | same | same |
| torch.compile critics | — | — | — | aot_eager | same | same |

---

## Change History

| Session | Change | Reason |
|---|---|---|
| 1 | PerspectiveEncoder + MHA + LSTM | Better multi-TF feature processing |
| 1 | BC direction pre-training | Bake in domain knowledge before SAC |
| 1 | Composite signals (macro/swing/entry/regime) | Explicit strategy knowledge |
| 2 | MAX_LEVERAGE 5×→2×, MAX_POS 95%→50% | 5× leverage = ruin during early learning |
| 2 | Trend-alignment reward | Teach agent to use composite signals |
| 3 | ALPHA_FIXED=0.3, LR_ALPHA=0 | Stop entropy collapse |
| 4 | LOG_STD clamp (MAX=0, MIN=−3) | σ_max was 7.4; now capped at 1.0 |
| 5 | Direction rule-based, PER buffer, 2022 val | Actor controls exit only |
| 5 | **Bug**: Q cycling ±Sharpe every 20K | Root: exit_signal bistable |
| 6 | 5D action, ATR-based SL/TP, trailing stop | Real risk management |
| 6 | **Bug**: Q cycling persists | BC couldn't override exit_signal |
| 7 | exit_signal removed → 4D action | Eliminates bistable Q attractors |
| 7 | Trade-level replay buffer | Q(entry) = E[trade_pnl] directly |
| 7 | **OOS: −6.81% Sharpe −0.99** | Val=2022 bear; OOS=2025 bull → mismatch |
| 8 | LSTM/FC 256→512, batch 64→512 | 2× capacity, GPU efficiency |
| 8 | G_STEPS 1→20, UPDATE_EVERY 5→1 | 20× UTD ratio |
| 8 | SharedModel pretrain (Beta+Alpha) | Warm-start encoder on regime/return |
| 8 | G_STEPS 20→10 | 160× too heavy; 80× vs Session 7 is enough |
| 9 | **BetaEngine**: +regime_stability head | Know if regime will persist |
| 9 | **AlphaEngine**: +p10/p50/p90 quantiles, sl_prob, exp_vol, alpha_confidence | Full return distribution + tail risk |
| 9 | **MarketDiagnostics**: EMA z-space OOD detector | Detect when market deviates from training |
| 9 | **ConfidenceGate**: EXECUTE/REDUCE/SKIP + size_mult | Gate replaces direction fusion |
| 9 | POS_SIZE_MIN 0.05 → 0.00 | Actor can soft-skip trades |
| 9 | Multi-regime val (3 windows) | Fix single-regime OOS failure root cause |
| 9 | Early-stop: ret_pct → min Sharpe | Robustness across all regimes |
| 9 | weight_decay=1e-4 in Adam | L2 regularisation |
| 10 | **BetaEngine**: +regime_embedding(32), vol_class, transition_prob, calib_confidence | Richer regime context |
| 10 | **AlphaEngine**: +exp_variance, tail_risk, exp_max_dd | Intraperiod risk prediction |
| 10 | OOD correction: Bayesian dampening of regime_probs | Calibration-standard approach |
| 10 | **Rule Engine**: explicit rule_feat(3) | Rule direction/confidence/active directly to gate |
| 10 | **Risk Budget Controller**: tiered DD-based scaling | Belt-and-suspenders position sizing |
| 10 | **KnowledgeMemory**: 5K ring buffer | Past-trade pattern recall at inference |
| 10 | **DriftManager**: NORMAL/WARNING/BLOCK | OOD EMA + calibration + return drift |
| 10 | LSTM_HIDDEN / FC_HIDDEN reset to 256 | Richer fusion (z+69) compensates; faster T4 |
| 10 | AMP (GradScaler + autocast float16) | ~2× GPU throughput on T4 Tensor Cores |
| 10 | torch.compile critics (aot_eager) | Faster critic forward/backward |
| 10.1 | **KnowledgeMemory wired into live path** | retrieve_feat → 10-dim memory_feat to DecisionFusion + policy |
| 10.1 | **OOD-gated memory retrieval**: k=20/10/5/0 | Avoids irrelevant memories when OOD |
| 10.1 | **DriftManager active**: get_beta_temperature(), get_memory_k() | Temperature scaling + k gating |
| 10.1 | **DecisionFusion input**: +memory_feat(10) + risk_budget(1) | Gate can SKIP at high DD |
| 10.1 | **⚠ Bug: OOD permanently BLOCK** (ood_ema=1.000) | OOD_EMA_ALPHA=0.01 too slow after BC pretrain |
| 10.1 | **⚠ Issue: ALPHA_FIXED=0.3 prevents convergence** | logπ=−2.7 constant across 350K steps |
| 10.1 | Training crashed at step 350K | Likely T4 OOM; best saved at ~260K |
| **11** | **ALPHA_FIXED 0.3 → 0.10** | Fix entropy collapse — policy can now converge |
| **11** | **OI features: 7 zeros → 7 real** | OI data from Binance bulk portal (2020-09-01 →) |
| **11** | **L/S sentiment: 5 new features** | ls_ratio_z20, ls_extreme, top_ls_z20, top_retail_div, taker_ls_z20 |
| **11** | **Basis features: 3 zeros → 3 real** | basis_raw, basis_z20, basis_trend (spot-futures carry) |
| **11** | **PerspectiveEncoder: 9 → 11 groups** | +openinterest(7→12d) +sentiment(5→12d) |
| **11** | **LSTM input: 9×32=288 → 11×32=352** | Architecture change requires full retrain from scratch |
| **11** | **Composite signals updated** | macro_score +OI confirm/crowd; swing_score +smart-money div; entry_score +taker L/S; regime_score +OI build |
| **11** | **Market features: 209 → 216** | 15 real futures metrics features (was 10 zero-filled cols) |
| **11** | **Obs shape: (48,217) → (48,224)** | 216 market + 8 portfolio |
| **11** | **Parallel val: ThreadPoolExecutor(3 workers)** | 3 regime windows run concurrently; ~3× faster val |
| **11** | **VAL_EVERY: 10K → 20K** | Combined with parallel val: ~38% faster total wall-clock |
| **11** | **TOTAL_STEPS: 600K → 400K** | Pretrained model converges faster |
| **11** | **WARMUP_TRADES: 500 → 300** | Pretrained actor needs less random data for buffer seeding |
| **11** | **⚠ Failed: OOD BLOCK** | BC pretrain shifted encoder z-space; OOD_EMA_ALPHA=0.01 too slow; ood_ema=1.000 from step 1 |
| **11** | **⚠ Failed: logπ saturation** | LOG_STD_MAX=0.0 → σ_max=1.0 → policy tanh-saturated |
| **12** | **OOD diagnostics hard-reset after BC pretrain** | Hard-zero n_updates/running_mean/std + ood_ema=0.0; ood recovers to 0.107 at step 20K |
| **12** | **LOG_STD_MAX: 0.0 → −0.5** | σ_max=0.6 prevents policy saturation; logπ=−2.3 (healthy) vs −2.7 (stuck) |
| **12** | **ALPHA_FIXED: 0.10 → 0.05** | Tighter entropy floor; faster convergence |
| **12** | **On-chain/cycle features: 7 new** | fng_raw/z60/mom7 (F&G from alternative.me) + mvrv_proxy/z + yr1_mom + ath_draw |
| **12** | **PerspectiveEncoder: 11 → 12 groups** | +onchain(7→10d); LSTM input 352→384 |
| **12** | **Market features: 216 → 223** | 7 new on-chain cols |
| **12** | **Obs shape: (48,224) → (48,231)** | 223 market + 8 portfolio |
| **12** | **MIN_HOLD_BARS=8** | Blocks direction-change exits in first 8 bars; avg_hold 4b→9-10b |
| **12** | **POS_SIZE_MAX: 0.25 → 0.60** | Enables 10-30% ROI per episode targets |
| **12** | **SL_ATR_MULT_MIN: 0.5 → 1.0** | Prevents hair-trigger stops (sl_hit was too frequent at 0.5×) |
| **12** | **TP_ATR_MULT range: 1–6 → 1.5–3.0** | Tighter realistic target; tp_prob improved from 0% to 1-3% |
| **12** | **Flat penalty: −0.002** | Penalises soft-skip when signal fires; flat_pct 79% → 67-72% |
| **12** | **TP bonus: +0.005** | Explicit incentive to let winners reach full target |
| **12** | **Hold patience reward: +0.0001/bar** | Small bonus when bar_pnl > 0.2% — rewards staying in winning trade |
| **12** | **VAL_REGIMES[2]: 2024-consol → 2021-H2-bull** | 2021-06-01→12-31 adds mid-cycle bull unseen in training; 2024 was too close to training end |
| **12** | **OOD_EMA_ALPHA: 0.05 → 0.15** | Faster adaptation to RL z-distribution after pretrain |
| **12** | **Step 40K: avgSharpe=+1.438, all regimes positive** | New best checkpoint; training continues to 400K |
