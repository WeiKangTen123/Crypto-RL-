# Strategy Forge — Complete Flow
> Last updated: 2026-06-23 (session 10)
> Explains every layer of strategy_forge/ from raw indicator to registered strategy

---

## OVERVIEW

Strategy Forge is an automated strategy discovery system. It assembles trading strategies from modular building blocks (entry signal + filters + exit method + params), backtests them, scores them, and surfaces the best for registration in `settings.py`.

```
OHLCV Data
    │
    ▼
[indicators/]          ← raw math functions (RSI, EMA, ATR, FVG, OBV, etc.)
    │
    ▼
[signals/]             ← entry signals, filters, exit methods (use indicators)
    │
    ▼
[composer/dna.py]      ← StrategyDNA glues entry + filters + exit into one object
    │
    ▼
[composer/random_compose.py]   ← generates random populations of DNAs
[composer/genetic.py]          ← OR evolves populations over generations
    │
    ▼
[runner/backtest_runner.py]    ← plugs each DNA into BacktestEngine, returns score + style metadata
    │
    ▼
[scripts/random_search.py]     ← run N random DNAs, print + save top results
[scripts/evolve.py]            ← run genetic search, evolve N generations
[scripts/mtf_search.py]        ← targeted MTF search (2-3%/mo, MDD~15%, 3-7/wk)
[scripts/sniper_swing_search.py] ← LTF entry (5m/15m) + HTF bias + 1-4h hold
[scripts/hft_search.py]        ← HFT/scalp search (5m/15m, 1-10 bar hold, 20-100/wk)
    │
    ▼
[results/*.json]               ← top-N candidate DNAs + metrics (incl. style label), saved per run
    │
    ▼
Manual review → register best in strategy_backtest/settings.py
```

---

## LAYER 1 — INDICATORS (`strategy_forge/indicators/`)

Raw math functions. Each takes a DataFrame and returns a computed Series or tuple.

| File | What's inside |
|---|---|
| `momentum.py` | RSI, MACD, KDJ, Stoch RSI, Williams %R, Elder Ray, DPO, WaveTrend, MFI, vRSI, Fisher, Aroon |
| `trend.py` | EMA, SMA, ZLEMA, HMA, Supertrend, ADX/DMI, Parabolic SAR, Vortex |
| `volatility.py` | ATR, Bollinger Bands, Keltner Channel, Squeeze |
| `volume.py` | VWAP, CVD, Taker Ratio, Volume Z-Score, OBV |
| `structure.py` | FVG, Imbalance Zone (IMB), Z-Score, Candle Patterns, Order Blocks |

All indicators are imported via `strategy_forge/indicators/__init__.py` and used inside signal files.

---

## LAYER 2 — SIGNALS (`strategy_forge/signals/`)

### 2A — Entry Signals (`entry_signals.py`)

Each entry function returns a `pd.Series` of `int`:
- `+1` = Long signal
- `-1` = Short signal
- `0` = No signal

All use the helper `_sig(long_cond, short_cond)` so every entry generates both long and short signals simultaneously.

**37 registered entry signals:**

| Category | Signals |
|---|---|
| Momentum | `rsi_reversion`, `rsi_trend`, `macd_cross`, `macd_zero_cross`, `kdj_reversion`, `wavetrend`, `mfi_reversion`, `vrsi_reversion`, `fisher`, `stoch_rsi_reversion`, `williams_r_reversion`, `elder_ray`, `dpo_reversion` |
| Trend | `ema_cross`, `ema_price_cross`, `supertrend`, `zlema_cross`, `hma_cross`, `parabolic_sar`, `vortex_cross`, `aroon_cross` |
| Volatility/Structure | `bb_reversion`, `bb_breakout`, `keltner_reversion`, `squeeze_breakout`, `fvg`, `imbalance_zone`, `fvg_zone_touch` |
| Volume/Flow | `vwap_reversion`, `cvd_cross`, `taker_momentum`, `zscore_reversion` |
| Candle Patterns | `candle_engulfing` (bull/bear engulfing), `candle_pin_bar` (hammer/shooting star) |
| Order Flow | `order_block` (institutional OB mitigation, bullish/bearish touch) |
| Z-Score *(session 8)* | `zscore_ema` (z-score of price vs EMA, `ema_trend`/`zscore_period`/`zscore_threshold`), `zscore_htf` (HTF z-score forward-filled to LTF, `htf_bars`/`zscore_period`/`zscore_threshold`) |
| Funding Rate *(session 8)* | `funding_rate_mr` (fade extreme funding: `fr_long_thresh`/`fr_short_thresh`, loads from parquet, best on 4h) |

> **Candle entries** take no params — they fire purely on bar structure.
> **`order_block`** uses `atr_period`, `atr_multiplier`, `lookback` to qualify block origin and size.
> **`zscore_ema`**: long when `(Close - EMA) / rolling_std < -threshold`, short when `> +threshold`. Mean reversion.
> **`zscore_htf`**: resamples Close to HTF, computes z-score there, forward-fills to LTF bars. Combines HTF regime with LTF timing.
> **`funding_rate_mr`**: loads `{coin}_funding_rate.parquet`, forward-fills to bar frequency. Extreme positive funding → go short (longs overlevered); extreme negative → go long.

### 2B — Filters (`filter_signals.py`)

Each filter returns a `pd.Series` of `bool`.
- `True` = allow the signal through
- `False` = block signal (set to 0)

