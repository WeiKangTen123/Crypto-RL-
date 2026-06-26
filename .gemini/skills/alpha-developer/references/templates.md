# Alpha Developer Templates

## Candidate Card Reference (read-only — written by @alpha-researcher)
Candidate Cards live in `factor_library/{FactorClass}/`. You do NOT create them — read them.

Key fields to extract before coding (Stage 1 — INGEST):
| Field | Where | How you use it |
|---|---|---|
| `coins` | YAML | Primary coin = first listed. Cross-asset = remaining coins. |
| `timeframes` | YAML | Primary tf = first listed. Cross-asset checks use same tf. |
| `factor_class` | YAML | Informs regime filter choices |
| `directional_bias` | YAML | Symmetric/Long-Biased/Short-Biased — affects SL/TP logic |
| `optimal_regime` | YAML | Trend/Ranging/High-Vol/Low-Vol — informs entry filter switch |
| `Minimum history` | Body | Sets `date_from` in Stage 5 (see Timeframe Config Table below) |
| `Signal Logic (Pseudocode)` | Body section | Translate step-by-step into `generate_signals()` / `manage_trade()` |
| `Key Indicators & Default Parameters` | Body table | Use as starting `__init__` params and `OPTIMIZATION_RANGES` base |
| `Recommended Logic Switches` | Body section | Implement EVERY listed switch in `OPTIMIZATION_RANGES` |
| `Data Engineer Request` | Body section | If any `NEED:` lines present → card is BLOCKED; wait for data before building |

## Timeframe Config Table (Stage 5 — DEV_REPORT)

`date_to` is always `2026-05-31` (data cutoff). Choose `date_from` by primary timeframe, or use the card's `Minimum history` if it requires more data:

| Primary TF | date_from | Approx candles | Notes |
|---|---|---|---|
| `5m` | `2025-05-31` | ~105k | 1 year; 5m has enough density |
| `15m` | `2024-05-31` | ~70k | 2 years |
| `1h` | `2023-05-31` | ~26k | 3 years standard |
| `4h` | `2023-05-31` | ~6.5k | 3 years minimum for WFO windows |
| `1d` | `2022-05-31` | ~1.4k | 4 years; daily needs more years for significance |

Cross-asset checks: use the **same timeframe** as the primary, on the other coins in the card's `coins` list.
Example: card says `coins: BTC, ETH, SOL`, primary tf `15m` → run baseline on BTC/15m, cross-check ETH/15m + SOL/15m.

After build (Stage 8 — MANIFEST), append to the card:
- **Implementation Metadata Block** (template below)
- **Observations & Wisdom** — 1–2 bullets on what worked and what to watch out for

## Implementation Metadata Block (append to Candidate Card after build)
```markdown
---

## Implementation Status: IMPLEMENTED

## Strategy Class
`ClassName` — `strategy_backtest/strategies/file_name.py`

## Strategy ID(s) in settings.py
`{id}` — `{STRATEGY_ID_STRING}`

## Registered Coins / Timeframes
- COIN / TF — Sharpe: x | Return: x%

## Best Performing Coin
{COIN} — Sharpe: {x} | Return: {x}% | Max DD: {x}%

## Optimizer Results
Best params: {param: value, ...} — from optimize_{name}/results.csv

## WFO Results
Window 1: Sharpe {x} | Window 2: Sharpe {x} | Window 3: Sharpe {x} | Window 4: Sharpe {x}
Pass/Fail: VALIDATED

## Implementation Date
{YYYY-MM-DD}

## First Backtest Result
Sharpe: {x} | Total Return: {x}% | Max DD: {x}% | Trades: {n}

## Known Issues / Deviations from Candidate Card
- List any differences between the Candidate Card design and the actual code.

## Next Iteration Ideas
- Improvements, new coins to register, filters to add.
```

## BaseStrategy Contract

BaseStrategy (`strategy_backtest/base_strategy.py`) enforces these rules — know them before coding:

