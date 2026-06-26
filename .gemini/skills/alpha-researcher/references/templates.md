# Quant Templates

## Raw Idea Template (Factor Library Candidate Card)

> Canonical source: `factor_library/templates/Factor_Card_Template.md`
> Always use that file as the actual template. The block below is the reference spec.

```markdown
---
name: strategy-name
strategy_id: TBD
type: short-term | long-term
factor_class: Momentum | Mean-Reversion | Volatility-Breakout | Stat-Arb | Funding-Rate | Sentiment
directional_bias: Symmetric | Long-Biased | Short-Biased
optimal_regime: Trend | Ranging | High-Vol | Low-Vol | Any
timeframes: 1h, 4h
coins: BTC, ETH
source: TradingView / X (@handle) / GitHub (repo) / blog (URL)
interest: High | Medium | Low
status: QUEUED
sharpe: 0.0
win_rate: 0.0
total_return: 0.0
tags: [alpha, factor, {{category}}]
---

# Strategy Name

## Concept
What market inefficiency does this exploit, and WHY does it exist in crypto?
Be specific about the behavioural or structural cause.

## Market Regime
- **Works best in**: e.g., Ranging / Low-Vol / Post-liquidation
- **Breaks down in**: e.g., Strong trend / News gaps / Low-liquidity hours
- **Suggested regime filter**: e.g., ADX(14) < 25, or NONE

## Entry Logic
- **Long**: Exact trigger — every indicator named with its parameter and condition
- **Short**: Exact trigger

## Exit Logic
- **Take Profit**: e.g., "Z-score returns to 0" or "1.5× ATR"
- **Stop Loss**: e.g., "1.0× ATR below entry" or "fixed 2%"
- **Default R:R**: e.g., 3:1

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute indicators
z   = (close - rolling_mean(close, 20)) / rolling_std(close, 20)
atr = ATR(high, low, close, 14)

# Step 2 — Entry signals
long_signal  = (z < -3.0) AND (close > close[-1])
short_signal = (z > +3.0) AND (close < close[-1])

# Step 3 — Exit
tp = entry_price + 3.0 * atr
sl = entry_price - 1.0 * atr
```

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| Z-Score | period=20 | inline |
| ATR | period=14 | `calc_atr(df, 14)` |

## Recommended Logic Switches (For @alpha-developer)
- `entry_filter`: ['NONE', 'ADX_BELOW_25', 'VOL_SPIKE']
- `exit_mode`: ['FIXED_TP', 'TRAILING_STOP', 'INDICATOR_CROSS']

## Data Requirements

### Available Binance Columns (use directly)
| Column | Used For |
|---|---|
| `Close`, `High`, `Low`, `Open` | Price action, ATR, indicators |
| `Volume` | Volume filter |
| `taker_buy_base_vol` | Taker flow, CVD proxy |
| `num_trades` | Trade intensity filter |
| `funding_rate` | Funding arb only (4h parquet) |

### Data Engineer Request
> Fill in ONLY if new data is needed beyond the columns above.
```
NEED: <column>  |  Source: Binance <endpoint>  |  Timeframe: <tf>  |  Coins: <coins>
```

## Implementation
- Minimum timeframe: 1h
- Minimum history: 1 year
- Library function: `strategy_backtest/library.py` → `function_name`

## Observations & Wisdom
-
```

## Implementation Metadata Block (`02_implemented/`)
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

## Known Issues / Deviations from Raw Idea
- List any differences between the raw idea and what was actually coded.

## Next Iteration Ideas
- Improvements, new coins to register, filters to add.
```

## Flexible Strategy Pattern (with Logic Switches)
Use this pattern to follow the **Architect Rule**. Build strategies with built-in categorical choices.

```python
class MyFlexibleStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({'ema_period', 'exit_mode'})

    # TUNEABLE RANGES: Dictate what the Tuner Agent tests
    OPTIMIZATION_RANGES = {
        'exit_mode': ['FIXED_TP', 'TRAILING_STOP'], # Categorical Switch
        'ema_period': (10, 200)                      # Numeric Range
    }

    def __init__(self, df, ema_period=20, exit_mode='FIXED_TP', **kwargs):
        super().__init__(df, **kwargs)
        self.ema_period = ema_period
        self.exit_mode  = exit_mode

    def manage_trade(self, row, position, entry_price, wallet=0):
        # ── Logic Switch Application ───────────────────────────────────────
        if self.exit_mode == 'FIXED_TP':
            # Logic for fixed take profit...
        elif self.exit_mode == 'TRAILING_STOP':
            # Logic for ATR trailing stop...
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