Multiple filters are **ANDed together** — ALL must be True for a signal to pass.

**19 registered filters:**

| Filter | Blocks when |
|---|---|
| `adx_trend` | trend strength weak (ADX < threshold) |
| `ema_trend_long` | price below trend EMA (biases strategy to longs-only in uptrend) |
| `ema_trend_short` | price above trend EMA (biases strategy to shorts-only in downtrend) |
| `supertrend_dir` | Supertrend is bearish — blocks ALL signals (both long and short) |
| `no_squeeze` | BB/Keltner squeeze is active |
| `vol_expansion` | volume below MA × multiplier |
| `atr_expansion` | ATR below its own rolling average |
| `rsi_not_extreme` | RSI is already overbought or oversold |
| `taker_confirm` | taker buy ratio ≤ 0.5 (sellers dominating) |
| `psar_trend` | Parabolic SAR is bearish |
| `vortex_trend` | VI+ < VI- (no confirmed trend) |
| `hma_slope` | HMA sloping downward |
| `wr_not_extreme` | Williams %R at extreme levels |
| `htf_ema_trend` *(MTF)* | price below higher-TF EMA (e.g. 4h EMA on 1h data) |
| `htf_supertrend` *(MTF)* | higher-TF Supertrend is bearish |
| `obv_trend` | OBV below its SMA (volume not accumulating) |
| `ob_buy_pressure` | order book bid imbalance below threshold (sellers winning) |
| `ob_sell_pressure` | order book ask imbalance above threshold (buyers winning) |
| `funding_rate_bias` *(session 8)* | funding rate ≥ `fr_long_threshold` (0.01%/8h default) — blocks longs when funding is positive/elevated (bubble risk). Falls back to True on missing data. |
| `dual_htf_trend` *(session 10)* | BOTH HTF1 and HTF2 must have Close above EMA simultaneously. `htf1_bars` + `htf2_bars` define the two levels (e.g. 12×5m=1h and 48×5m=4h). Strongest regime gate — drops trade frequency but sharply raises quality. |
| `macro_regime` *(session 10)* | Highest-level Supertrend check resampled to `macro_bars` (e.g. 288×5m=1d). Filters out all counter-trend entries during bear markets. Falls back to True on error or insufficient data. |

> **MTF filters** (`htf_ema_trend`, `htf_supertrend`) auto-detect the base TF from the DatetimeIndex and compute the correct resample rule (e.g. 5m data + htf_bars=48 → '240min' = 4h). This is correct for ALL base timeframes (5m, 15m, 30m, 1h). Requires DatetimeIndex.
>
> **Bug fixed (2026-06-19):** Previously the resample rule was `f'{htf_bars}h'` — on 5m data with htf_bars=48 this produced 48-hour (2-day) bars instead of 4h. Now uses `_htf_resample_rule(df, htf_bars)` which derives the target duration from the actual index spacing.

### 2C — Exit Methods (`exit_signals.py`)

Each exit function is called inside `manage_trade()` every bar during an open trade. Returns `(action, price)`.

| Exit Method | Logic |
|---|---|
| `atr_tp_sl` | ATR-based TP + SL |
| `pct_tp_sl` | Fixed % TP + SL |
| `rr_ratio` | Fixed SL %, TP = SL × RR multiple |
| `max_hold` | Exit after N bars (time stop) |
| `atr_tp_sl_hold` | ATR TP/SL + max hold bars (most common for sniper-swing) |
| `chandelier` | Trailing stop via Chandelier Exit |
| `chandelier_tp` | Chandelier stop + fixed ATR take-profit |
| `supertrend_trail` | Trail stop via Supertrend direction flip |
| `tight_atr` | Asymmetric ATR: small SL, large TP |
| `breakeven_trail` | Move SL to entry once price reaches `be_trigger_mult × ATR`, then trail at `atr_multiplier × ATR` from peak. Best for HFT — cuts losers fast. |
| `rsi_exit` | Exit when RSI crosses back through `rsi_threshold` (default 50) against trade direction. Requires `_rsi` pre-computed in `generate_signals()`. |
| `trailing_tp` *(session 8)* | Phase 1: hard SL at `sl_atr_mult × ATR`. Phase 2 once `tp_activation_mult × ATR` profit reached: trail exit at `peak − tp_trail_mult × ATR`. Tagged 'TP'. |
| `psar_trail` *(session 8)* | Parabolic SAR trailing stop using `_psar_prev` (previous bar's SAR = actual stop level). Low-touch trigger matches chandelier pattern. Requires `parabolic_sar_raw()`. |
| `vol_adaptive_sl` *(session 8)* | SL = `sl_atr_mult × clamp(current_ATR/avg_ATR, 0.5, 3.0) × ATR`. Widens in high-vol, tightens in low-vol. Requires `_atr_avg` pre-computed. |

> **State persistence bug (fixed 2026-06-23):** `dna.py` was creating `p = {**self.params}` fresh each bar, wiping all state written by exit functions (`_peak`, `_ttp_active_long`, `_be_hit_long`, etc.). Fixed with `self._exit_state = {}` persisted on the StrategyDNA instance across bars and reset on position close. This made `chandelier`, `breakeven_trail`, `trailing_tp` work correctly for the first time — `chandelier_tp` in particular now properly trails the running peak.
>
> **PSAR raw values bug (fixed 2026-06-23):** `psar_trail` was using `parabolic_sar()` which returns direction (±1), not SAR price levels — causing the exit to never trigger. Fixed with `parabolic_sar_raw()` in `indicators/trend.py`. Exit also now uses `_psar_prev` so the stop level is the previous bar's SAR (not the current bar's, which has already flipped above close).