| Rule | Detail |
|---|---|
| **Auto-kwargs** | `super().__init__(df, **kwargs)` calls `setattr(self, k, v)` for every kwarg. Only put params in `__init__` that need explicit type-casting (`int()`, `float()`). Everything else is assigned automatically. |
| **`SIGNAL_PARAMS`** | `SIGNAL_PARAMS = frozenset({'param_a', 'param_b'})` — params that affect signal generation. The optimizer uses this to decide when signals must be regenerated vs. reused. Params NOT in SIGNAL_PARAMS are treated as risk-only (SL/TP multipliers, RR ratios). |
| **`generate_signals()`** | MUST assign `self.df = df` (with the signal column) before returning. Some engine paths read `self.df` directly. Return the same `df` object. |
| **`validate_params()`** | Override as `@classmethod` to enforce constraints: `if params['fast'] >= params['slow']: return False`. Returning False skips that combo during WFO/optimization. Default returns True (accepts everything). |
| **Regime filtering** | There is NO `check_regime()` method in BaseStrategy. Implement regime guards inline in `generate_signals()` as boolean mask columns. `check_regime()` is NOT an abstract method — do not define it as an override. |
| **`VALID_ACTIONS`** | BaseStrategy defines `VALID_ACTIONS = frozenset({'SL','TP','REVERSE','EXIT','HOLD','SKIP'})` — but the ENGINE also recognizes `'TS'` and `'ADD'`. Always use the 8 engine-recognized strings from the table below. |

## Library.py Indicator Inventory

Available functions in `strategy_backtest/library.py` — import, do not reimplement:

| Category | Functions |
|---|---|
| **Trend** | `calc_ema`, `calc_ema_ribbon`, `calc_supertrend`, `calc_ichimoku`, `calc_zlema`, `calc_t3`, `calc_zero_lag_macd` |
| **Momentum** | `calc_macd`, `calc_rsi`, `calc_stoch_kdj`, `calc_kdj`, `calc_wavetrend`, `calc_tsi`, `calc_mfi`, `calc_vrsi`, `calc_cci`, `calc_aroon`, `calc_fisher_transform` |
| **Volatility** | `calc_atr`, `calc_bollinger_bands`, `calc_keltner_channels`, `calc_bb_kc_squeeze` |
| **Volume** | `calc_vwap`, `calc_vwma`, `calc_cvd`, `calc_taker_intensity` |
| **Breadth/Structure** | `calc_adx_dmi`, `calc_choppiness_index`, `calc_donchian_channels`, `calc_zscore`, `calc_vwap_zscore`, `calc_basis_z_score` |
| **Patterns** | `detect_fvg`, `detect_swing_high_low`, `detect_divergence`, `detect_candle_engulfing`, `detect_candle_hammer`, `detect_order_blocks` |
| **ML** | `calc_lorentzian_classification` |
| **Utils** | `ts_corr`, `ts_min`, `S_log1p`, `window_any_true` |

Always run `grep "^def " strategy_backtest/library.py` for the definitive up-to-date list.

## Flexible Strategy Pattern (with Logic Switches)
Follow the **Architect Rule**: every strategy MUST include 2–3 Logic Switches in `OPTIMIZATION_RANGES`.

### Engine-Recognized Return Actions (manage_trade)
The backtest engine ONLY closes a position when `manage_trade` returns one of these exact strings:

| Action | Meaning | Use when |
|---|---|---|
| `'SL'` | Stop-loss hit | Price crossed hard stop |
| `'TP'` | Take-profit hit | Price reached fixed target |
| `'TS'` | Trailing stop hit | ATR trail triggered |
| `'EXIT'` | Signal-based exit | Indicator reversal / signal flip |
| `'REVERSE'` | Close + flip side | Signal changed to opposite |
| `'HOLD'` | Keep position open | No exit condition met |
| `'SKIP'` | Skip entry this bar | Used in open-position check |
| `'ADD'` | Add to position | Pyramid / layering |

Any other string (e.g. `'TRAIL_STOP'`, `'FIXED_TP'`, `'CLOSE'`) is silently ignored — the position stays open forever. Always use the exact strings above.

### State Reset Pattern for `_s` Dict
The `_s` dict persists across multiple trades. Without a reset, the second trade of the same direction inherits the first trade's SL/TP/TS levels. **Always track `entry_price` to detect new trades:**

