---
coins: BTC
directional_bias: Symmetric
factor_class: Volatility-Breakout
interest: High
max_drawdown: 0.0
name: simulated-volatility-breakout
optimal_regime: High-Vol
sharpe: 0.0
source: Simulated Discovery
status: IMPLEMENTED
strategy_id: TBD
tags:
- alpha
- factor
- Volatility-Breakout
- implemented
timeframes: 1h
total_return: 0.0
type: short-term
win_rate: 0.0
---
# Simulated Volatility Breakout

## Concept
Retail traders panic during high volatility, causing price to break through 20-period bollinger bands with high volume. This factor exploits the momentum of the breakout.

## Agent Reasoning (Chain of Thought)
*Selected based on high volatility regime. Bridges volatility expansion to price momentum.*

## Market Regime
- **Works best in**: e.g., Ranging / Low-Vol / Post-liquidation recovery
- **Breaks down in**: e.g., Strong directional trend / News-driven gaps / Low-liquidity hours (00:00–04:00 UTC)
- **Suggested regime filter**: e.g., ADX(14) < 25, BB Width < 0.03, or NONE

## Entry Logic
- **Long**: Exact trigger — name every indicator and its condition (e.g., "RSI(14) crosses above 30 AND Close > EMA(200) AND current bar is a bullish engulfing")
- **Short**: Exact trigger

## Exit Logic
- **Take Profit**: e.g., "Close crosses EMA(20)" or "Z-score returns to 0" or "1.5× ATR from entry"
- **Stop Loss**: e.g., "1.0× ATR below entry low" or "Z-score extends to ±4.0"
- **Default R:R**: e.g., 3:1  ← developer uses this as baseline TP/SL multipliers

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute indicators
z       = (close - rolling_mean(close, N)) / rolling_std(close, N)
atr     = ATR(high, low, close, 14)
ema_200 = EMA(close, 200)

# Step 2 — Entry signals
long_signal  = (z < -3.0) AND (close > close[-1])   # price recovering
short_signal = (z > +3.0) AND (close < close[-1])   # price rolling over

# Step 3 — Exit
tp_long = entry_price + 3.0 * atr   # Z returns to 0 ≈ 3σ profit
sl_long = entry_price - 1.0 * atr   # Z extends to ±4 ≈ 1σ loss
```
> Developer translates this directly into `manage_trade()` and `generate_signals()`. Keep it precise — no vague phrases like "if price reverses".

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| Z-Score | period=20 | inline or `calc_z_score(df, 20)` |
| ATR | period=14 | `calc_atr(df, 14)` |
| EMA | period=200 | `calc_ema(df, 200)` |

## Recommended Logic Switches (For @alpha-developer)
Must include 2–3 categorical switches in `OPTIMIZATION_RANGES` so the Tuner can explore architectural choices:
- `entry_filter`: ['NONE', 'ADX_BELOW_25', 'VOL_SPIKE'] — controls regime gate
- `exit_mode`: ['FIXED_TP', 'TRAILING_STOP', 'INDICATOR_CROSS'] — controls how trade exits

## Data Requirements

### Available Binance Columns (use directly — already in parquet)
| Column | Parquet Path | Used For |
|---|---|---|
| `Open`, `High`, `Low`, `Close` | `dataset/{COIN}/{TF}/spot_ohlcv.parquet` | Price action, ATR, indicators |
| `Volume` | same | Volume filter |
| `taker_buy_base_vol` | same | Taker flow, CVD proxy (`CVD ≈ 2×taker_buy_base_vol − Volume`) |
| `num_trades` | same | Trade intensity filter |
| `funding_rate` | `dataset/{COIN}/4h/funding_rate.parquet` | Funding arb only — 4h timeframe, all 5 coins |

### Data Engineer Request
> **Fill in ONLY if this strategy needs data NOT listed above.**
> Tag `@crypto-data-engineer` in the handoff message with this block.

```
NEED: <column_name>  |  Source: Binance <endpoint>  |  Timeframe: <1h/4h/…>  |  Coins: <BTC/ETH/…>
```

Examples:
```
NEED: open_interest   |  Source: Binance /fapi/v1/openInterest     |  Timeframe: 1h, 4h  |  Coins: BTC, ETH
NEED: liquidation_vol |  Source: Binance /fapi/v1/forceOrders       |  Timeframe: 1h       |  Coins: BTC, ETH
NEED: long_short_ratio|  Source: Binance /futures/data/globalLongShortAccountRatio  |  Timeframe: 1h  |  Coins: BTC
```

## Implementation
- Minimum timeframe: 1h
- Minimum history: 1 year
- Library function: `strategy_backtest/library.py` → `{{function_name}}`

## Performance Summary
*Auto-updated by `sync_backtest_to_obsidian.py` when `strategy_id` matches.*

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.0 |
| Win Rate | 0.0% |
| Total Return | 0.0% |
| Max Drawdown | 0.0% |

## Observations & Wisdom
- 

## Connections
**Category:** [[{{category}}/_Index]]
**Indicators:** [[_Concepts/ATR]]
**Related Factors:**