---

## LAYER 3 — COMPOSER (`strategy_forge/composer/`)

### `dna.py` — StrategyDNA

The core object. Wraps entry + filters + exit into a single strategy that plugs into `BacktestEngine`.

```python
StrategyDNA(df, entry='ema_cross', filters=['htf_ema_trend', 'taker_confirm'],
            exit_method='atr_tp_sl_hold', params={...})
```

**`generate_signals()` flow inside StrategyDNA:**
```
1. compute_entry_signal(entry, df, params)    → raw Series (+1/-1/0)
2. for each filter: allow &= compute_filter(filter, df, params)
3. raw_signal = raw_signal.where(allow, 0)   → filtered signals
4. df['_atr'] = atr(df, atr_period)          → pre-compute for exit use
5. if exit == 'supertrend_trail': df['_st_direction'] = supertrend(...)
6. if exit == 'rsi_exit':         df['_rsi'] = rsi(df, rsi_period)   ← new
7. return df with df['signal'] column
```

**`manage_trade()` flow (called each bar while in trade):**
```
1. increment bars_held counter (long or short)
2. compute_exit(exit_method, row, position, entry_price, params)
3. returns ('TP'/'SL'/'EXIT'/'HOLD', exec_price)
4. on TP/SL/EXIT → reset bars_held counter
```

### `random_compose.py` — Random DNA Generator

Generates random StrategyDNA instances by:
1. Pick 1 entry from ENTRY_SIGNAL_REGISTRY at random
2. Pick 0–2 filters from FILTER_REGISTRY at random
3. Pick 1 exit from EXIT_REGISTRY at random
4. Sample all required params from `params/ranges.py` DEFAULT_RANGES

`random_population(df, size=100)` generates N DNAs for batch testing.

`_ENTRY_PARAMS`, `_FILTER_PARAMS`, `_EXIT_PARAMS` dicts map each signal to its required param names. Updated for all new signals.

### `genetic.py` — Genetic Evolution

Evolves a population over generations:
- Keep top `survivors` DNAs
- Breed `offspring` by crossing two parent DNAs (swap entry/filters/exit)
- Mutate some params (random re-sample within range)
- Repeat for N generations

> **Note:** Genetic evolution is style-unaware — mutated DNAs may cross style boundaries (e.g., HFT params → swing entry signal). `hft_search.py` and `sniper_swing_search.py` re-enforce style constraints after each generation.

---

## LAYER 4 — PARAMS (`strategy_forge/params/ranges.py`)

Single source of truth for all parameter search spaces. Maps param name → `(min, max)` tuple.

```python
DEFAULT_RANGES = {
    'ema_fast':         (5,    30),
    'ema_slow':         (20,  200),
    'atr_period':       (5,    30),
    'tp_atr_mult':      (1.0,  8.0),
    'sl_atr_mult':      (0.5,  3.0),
    'htf_bars':         (2,     8),   # MTF: bar-count multiplier; 1h data → 2=2h, 4=4h, 8=8h
    'be_trigger_mult':  (0.3,  2.0),  # ← new: breakeven trigger distance in ATR
    'ob_lookback':      (2,    10),   # ← new: order block lookback bars
    ...
}
```

`sample_params(param_names, seed)` randomly picks one value per param from its range.
Integer ranges → `randint`. Float ranges → `uniform`.

---

## LAYER 5 — RUNNER (`strategy_forge/runner/backtest_runner.py`)

Plugs StrategyDNA into the existing BacktestEngine.

**`score_dna(dna, df, risk, score_mode, min_trades)`:**
```
1. Create fresh DNA copy with df
2. BacktestEngine.run() → equity curve
3. compute_metrics() → Sharpe, ROI, MDD, WR, Trades, PF
4. Filter out DNAs with trades < min_trades OR MDD > 80%
5. Compute trades_per_week and style label        ← new
6. Score by 'roi' / 'sharpe' / 'blend' (0.5×log(ROI) + 0.5×Sharpe)
7. Return (score, metrics_dict)
```

**Style classification (added to every metrics dict):**
| style | trades_per_week |
|---|---|
| `hft` | ≥ 30/wk |
| `mft` | 8–29/wk |
| `swing` | 2–7/wk |
| `position` | < 2/wk |

**`score_population(population, df, ...)`:**
Runs `score_dna` for all DNAs, sorts descending by score, returns list of `(score, dna, metrics)`.
Verbose print now includes `trades_per_week` and `[style]` label per strategy.

---

## LAYER 6 — SCRIPTS (entry points)

### `random_search.py` — General Random Search

```bash
python strategy_forge/scripts/random_search.py \
    --coin ETH --tf 4h --n 200 --score blend --top 10

# With style preset:
python strategy_forge/scripts/random_search.py \
    --coin BTC --tf 5m --n 300 --style hft
python strategy_forge/scripts/random_search.py \
    --coin ETH --tf 1h --n 200 --style swing
```

