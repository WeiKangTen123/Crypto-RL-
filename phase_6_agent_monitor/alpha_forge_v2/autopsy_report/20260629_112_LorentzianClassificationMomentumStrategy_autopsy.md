---
strategy_id: 112
strategy_class: LorentzianClassificationMomentumStrategy
status: ERROR
date: 2026-06-29
failure_stage: SCAN_AUDIT (Stage 2)
error_type: CRASH
error_message: "Can't instantiate abstract class LorentzianClassificationMomentumStrategy with abstract methods populate_buy_trend, populate_sell_trend"
---
## Autopsy Report for Lorentzian Classification Momentum Strategy (ID 112)

**Date of Autopsy:** 2026-06-29

**Strategy ID:** 112
**Strategy Class:** LorentzianClassificationMomentumStrategy
**Failure Stage:** SCAN_AUDIT (Stage 2)

**Parameters:**
- `k_neighbors`: 5
- `history_window`: 2000
- `rsi_period`: 14
- `cci_period`: 14
- `adx_period`: 14
- `ema_period`: 200
- `adx_threshold`: 20
- `entry_filter`: 'ADX_ABOVE_20'
- `exit_mode`: 'ATR_TRAILING_STOP'
- `tp_rr`: 2.0
- `sl_atr_mult`: 1.0

**Reason for Failure:**
The strategy crashed during `scan_all.py` execution due to a class definition error. It cannot be instantiated because it inherits from a base strategy class (likely Freqtrade's `IStrategy`) but lacks concrete implementations of abstract methods `populate_buy_trend` and `populate_sell_trend`.

**Root Cause Diagnosis:**
The strategy implementation file is incomplete or utilizes an incorrect class structure. The backtesting framework expects `populate_buy_trend` and `populate_sell_trend` to be defined for signal generation, but they are missing or abstract in the `LorentzianClassificationMomentumStrategy` class definition.

**Recommendation:**
Send a `FACTOR_FAILURE_REPORT` to `@alpha-researcher`. The researcher must fix the class structure of `LorentzianClassificationMomentumStrategy` to implement all required abstract methods before this strategy can be scanned or tuned.
