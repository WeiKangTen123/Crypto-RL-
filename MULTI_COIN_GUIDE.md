# Multi-Coin Portfolio & Per-Coin Mode Guide

**Status:** ✅ Implemented (Phase 4, 2026-07-06)

---

## Overview

The backtest engine now supports **two modes** for multi-coin testing:

1. **Portfolio Mode** (default)
   - All coins share one equity book
   - Useful for basket strategies (e.g., BTC + ETH + SOL as a portfolio)
   - Output: 1 verdict covering all coins combined

2. **Per-Coin Mode**
   - Each coin runs in isolated books
   - Useful for testing single-coin strategies across multiple coins
   - Output: N verdicts (one per coin)

---

## Quick Start

### Single-Coin (Backward Compatible)

```python
# Old code still works — nothing changes
from strategy_backtest.run_backtest import run_strategy
from strategy_backtest.settings import STRATEGY_LIBRARY

cfg = STRATEGY_LIBRARY['86']  # Strategy 86 config
result = run_strategy(cfg)    # Single coin (BTC)
print(result['sharpe'])
```

### Multi-Coin Portfolio Mode

```python
# New: Load multiple coins, one equity book
from strategy_backtest.run_backtest import load_data, run_strategy
from strategy_backtest.settings import STRATEGY_LIBRARY
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager
from strategy_backtest.metrics import compute_metrics

# Load multi-coin data
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLSOL']
df = load_data(symbols, '4h', '2023-01-01', '2026-01-01', mode='portfolio')
# Returns: DF with symbol column, bars interleaved by time

# Create strategy with multi-coin state keying
cfg = STRATEGY_LIBRARY['86']
strategy = SID_86_Strategy(df, **cfg['params'])  # Must handle symbol column

# Run engine (one book, all symbols)
rm = RiskManager(frequency='4h')
engine = BacktestEngine(df, strategy, rm, initial_balance=10000)
equity = engine.run()

# Get verdict (portfolio across all 3 symbols)
from strategy_backtest.verdict_engine import VerdictEngine
m = compute_metrics(equity=equity, initial_balance=10000, timestamps=engine.df.index, trades=engine.trades)
engine_v = VerdictEngine(frequency='4h')
verdict = engine_v.check_all(m, equity, engine.trades, engine.df.index, cfg, is_crypto=True)
print(f"Verdict: {verdict['decision']} (Score: {verdict['score']}/100)")
```

### Multi-Coin Per-Coin Mode (Loop)

```python
# Run each symbol separately
symbols = ['BTCUSDT', 'ETHUSDT']
results = {}

for symbol in symbols:
    # Load single symbol (per_coin mode)
    df = load_data(symbol, '4h', '2023-01-01', '2026-01-01', mode='per_coin')

    # Run strategy (no symbol column when single-coin)
    cfg = STRATEGY_LIBRARY['86']
    strategy = SID_86_Strategy(df, **cfg['params'])
    rm = RiskManager(frequency='4h')
    engine = BacktestEngine(df, strategy, rm, initial_balance=10000)
    equity = engine.run()

    # Get verdict per coin
    m = compute_metrics(...)
    v_engine = VerdictEngine(frequency='4h')
    verdict = v_engine.check_all(m, equity, engine.trades, engine.df.index, cfg)

    results[symbol] = {
        'equity': equity,
        'trades': engine.trades,
        'verdict': verdict
    }

# Analyze results per-coin
for symbol, result in results.items():
    print(f"{symbol}: {result['verdict']['decision']} ({result['verdict']['score']}/100)")
```

---

## Strategy Implementation: Symbol Keying

### Single-Coin Strategies (No Changes Needed)

```python
from strategy_backtest.base_strategy import BaseStrategy

class SingleCoinStrategy(BaseStrategy):
    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)
        self._ema = None  # Single EMA for one coin
        self._rsi = None

    def generate_signals(self):
        # ... indicators based on self.df ...
        return self.df
```

### Multi-Coin Portfolio Strategies (Symbol Keying Required)