Key args:
| Arg | Default | Meaning |
|---|---|---|
| `--coin` | BTCUSDT | Coin to test |
| `--tf` | 1h | Timeframe |
| `--n` | 100 | Number of random strategies |
| `--top` | 10 | How many to save |
| `--score` | roi | Scoring: `roi` / `sharpe` / `blend` |
| `--min_trades` | 20 | Disqualify if fewer trades |
| `--max_filters` | 2 | Max filters per strategy |
| `--style` | None | `hft` / `mft` / `swing` — adjusts min_trades/risk/leverage defaults |

> **`--style hft`** sets: min_trades=50, leverage=3, risk=0.005, max_filters=1.
> For a dedicated HFT search with curated signal pools use `hft_search.py`.

### `evolve.py` — Genetic Search

```bash
python strategy_forge/scripts/evolve.py \
    --coin ETH --tf 4h --pop 60 --generations 20 --score blend
```

Runs multi-generation genetic algorithm. Each generation: score → keep survivors → breed offspring → mutate → repeat.

### `mtf_search.py` — MTF-Targeted Search

```bash
python strategy_forge/scripts/mtf_search.py --coin ETH --tf 1h --n 200
python strategy_forge/scripts/mtf_search.py --coin BTC --tf 1h --n 300 --score blend
```

Targets 1h data with HTF filters. Phase 1: 10 hand-crafted compositions (including `breakeven_trail`). Phase 2: N random MTF candidates. Combined ranking saved to results/. Now fully CLI-parametric.

| Arg | Default | Meaning |
|---|---|---|
| `--coin` | ETH | Coin |
| `--tf` | 1h | Base timeframe |
| `--n` | 200 | Random population size |
| `--score` | blend | Scoring mode |
| `--risk` | 0.05 | risk_per_trade |

### `sniper_swing_search.py` — LTF-Entry / HTF-Bias / Swing-Hold

```bash
python strategy_forge/scripts/sniper_swing_search.py --tf 5m --coin BTC --n 300
python strategy_forge/scripts/sniper_swing_search.py --tf 15m --coin ETH --n 200 --phase2 --evolve
```

LTF (5m/15m) precision entry + HTF (1h/4h) bias filter + 1-4h forced time stop.
HTF resample bug fix applied — htf_bars on 5m data now correctly maps to 4h bars (not 48h).

### `hft_search.py` — HFT / Scalp Search *(new)*

```bash
python strategy_forge/scripts/hft_search.py --coin BTC --tf 5m --n 300
python strategy_forge/scripts/hft_search.py --coin ETH --tf 15m --n 200 --phase2
python strategy_forge/scripts/hft_search.py --coin BTC --tf 5m --n 400 --phase2 --evolve --generations 5
```

Dedicated HFT search targeting 20-100 trades/week. Features:
- Curated signal pool: `stoch_rsi_reversion`, `williams_r_reversion`, `candle_engulfing`, `candle_pin_bar`, `bb_reversion`, `wavetrend`, `vwap_reversion`, `imbalance_zone`, `order_block`
- 0-1 filters only (more signals)
- HFT-tuned exits: `breakeven_trail` (primary), `tight_atr`, `rsi_exit`, `max_hold`
- Overrides: max_hold_bars=1-10, sl_atr_mult=0.3-0.8, tp_atr_mult=1.5-4.0
- Custom `_hft_score()` that rewards frequency (20-100/wk) and PF ≥ 1.3
- 3 phases: random → hand-crafted → genetic evolution

| Arg | Default | Meaning |
|---|---|---|
| `--coin` | BTC | Coin |
| `--tf` | 5m | Entry timeframe (5m or 15m) |
| `--n` | 300 | Phase 1 population size |
| `--min_trades` | 50 | Min trades to qualify (higher for HFT) |
| `--risk` | 0.005 | Low risk per trade (HFT default) |
| `--leverage` | 3.0 | Lower leverage for HFT |
| `--phase2` | off | Run hand-crafted HFT candidates |
| `--evolve` | off | Run genetic evolution phase |

### `multi_forge_search.py` — Multi-Coin Multi-TF Search *(session 10)*

```bash
# Search across all 10 coins at 1h (recommended first run)
python strategy_forge/scripts/multi_forge_search.py --tf 1h --coins all --n 300

# Sniper-swing: 15m entry with 1h+4h regime on liquid coins
python strategy_forge/scripts/multi_forge_search.py --tf 15m --coins BTC,ETH,SOL,BNB --n 300

# Daily swing across all 10 coins
python strategy_forge/scripts/multi_forge_search.py --tf 4h --coins all --n 300

# Full sweep: all TFs, all 10 coins
python strategy_forge/scripts/multi_forge_search.py --tf all --coins all --n 200
```

Architecture: every DNA uses **LTF entry + dual-HTF regime + optional macro guard**.

**TF hierarchy (auto-wired — no manual tuning needed):**

| Base TF | HTF1 (bars) | = | HTF2 (bars) | = | Macro (bars) | = |
|---------|-------------|---|-------------|---|--------------|---|
| 5m | 12 | 1h | 48 | 4h | 288 | 1d |
| 15m | 4 | 1h | 16 | 4h | 96 | 1d |
| 1h | 4 | 4h | 24 | 1d | 168 | 1w |
| 4h | 6 | 1d | 42 | 1w | — | — |
| 1d | 7 | 1w | — | — | — | — |

**10 supported coins:** BTC, ETH, BNB, SOL, XRP, AVAX, LINK, ADA, MATIC, DOT