```python
class MyFlexibleStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({'atr_period', 'tp_rr', 'sl_atr_mult', 'exit_mode'})

    OPTIMIZATION_RANGES = {
        'exit_mode':   ['FIXED_RR', 'TRAILING_STOP'],  # ← use FIXED_RR, not FIXED_TP
        'tp_rr':       (1.5, 5.0),
        'sl_atr_mult': (0.5, 3.0),
    }

    def __init__(self, df, atr_period=14, tp_rr=3.0, sl_atr_mult=1.5,
                 exit_mode='FIXED_RR', **kwargs):
        super().__init__(df, **kwargs)
        self.atr_period   = atr_period
        self.tp_rr        = tp_rr
        self.sl_atr_mult  = sl_atr_mult
        self.exit_mode    = exit_mode
        # State dict — track entry_price to detect new trades and reset targets
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }

    def manage_trade(self, row, position, entry_price, wallet=0):
        if position == 0:
            return 'HOLD', None
        side = int(np.sign(position))
        s    = self._s[side]
        atr  = float(row['atr'])

        # ── Reset state when a NEW trade starts (entry_price changed) ──────
        if s['entry_price'] != entry_price:
            sl = entry_price - side * (self.sl_atr_mult * atr)
            tp = entry_price + side * (abs(entry_price - sl) * self.tp_rr)
            s.update(entry_price=entry_price, sl_price=sl, tp_price=tp, ts_price=sl)

        # ── Hard stop-loss (always check first) ─────────────────────────────
        if (side ==  1 and row['Low']  <= s['sl_price']) or \
           (side == -1 and row['High'] >= s['sl_price']):
            return 'SL', s['sl_price']

        # ── Exit mode switch ────────────────────────────────────────────────
        if self.exit_mode == 'FIXED_RR':
            if (side ==  1 and row['High'] >= s['tp_price']) or \
               (side == -1 and row['Low']  <= s['tp_price']):
                return 'TP', s['tp_price']
        else:  # TRAILING_STOP
            if side == 1:
                s['ts_price'] = max(s['ts_price'], float(row['Close']) - self.sl_atr_mult * atr)
                if row['Low'] <= s['ts_price']:
                    return 'TS', s['ts_price']   # ← 'TS' is recognized by the engine
            else:
                s['ts_price'] = min(s['ts_price'], float(row['Close']) + self.sl_atr_mult * atr)
                if row['High'] >= s['ts_price']:
                    return 'TS', s['ts_price']

        return 'HOLD', None
```

### validate_params Pattern (optimizer constraint enforcement)
```python
@classmethod
def validate_params(cls, params):
    # Reject combos where fast period >= slow period
    if params.get('fast_period', 0) >= params.get('slow_period', 1):
        return False
    return True
```

### Signal Sanity Check (run BEFORE Stage 4 SMOKE)
Before running the backtest engine, verify your signal conditions are actually achievable in the data. A condition can be logically valid but mathematically impossible on real price data.

```python
# Quick check — run this after generate_signals() before the full backtest:
out = strategy.generate_signals()
longs  = (out['signal'] ==  1).sum()
shorts = (out['signal'] == -1).sum()
print(f"Long signals: {longs}, Short signals: {shorts}")
# If both are 0 → your condition is impossible. Common causes:
#   - AND-chaining two conditions that can't be true simultaneously
#     e.g. (z_score < -3) AND (Close > Close.shift(1)):
#     when z < -3 (price in freefall), Close is almost always FALLING, not rising.
#     Fix: use a CROSSOVER — enter when z_score recovers FROM the extreme:
#     (z_score.shift(1) < -3) & (z_score >= -3)
#   - Threshold too extreme for the data range (check indicator.min() / .max())
#   - NaN propagation: rolling window not dropping NaN rows before signal logic
```

## Optimizer Script Pattern (`strategy_backtest/optimizer/`)
```python
import strategy_backtest.settings as settings
from strategy_backtest.optimizer.optimizer import StrategyOptimizer

settings.ACTIVE_STRATEGY = "{id}"

# Load data (same as run_backtest)
df = load_data(settings.STRATEGY_LIBRARY[settings.ACTIVE_STRATEGY])

param_grid = {
    # strategy params — vary ±30% from defaults
    "fast_period": [8, 12, 16],
    "slow_period": [20, 26, 30],
    # risk params — auto-routed to RiskManager
    "stop_loss_pct": [0.01, 0.02, 0.03],
    "take_profit_pct": [0.03, 0.04, 0.06],
}

results = StrategyOptimizer(df).optimize(
    param_grid=param_grid,
    objective="Sharpe Ratio",
    min_trades=10,
    top_n=10,
    output_csv=f"strategy_backtest/optimizer/optimize_{name}/results.csv"
)
print(results.head(10))
```