```python
class MultiCoinPortfolioStrategy(BaseStrategy):
    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)
        # Key state by symbol — not by single values
        self._ema = {}    # {"BTCUSDT": 45000, "ETHUSDT": 2500}
        self._rsi = {}
        self._position = {}

    def generate_signals(self):
        # Need to handle 'symbol' column
        self.df['signal'] = 0

        for symbol in self.df['symbol'].unique():
            mask = self.df['symbol'] == symbol
            symbol_data = self.df[mask]

            # Calculate indicators per-symbol
            # Update dicts with symbol keys
            ema = symbol_data['Close'].ewm(span=20).mean()
            rsi = ... # per-symbol RSI

            # Example: Long if close > EMA
            self.df.loc[mask, 'signal'] = (symbol_data['Close'] > ema).astype(int)

            # Store state per-symbol
            self._ema[symbol] = ema.iloc[-1]
            self._rsi[symbol] = rsi.iloc[-1]

        return self.df

    def manage_trade(self, bar, position, entry_price, wallet):
        # Access state per-symbol
        symbol = bar.symbol  # Available in portfolio mode
        ema = self._ema.get(symbol, bar.close)
        rsi = self._rsi.get(symbol, 50)

        # Exit logic per-symbol
        if rsi < 30:
            return 'TP', None  # Take profit

        return 'HOLD', None
```

---

## Important: Silent Scrambling Risk

⚠️ **CRITICAL:** A single-coin strategy with multi-coin data in portfolio mode will **silently scramble**:

```
Bar 1: BTCUSDT → signal fires → ENTRY on BTCUSDT ✓
Bar 2: ETHUSDT → signal fires → signal interpreted as BTCUSDT ✓
Bar 3: BTCUSDT → exit signal fires → exits ETHUSDT ❌ WRONG!
```

### How to Avoid

**Option 1: Use Per-Coin Mode** (recommended for single-coin strategies)
```python
for symbol in ['BTCUSDT', 'ETHUSDT']:
    df = load_data(symbol, '4h', ...)  # Single symbol
    # Run strategy (no symbol column)
```

**Option 2: Key State by Symbol** (for true multi-coin strategies)
```python
self._ema = {}  # Dict keyed by symbol
# In generate_signals: self._ema[bar.symbol] = value
```

**Option 3: Accept the Warning**
```
[WARN] Multi-coin data loaded in portfolio mode.
       Strategy must key state by symbol (e.g., self._ema[event.symbol])
       Otherwise: entries on BTC, exits on ETH (SCRAMBLE)!
```

---

## Configuration Format

### Old Format (Single-Coin, Still Works)

```python
"86": {
    "id": "STRATEGY_86",
    "desc": "Multi-timeframe mean-reversion",
    "class": "SID_86_Strategy",
    "data": {"coins": "BTCUSDT", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-01-01"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, ...},
}
```

### New Format (Multi-Coin, Portfolio)

```python
"86_portfolio": {
    "id": "STRATEGY_86_PORTFOLIO",
    "desc": "Multi-coin basket: BTC + ETH + SOL",
    "class": "SID_86_Portfolio_Strategy",  # Must handle symbol column
    "data": {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLSOL"],  # NEW: list of symbols
        "timeframes": "4h",
        "date_from": "2023-01-01",
        "date_to": "2026-01-01"
    },
    "mode": "portfolio",  # NEW: explicit mode
    "risk": {"initial_balance": 10000, "risk_per_trade": 0.15, ...},
}
```

### New Format (Multi-Coin, Per-Coin Loop)

```python
"86_eth": {
    "id": "STRATEGY_86_ETH",
    "desc": "Single-coin strategy (ETH)",
    "class": "SID_86_Strategy",  # Standard, no symbol keying
    "data": {"coins": "ETHUSDT", "timeframes": "4h", ...},  # Single string
    "mode": "per_coin",  # Optional; for documentation
    "risk": {...},
}
```

---

## API Reference

### load_data()

```python
def load_data(coins, timeframe: str, date_from: str, date_to: str, mode='portfolio') -> pd.DataFrame:
    """
    Load OHLCV from Crypto-RL dataset.

    Args:
        coins: str or list
            "BTCUSDT"         → Single coin (backward compat)
            ["BTC", "ETH"]    → Multi-coin, returns DF with 'symbol' column

        timeframe: "1m", "5m", "15m", "30m", "1h", "4h", "1d"
        date_from, date_to: ISO date strings
        mode: "portfolio" (default) or "per_coin"

    Returns:
        DataFrame with columns: [Open, High, Low, Close, Volume, funding_rate?, symbol?]
        - symbol column present if multi-coin
        - Rows sorted by time, then symbol (for reproducibility)
    """
```

### BacktestEngine (No API Changes)

```python
engine = BacktestEngine(df, strategy, risk_manager, initial_balance=10000)
equity = engine.run()  # Works for single or multi-coin
```

**Key:** If `df` has a 'symbol' column, strategy receives bars with `bar.symbol` available.