**3-phase search:**
1. **Random** — N random DNAs scored across all selected coins (multi-coin avg)
2. **Presets** — 10–12 hand-crafted MTF combos with proven signal pairs
3. **Evolution** — genetic evolution of top survivors, HTF params re-pinned after mutation

**Preset catalog (11 combos per TF):**

| Name | Entry | Filters | Exit |
|------|-------|---------|------|
| ema_dual_htf_chandelier | ema_cross | dual_htf_trend, adx_trend | chandelier_tp |
| supertrend_macro_trailing | supertrend | macro_regime, atr_expansion | trailing_tp |
| hma_dual_htf_atr | hma_cross | dual_htf_trend, obv_trend | atr_tp_sl |
| zlema_dual_htf_st_trail | zlema_cross | dual_htf_trend, taker_confirm | supertrend_trail |
| bb_breakout_macro_chandelier | bb_breakout | macro_regime, vol_expansion | chandelier_tp |
| fvg_dual_htf_atr | fvg | dual_htf_trend, wr_not_extreme | atr_tp_sl |
| cvd_macro_psar | cvd_cross | macro_regime, htf_ema_trend | psar_trail |
| elder_ray_dual_htf_be | elder_ray | dual_htf_trend, adx_trend | breakeven_trail |
| stochrsi_macro_tight_atr *(scalp)* | stoch_rsi_reversion | macro_regime, dual_htf_trend | tight_atr |
| williams_macro_be *(scalp)* | williams_r_reversion | macro_regime, atr_expansion | breakeven_trail |
| imb_dual_htf_atr | imbalance_zone | dual_htf_trend, taker_confirm | atr_tp_sl |
| aroon_macro_st_trail | aroon_cross | macro_regime, dual_htf_trend | supertrend_trail |

Key args:
| Arg | Default | Meaning |
|-----|---------|---------|
| `--coins` | all | Comma-separated coins or "all" (10 cryptos) |
| `--tf` | 1h | Base TF or "all": 5m,15m,1h,4h,1d |
| `--n` | 300 | Random candidates per TF |
| `--generations` | 8 | Evolution generations |
| `--offspring` | 40 | Children per generation |
| `--risk_per_trade` | 0.05 | Fraction of balance per trade |
| `--leverage` | 5.0 | Leverage multiplier |

> **HTF params are auto-pinned after each mutation** so evolution cannot accidentally break the TF hierarchy (e.g. mutating `htf1_bars` to a value incompatible with the base TF). Entries/exits are constrained per TF style: `scalp` pool for 5m/15m, `swing` pool for 1h/4h, `daily` pool for 1d.

### `alpha_forge_search.py` — Targeted Alpha Search *(session 8)*

```bash
python strategy_forge/scripts/alpha_forge_search.py --coin ETH --tf 5m --n 200
python strategy_forge/scripts/alpha_forge_search.py --coin BTC --tf 15m --n 150 --top 10
python strategy_forge/scripts/alpha_forge_search.py --coin ETH --tf 4h --n 100 --mode funding
```

Tests new playstyles (exits A/B/C + entries D/E/F) against validated signal combos. Not a general random search — applies research-derived quad-filter combo (`htf_ema_trend + atr_expansion + obv_trend + adx_trend`) to every candidate.

Playstyle modes:
| Mode | Entries tested | Exits tested |
|---|---|---|
| `trend` (default) | `supertrend`, `ema_cross`, `hma_cross`, `zlema_cross` | all exits |
| `reversion` | `zscore_ema`, `zscore_htf`, `zscore_reversion`, `stoch_rsi_reversion`, `williams_r_reversion`, `vwap_reversion` | all exits |
| `structure` | `fvg_zone_touch`, `order_block`, `imbalance_zone`, `taker_momentum` | all exits |
| `funding` | `funding_rate_mr` | all exits |

Phase 1: hand-crafted preset candidates (10-16 combos). Phase 2: N random candidates from specified mode. Results saved to `phase_6_agent_monitor/alpha_forge_v2/dev_report/`.

**Alpha search conclusions (ETH 5m, 2022-2026):** None of the new exits beat `supertrend_trail` outright on 5m ETH. Mean reversion modes performed poorly on this TF. `psar_trail` tuned: +0.84%/mo, `vol_adaptive_sl`: +0.55%/mo vs `supertrend_trail`: +2.41%/mo. The `chandelier_tp` exit now shows dramatically better results post-state-fix (+4590% on 2023-2026 ETH bull run due to correct peak accumulation).

### `report.py` — Results Reporter

Reads JSON files from `results/` and prints formatted leaderboard.
Results now include `trades_per_week` and `style` fields.

---

## LAYER 7 — RESULTS & REGISTRATION

### Results (`strategy_forge/results/*.json`)

Each search run saves a JSON with:
```json
{
  "run_at": "...", "style": "hft", "coin": "BTC", "tf": "5m",
  "n_tested": 300, "n_valid": 87,
  "top_results": [
    {
      "rank": 1, "score": 12.4,
      "entry": "candle_engulfing", "filters": ["adx_trend"],
      "exit_method": "breakeven_trail",
      "params": {"sl_atr_mult": 0.5, "be_trigger_mult": 0.4, ...},
      "metrics": {
        "total_return": 320, "sharpe": 1.8,
        "trades_per_week": 45.2, "style": "hft"
      }
    }
  ]
}
```

### Manual Registration (`strategy_backtest/settings.py`)

After reviewing results, manually register the best DNA as a new strategy ID:

```python
"131": {
    "id":    "FORGE_HFT_BTC_5M_CANDLE_BE",
    "class": "ForgeStrategy",
    "params": {
        "entry":       "candle_engulfing",
        "filters":     ["adx_trend"],
        "exit_method": "breakeven_trail",
        ...
    },
}
```

`ForgeStrategy` (in `strategy_backtest/strategies/forge_strategy.py`) is a thin wrapper that constructs a `StrategyDNA` from the settings params and delegates all logic to it.

---

## REGISTERED STRATEGIES (IDs 117–130)

| ID | Name | Entry | Filters | Sharpe | ROI | MDD |
|---|---|---|---|---|---|---|
| 117 | ZLEMA_TAKER_MAXHOLD | zlema_cross | taker_confirm | 1.48 | 512% | — |
| 118 | BB_BREAKOUT_EMA_ATR | bb_breakout | ema_trend_long | 1.18 | 190% | 32% |
| 119 | RSI_TREND_STABLE | rsi_trend | atr_expansion, ema_trend_long | 1.04 | — | 23% |
| 120 | EMA_SUPERTREND | ema_cross | supertrend_dir | 1.49 | — | <1% |
| 121 | BB_ATR_CLEAN | bb_breakout | — | 1.31 | — | <2% |
| 122 | CVD_CHANDELIER | cvd_cross | — | 1.22 | — | <2% |
| 123 | ELDER_RAY_CHANDELIER | elder_ray | — | 1.00 | — | — |
| 124 | HMA_TIGHT_ATR | hma_cross | — | 1.19 | 511% | 43% |
| 125 | FVG_TAKER_WR_ATR | fvg | taker_confirm, wr_not_extreme | **1.46** | **854%** | 40% |
| 126 | BTC_ELDER_RAY_ATR | elder_ray (BTC) | — | 1.03 | 255% | 42% |
| 127 | EMA_WR_SHORT_TIGHT | ema_price_cross | wr_not_extreme, ema_trend_short | 1.24 | 283% | 26% |
| 128 | AROON_VORTEX_EMA | aroon_cross | vortex_trend, ema_trend_long | 0.78 | 163% | 37% |
| 129 | MTF_EMA_CROSS | ema_cross (1h) | htf_ema_trend (4h), taker_confirm | 1.12 | 153% | 22% |
| 130 | **IMB_SNIPER** | **imbalance_zone** (4h) | taker_confirm, wr_not_extreme | **1.06** | **188%** | **19%** |

> **#130 notes:** New `imbalance_zone` indicator (consecutive-bar near-gap, thr=0.002). Ultra-selective: 0.2/wk, WR=45%, MDD=19%, monthly~3%. 5/5 years positive since 2022.

---

## TRADE STYLE REFERENCE

| Style | TF | Hold | Trades/wk | Key Entries | Key Exits |
|---|---|---|---|---|---|
| **HFT** | 5m / 15m | 1-10 bars (5-50 min) | 20-100 | stoch_rsi, candle_engulfing, wavetrend, bb_reversion | breakeven_trail, tight_atr, rsi_exit |
| **MFT** | 1h | 6-48h | 3-7 | ema_cross, hma_cross, zlema_cross | atr_tp_sl, chandelier_tp, supertrend_trail |
| **Sniper-Swing** | 5m / 15m | 1-4h | 2-15 | fvg_zone_touch, stoch_rsi, ema_cross (LTF) | atr_tp_sl_hold, chandelier_tp |
| **Swing** | 1h / 4h | 1-7 days | <2 | fvg, imbalance_zone, supertrend | chandelier, supertrend_trail |

---

## HOW TO RUN A NEW SEARCH

```bash
source venv/bin/activate

# Generic random search (ETH 4h)
python strategy_forge/scripts/random_search.py --coin ETH --tf 4h --n 200 --score blend

# HFT scalp search (BTC 5m) — dedicated
python strategy_forge/scripts/hft_search.py --coin BTC --tf 5m --n 300 --phase2

# MFT search (ETH 1h)
python strategy_forge/scripts/mtf_search.py --coin ETH --tf 1h --n 200

# Sniper-swing (5m entry, 4h HTF bias)
python strategy_forge/scripts/sniper_swing_search.py --tf 5m --coin BTC --n 300 --phase2

# Genetic evolution (general)
python strategy_forge/scripts/evolve.py --coin ETH --tf 1h --pop 60 --generations 20

# View latest results
python strategy_forge/scripts/report.py --top 5
```

Results land in `strategy_forge/results/`. Review top candidates and manually register the best in `strategy_backtest/settings.py` as the next strategy ID.

---

## KEY RULES & CONSTRAINTS

1. **Filters are direction-agnostic** — `allow=False` blocks BOTH long (+1) and short (-1) signals. Exception: `ema_trend_long` / `ema_trend_short` are named for intent but still block both directions — use together with a bidirectional entry for directional bias only.

2. **All registered ForgeStrategies trade BOTH long and short** — the engine (engine.py:188-192) opens long on `signal==1` and short on `signal==-1`.

3. **MTF filters require DatetimeIndex** — `htf_ema_trend` and `htf_supertrend` call `df.resample()` which fails on integer-indexed data. `load_data()` always returns DatetimeIndex by default.