### VerdictEngine (No API Changes)

```python
v_engine = VerdictEngine(frequency='4h')
verdict = v_engine.check_all(
    metrics_dict=...,
    equity_curve=...,
    trades=...,
    timestamps=...,
    cfg=...,
    is_crypto=True
)
# Returns: {"decision": "PASS", "score": 85, "outcomes": [...]}
```

---

## Example: Converting Single-Coin to Multi-Coin

### Before (Single-Coin)

```python
class SID_86_Strategy(BaseStrategy):
    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)
        self._rsi = None
        self._atr = None

    def generate_signals(self):
        close = self.df['Close']
        self._rsi = ta.RSI(close, 14)
        signal = (self._rsi < 30).astype(int)  # Long when RSI oversold
        self.df['signal'] = signal
        return self.df

    def manage_trade(self, bar, position, entry_price, wallet):
        if self._rsi < 20:
            return 'TP', None
        return 'HOLD', None
```

### After (Multi-Coin)

```python
class SID_86_Portfolio_Strategy(BaseStrategy):
    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)
        self._rsi = {}  # Dict: symbol → RSI series
        self._atr = {}

    def generate_signals(self):
        self.df['signal'] = 0

        for symbol in self.df['symbol'].unique():
            mask = self.df['symbol'] == symbol
            close = self.df.loc[mask, 'Close']

            # Calculate per-symbol indicators
            rsi = ta.RSI(close, 14)
            signal = (rsi < 30).astype(int)

            # Assign signals
            self.df.loc[mask, 'signal'] = signal

            # Store state per-symbol
            self._rsi[symbol] = rsi
            self._atr[symbol] = ...

        return self.df

    def manage_trade(self, bar, position, entry_price, wallet):
        symbol = bar.symbol  # NEW: symbol available in portfolio mode
        rsi_val = self._rsi.get(symbol, [50])[-1]

        if rsi_val < 20:
            return 'TP', None

        return 'HOLD', None
```

**Changes:**
1. Change `self._rsi` from single value → dict keyed by symbol
2. Loop over `self.df['symbol'].unique()` in `generate_signals()`
3. Access `bar.symbol` in `manage_trade()` for per-symbol logic

---

## Backward Compatibility

✅ **All existing single-coin strategies work unchanged.**

```python
# Old code: Still works
df = load_data("BTCUSDT", "4h", ...)  # String, not list
engine = BacktestEngine(df, strategy, rm)  # No 'symbol' column
strategy.generate_signals()  # No 'symbol' handling needed
```

---

## Testing Checklist

For each new multi-coin strategy:

- [ ] Load multi-coin data: `df = load_data(["BTC", "ETH"], ...)`
- [ ] Verify `'symbol'` column present in df
- [ ] Strategy keys state by symbol: `self._ema[symbol]`
- [ ] Strategy accesses `bar.symbol` in `manage_trade()`
- [ ] Run backtest in portfolio mode: all coins share equity
- [ ] Check verdict: PASS / PASS_WITH_WARNINGS
- [ ] Test per-coin mode: loop over coins separately
- [ ] Compare portfolio vs per-coin results (should be different if basket effect)

---

## Troubleshooting

### "KeyError: 'symbol' in strategy"

**Problem:** Trying to access `bar.symbol` in single-coin mode

**Solution:** Check if 'symbol' column exists
```python
if hasattr(bar, 'symbol'):
    symbol = bar.symbol
else:
    symbol = 'SINGLE_COIN'
```

### Entries on BTC, exits on ETH

**Problem:** Single-coin strategy in portfolio mode

**Solution 1:** Use per-coin mode
```python
for symbol in ['BTC', 'ETH']:
    df = load_data(symbol, ...)  # Single symbol
```

**Solution 2:** Key state by symbol
```python
self._position = {}  # Dict, not single value
self._position[bar.symbol] = qty
```

### Different results in portfolio vs per-coin

**Expected:** Portfolio (shared equity) will have different results than per-coin (isolated books)

**Why:** Entry/exit prices differ when portfolio equity changes from other coins.

---

## Next Steps

1. ✅ Implement multi-coin loading (DONE)
2. ✅ Implement symbol field in bars (DONE)
3. ✅ Update verdict engine for multi-coin (DONE)
4. ⏳ Create multi-coin example strategies
5. ⏳ Benchmark portfolio vs per-coin modes
6. ⏳ Integrate with live trading (paper trading)

---

**Last Updated:** 2026-07-06  
**Ready to use:** Yes ✅