4. **Fee drag kills low-R:R HFT strategies** — at 3× leverage, round-trip fee ≈ 0.24% equity per trade. At 50 trades/week = 200/month you need PF ≥ 1.5 to survive. HFT requires tight SL + moderate TP (≥ 2:1 R:R) to break even after fees.

5. **Max achievable trade frequency with quality edge on 1h ETH + MTF filter: ~1.5/week** — 3-7/week + MDD<20% + monthly>2% are mutually exclusive on ETH.

6. **Breakeven trail state** — `_be_hit_long`, `_be_hit_short`, `_be_entry` are stored in the `params` dict. They auto-reset when `entry_price` changes (new trade). No cleanup needed in the engine.

7. **`rsi_exit` requires `_rsi` column** — `StrategyDNA.generate_signals()` pre-computes it when `exit_method == 'rsi_exit'`. If exit is mutated to `rsi_exit` post-generation (e.g., genetic crossover), the column may be missing; the exit falls back silently to HOLD.

8. **IMB (Imbalance Zone) vs FVG** — IMB detects consecutive-bar near-gaps (`bar[i].Low >= bar[i-1].High × (1-thr)`). FVG uses a 3-bar gap (`bar[i].Low > bar[i-2].High`). At `thr=0.002` (0.2% tolerance), IMB fires ~same frequency as FVG but slightly more often. At `thr=0.01+`, IMB fires 3-5× more — quality collapses.

---

## CHANGES — 2026-06-23 (session 8)

| Type | What changed |
|---|---|
| **Bug fix** | `dna.py` state persistence: `p = {**self.params}` was created fresh each bar, wiping exit state (`_peak`, `_ttp_active_long`, `_be_hit_long`, etc.). Fixed with `self._exit_state = {}` on the StrategyDNA instance, persisted across bars, cleared on position close. `chandelier_tp`, `breakeven_trail`, and `trailing_tp` were effectively broken before this fix. |
| **Bug fix** | `psar_trail` raw values: `parabolic_sar()` returns ±1 direction, not price levels. SAR stop was `1.0` — exit never triggered → infinite compounding. Fixed with `parabolic_sar_raw()` returning actual SAR price, added to `indicators/trend.py`. |
| **Bug fix** | `psar_trail` stop level: was using current-bar's SAR (which flips above Close after trigger). Fixed with `_psar_prev` (previous bar's SAR = actual stop before flip), using Low-touch trigger pattern matching chandelier exit. |
| **Bug fix** | `_score_candidate` in `alpha_forge_search.py`: called `score_dna(dna, date_from=..., date_to=...)` — wrong kwargs. Fixed to `score, nm = score_dna(dna, df)` with Title Case key access. |
| **Bug fix** | Trend mode in `alpha_forge_search.py`: `c['params']['entry'] = ...` wrote to wrong key; actual entry is `c['entry']`. Fixed. |
| **Bug fix** | Format crash in `alpha_forge_search.py`: `:.3f` applied to string `'N/A'` raises `ValueError`. Fixed with None sentinel. |
| **Bug fix** | `DataFrame.append()` removed in pandas 2.0 — fixed in `processor_Base.py` and `processor_Yahoo.py` with `pd.concat([...])`. |
| **New exit** | `trailing_tp`: phase-1 hard SL, phase-2 trailing below peak once `tp_activation_mult × ATR` profit reached. State: `_ttp_active_long/short`, `_peak`, `_trough`. |
| **New exit** | `psar_trail`: Parabolic SAR trailing stop using `_psar_prev`. Low-touch trigger. Falls back to `atr_tp_sl` on missing data. |
| **New exit** | `vol_adaptive_sl`: volatility-adaptive SL width = `sl_atr_mult × clamp(ATR/ATR_avg, 0.5, 3.0)`. Requires `_atr_avg` pre-computed. |
| **New entries** | `zscore_ema`: z-score of (Close − EMA) mean reversion. Params: `ema_trend`, `zscore_period`, `zscore_threshold`. |
| **New entries** | `zscore_htf`: HTF-level z-score forward-filled to LTF bars for precision timing. Params: `htf_bars`, `zscore_period`, `zscore_threshold`. |
| **New entries** | `funding_rate_mr`: fade extreme funding rate. Loads `{coin}_funding_rate.parquet`. Params: `fr_long_thresh`, `fr_short_thresh`. |
| **New filter** | `funding_rate_bias`: blocks longs when funding ≥ `fr_long_threshold`. Regime gate for funding bubbles. |
| **New indicator** | `parabolic_sar_raw()` in `indicators/trend.py` — returns actual SAR price-level Series via `talib.SAR()`. |
| **New script** | `alpha_forge_search.py`: targeted search applying quad-filter combo to new playstyle exits/entries. 4 modes: trend/reversion/structure/funding. Results to `phase_6_agent_monitor/alpha_forge_v2/dev_report/`. |
| **Enhancement** | `dna.py` `manage_trade()` fully rewritten to use exit state persistence. Also pre-computes `_psar`/`_psar_prev` columns when exit is `psar_trail`. |
| **Phase 12** | Alpha Forge Chatbot built: `phase_12/dashboard/` with streaming SSE, reasoning display, 5 free models, session management in localStorage. API key read from `open_router_API.txt` at runtime (never hardcoded). Backend at `/api/phase_12/chat` in `main_controller/main.py`. |

---

## CHANGES — 2026-06-19 (session 7)

| Type | What changed |
|---|---|
| **Bug fix** | `filter_htf_ema_trend` / `filter_htf_supertrend`: resample rule was `f'{htf_bars}h'`, wrong for sub-1h TFs (5m+htf_bars=48 gave 48h bars). Now uses `_htf_resample_rule()` which auto-derives target duration from DatetimeIndex spacing. |
| **Bug fix** | `mtf_search.py`: was executing at import time (all code at module level). Refactored to proper `main()` + `argparse` CLI. |
| **New exit** | `breakeven_trail`: moves SL to entry once price reaches `be_trigger_mult × ATR`, then trails at `atr_multiplier × ATR` from peak. State auto-resets per trade via `_be_entry` key. |
| **New exit** | `rsi_exit`: exits when RSI crosses back through `rsi_threshold` (default 50) against trade direction. Best for momentum scalps. |
| **New entries** | `candle_engulfing`: bull/bear engulfing bar. `candle_pin_bar`: hammer/shooting star. `order_block`: institutional OB mitigation (uses `order_blocks()` from structure.py). |
| **New params** | `be_trigger_mult (0.3-2.0)`, `ob_lookback (2-10)` added to `DEFAULT_RANGES`. |
| **Enhancement** | `backtest_runner.py`: `score_dna()` now computes `trades_per_week` and `style` label (`hft`/`mft`/`swing`/`position`) and adds them to the returned metrics dict. Verbose print shows `(X/wk) [style]`. |
| **Enhancement** | `random_search.py`: added `--style hft|mft|swing` flag that applies preset defaults (min_trades, leverage, risk, max_filters). |
| **New script** | `hft_search.py`: dedicated HFT/scalp search with curated signal pool, HFT param overrides, `_hft_score()` frequency-weighted scoring, and 3-phase search (random → hand-crafted → genetic). |
| **Enhancement** | All saved results JSONs now include `style`, `trades_per_week` fields in metrics. |
| **Docs** | `strategy_forge_flow.md` updated with all changes, trade style reference table, and updated script usage examples. |

---

## CHANGES — 2026-06-23 (session 10 - Multi-Coin Multi-TF Forge)

| Type | What changed |
|---|---|
| **New filter** | `dual_htf_trend`: checks TWO HTF EMA levels simultaneously (`htf1_bars` + `htf2_bars`). Both must be above their EMAs for a signal to pass. Strongest quality gate in the registry — forces regime alignment at both intermediate and macro TF. |
| **New filter** | `macro_regime`: Supertrend check at the highest HTF (`macro_bars`). Blocks all counter-trend entries during bear markets. Falls back to True on insufficient data. |
| **New params** | `htf1_bars (4–48)`, `htf2_bars (12–288)`, `macro_bars (48–288)` added to `DEFAULT_RANGES` and `_FILTER_PARAMS` in `random_compose.py`. |
| **New script** | `multi_forge_search.py`: full multi-coin (10 cryptos) × multi-TF (5m/15m/1h/4h/1d) strategy discovery. Auto-wires HTF hierarchy per TF, constrains entry/exit pools per style (scalp/swing/daily), runs 3-phase search (random→presets→evolution), scores DNAs across all selected coins simultaneously, re-pins HTF params after each mutation. |
| **11 MTF presets** | Hand-crafted signal combos using `dual_htf_trend` and `macro_regime` filters across all styles — EMA/HMA/ZLEMA cross, BB breakout, FVG, IMB, Elder Ray, CVD, Aroon, Stoch RSI, Williams %R. |
| **Bug fix** | `target_search.py` (created this session): `evolve()` expects `(score, dna)` tuples — was passing bare `StrategyDNA` list. Fixed. Python 3.9 `dict | None` type hint incompatibility fixed. |
| **Bug fix** | `multi_forge_search.py` coin path: dataset uses bare coin names (`ETH`, `BTC`) not `ETHUSDT` — coin symbol stripping logic fixed. |

---

## CHANGES — 2026-06-23 (session 9 - Orderbook & MTF Scaling)

| Type | What changed |
|---|---|
| **Data Integration** | `load_data()` in `run_backtest.py` now automatically merges `order_book_depth.parquet` using a left-join, extracting Level-2 Bid/Ask notional columns without breaking existing data. |
| **New Indicator Math** | Added `calc_orderbook_imbalance()` to `library.py` (calculates Bid / (Bid + Ask) at a specific depth level). |
| **New Indicator Wrapper** | Added `ob_imbalance()` to `strategy_forge/indicators/volume.py` to expose the L2 depth ratio. |
| **New Filters** | Registered `ob_buy_pressure` (requires `ob_imbalance > ob_buy_threshold`) and `ob_sell_pressure` (requires `ob_imbalance < ob_sell_threshold`) to filter trades based on orderbook stacking. |
| **Multi-Coin Engine** | `score_dna()` in `backtest_runner.py` completely rewritten to accept a `Dict[str, pd.DataFrame]`. If multiple coins are passed, it evaluates the DNA on every coin and averages the ROI, Sharpe, MDD, and WR to produce a universally robust cross-market score. |
| **All-Market Search** | `mtf_search.py` now accepts `--coin all`. It dynamically loads all valid crypto parquets from `dataset/` and evaluates strategies across the entire market simultaneously. |
| **MTF Scaling Unlock** | Expanded `htf_bars` upper limit in `params/ranges.py` from `8` up to `288`. Allows 5-minute charts to properly reference 1-Day higher timeframe market regimes (`5m × 288 = 1D`). |
