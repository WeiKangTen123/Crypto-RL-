"""
exit_signals.py — registry of exit methods.

Each exit function is called inside manage_trade() and returns
(action, exec_price) matching BacktestEngine's contract:
  action : 'TP' | 'SL' | 'EXIT' | 'HOLD'
  exec_price : float | None
"""
import pandas as pd

from strategy_forge.indicators import atr, rsi, supertrend


def _sl_first(row, position: float) -> bool:
    """Return True when SL should be checked before TP on this bar.

    Bearish candle (Close < Open) for a long → Low was likely hit before High
    → SL check first.  The opposite applies for shorts.
    This prevents TP always winning when both levels are inside the bar's range.
    """
    if position > 0:
        return float(row['Close']) < float(row['Open'])
    else:
        return float(row['Close']) > float(row['Open'])


def exit_atr_tp_sl(row, position, entry_price, params, df_slice=None):
    """ATR-based take-profit and stop-loss."""
    try:
        atr_val = row['_atr']
    except Exception:
        atr_val = row['Close'] * 0.02
    tp_mult = params.get('tp_atr_mult', 3.0)
    sl_mult = params.get('sl_atr_mult', 1.0)
    if position > 0:
        tp_px, sl_px = entry_price + tp_mult * atr_val, entry_price - sl_mult * atr_val
        tp_hit = row['High'] >= tp_px
        sl_hit = row['Low']  <= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    elif position < 0:
        tp_px, sl_px = entry_price - tp_mult * atr_val, entry_price + sl_mult * atr_val
        tp_hit = row['Low']  <= tp_px
        sl_hit = row['High'] >= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    return 'HOLD', None


def exit_pct_tp_sl(row, position, entry_price, params, df_slice=None):
    """Fixed percentage take-profit and stop-loss."""
    tp = params.get('tp_pct', 0.05)
    sl = params.get('sl_pct', 0.02)
    if position > 0:
        tp_px, sl_px = entry_price * (1 + tp), entry_price * (1 - sl)
        tp_hit = row['High'] >= tp_px
        sl_hit = row['Low']  <= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    elif position < 0:
        tp_px, sl_px = entry_price * (1 - tp), entry_price * (1 + sl)
        tp_hit = row['Low']  <= tp_px
        sl_hit = row['High'] >= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    return 'HOLD', None


def exit_rr_ratio(row, position, entry_price, params, df_slice=None):
    """Risk-Reward ratio exit — SL fixed pct, TP = SL × RR."""
    sl_pct = params.get('sl_pct', 0.02)
    rr     = params.get('tp_rr', 2.0)
    tp_pct = sl_pct * rr
    if position > 0:
        tp_px, sl_px = entry_price * (1 + tp_pct), entry_price * (1 - sl_pct)
        tp_hit = row['High'] >= tp_px
        sl_hit = row['Low']  <= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    elif position < 0:
        tp_px, sl_px = entry_price * (1 - tp_pct), entry_price * (1 + sl_pct)
        tp_hit = row['Low']  <= tp_px
        sl_hit = row['High'] >= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    return 'HOLD', None


def exit_max_hold(row, position, entry_price, params, df_slice=None):
    """Exit after max_hold_bars bars (tracked via params['_bars_held'])."""
    max_bars = params.get('max_hold_bars', 48)
    bars_held = params.get('_bars_held', 0)
    if bars_held >= max_bars:
        return 'EXIT', None
    return 'HOLD', None


def exit_atr_tp_sl_with_hold(row, position, entry_price, params, df_slice=None):
    """ATR TP/SL + max hold bars combined."""
    action, price = exit_atr_tp_sl(row, position, entry_price, params)
    if action != 'HOLD':
        return action, price
    return exit_max_hold(row, position, entry_price, params)


def exit_chandelier(row, position, entry_price, params, df_slice=None):
    """
    Chandelier Exit — ATR trailing stop from the highest high / lowest low
    since entry. Tracks peak internally via params['_peak'] and '_trough'.
    Significantly cuts MDD vs fixed SL by locking in gains as price moves.

    State is keyed to entry_price so it auto-resets between trades
    (same guard pattern as breakeven_trail / trailing_tp).
    """
    try:
        atr_val = row['_atr']
    except Exception:
        atr_val = row['Close'] * 0.02

    mult   = params.get('atr_multiplier', 3.0)
    sl_mult = params.get('sl_atr_mult', mult)   # hard initial SL if provided

    # ── Auto-reset on new trade ─────────────────────────────────────────
    if params.get('_chan_entry') != entry_price:
        params['_chan_entry'] = entry_price
        params.pop('_peak',   None)
        params.pop('_trough', None)

    if position > 0:
        peak = max(params.get('_peak', entry_price), row['High'])
        params['_peak'] = peak
        stop = peak - mult * atr_val
        if row['Low'] <= stop:
            return 'SL', stop
        # Hard initial SL guard (before peak has moved above entry)
        hard_sl = entry_price - sl_mult * atr_val
        if peak <= entry_price and row['Low'] <= hard_sl:
            return 'SL', hard_sl
    elif position < 0:
        trough = min(params.get('_trough', entry_price), row['Low'])
        params['_trough'] = trough
        stop = trough + mult * atr_val
        if row['High'] >= stop:
            return 'SL', stop
        # Hard initial SL guard (before trough has moved below entry)
        hard_sl = entry_price + sl_mult * atr_val
        if trough >= entry_price and row['High'] >= hard_sl:
            return 'SL', hard_sl

    return 'HOLD', None


def exit_chandelier_with_tp(row, position, entry_price, params, df_slice=None):
    """
    Chandelier trailing stop + fixed ATR take-profit ceiling.

    State is keyed to entry_price so it auto-resets between trades.
    TP/SL priority uses candle direction: bearish bar → chandelier SL checked first.
    """
    try:
        atr_val = row['_atr']
    except Exception:
        atr_val = row['Close'] * 0.02

    tp_mult = params.get('tp_atr_mult', 5.0)

    # Compute chandelier SL result first (updates state internally)
    chan_action, chan_price = exit_chandelier(row, position, entry_price, params)

    if position > 0:
        tp_level = entry_price + tp_mult * atr_val
        tp_hit   = row['High'] >= tp_level
        sl_hit   = chan_action != 'HOLD'
        if _sl_first(row, position):
            if sl_hit: return chan_action, chan_price
            if tp_hit:
                params.pop('_chan_entry', None); params.pop('_peak', None)
                return 'TP', tp_level
        else:
            if tp_hit:
                params.pop('_chan_entry', None); params.pop('_peak', None)
                return 'TP', tp_level
            if sl_hit: return chan_action, chan_price
    elif position < 0:
        tp_level = entry_price - tp_mult * atr_val
        tp_hit   = row['Low'] <= tp_level
        sl_hit   = chan_action != 'HOLD'
        if _sl_first(row, position):
            if sl_hit: return chan_action, chan_price
            if tp_hit:
                params.pop('_chan_entry', None); params.pop('_trough', None)
                return 'TP', tp_level
        else:
            if tp_hit:
                params.pop('_chan_entry', None); params.pop('_trough', None)
                return 'TP', tp_level
            if sl_hit: return chan_action, chan_price

    return 'HOLD', None


def exit_supertrend_trail(row, position, entry_price, params, df_slice=None):
    """
    Exit when Supertrend flips direction — acts as a dynamic trailing stop.
    Requires '_st_direction' column pre-computed in generate_signals().
    Falls back to ATR SL if column missing.
    """
    try:
        st_dir = row['_st_direction']
        if position > 0 and st_dir == -1:
            return 'EXIT', None
        if position < 0 and st_dir == 1:
            return 'EXIT', None
        return 'HOLD', None
    except Exception:
        return exit_atr_tp_sl(row, position, entry_price, params)


def exit_tight_atr(row, position, entry_price, params, df_slice=None):
    """
    Tight ATR exit: small SL multiplier (0.5–1.0), large TP multiplier (4–8).
    High R:R forces only high-conviction trades to survive.
    """
    try:
        atr_val = row['_atr']
    except Exception:
        atr_val = row['Close'] * 0.015

    sl_mult = params.get('sl_atr_mult', 0.8)
    tp_mult = params.get('tp_atr_mult', 5.0)

    if position > 0:
        tp_px, sl_px = entry_price + tp_mult * atr_val, entry_price - sl_mult * atr_val
        tp_hit = row['High'] >= tp_px
        sl_hit = row['Low']  <= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    elif position < 0:
        tp_px, sl_px = entry_price - tp_mult * atr_val, entry_price + sl_mult * atr_val
        tp_hit = row['Low']  <= tp_px
        sl_hit = row['High'] >= sl_px
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_px
            if tp_hit: return 'TP', tp_px
        else:
            if tp_hit: return 'TP', tp_px
            if sl_hit: return 'SL', sl_px
    return 'HOLD', None


def exit_breakeven_trail(row, position, entry_price, params, df_slice=None):
    """
    Move SL to breakeven once price reaches be_trigger_mult × ATR in profit direction,
    then trail at atr_multiplier × ATR from the peak/trough.
    Cuts losers fast, lets profitable moves trail further.
    State is keyed to entry_price so it auto-resets between trades.
    """
    try:
        atr_val = row['_atr']
    except Exception:
        atr_val = row['Close'] * 0.02

    sl_mult    = params.get('sl_atr_mult', 1.0)
    be_trig    = params.get('be_trigger_mult', 0.5)
    trail_mult = params.get('atr_multiplier', 2.0)

    # Auto-reset state on new trade (entry_price changes)
    if params.get('_be_entry') != entry_price:
        params['_be_entry']     = entry_price
        params['_be_hit_long']  = False
        params['_be_hit_short'] = False
        params.pop('_peak',    None)
        params.pop('_trough',  None)

    if position > 0:
        if not params['_be_hit_long']:
            if row['High'] >= entry_price + be_trig * atr_val:
                params['_be_hit_long'] = True
                params['_peak'] = max(params.get('_peak', entry_price), row['High'])
            else:
                if row['Low'] <= entry_price - sl_mult * atr_val:
                    return 'SL', entry_price - sl_mult * atr_val
        if params['_be_hit_long']:
            peak = max(params.get('_peak', entry_price), row['High'])
            params['_peak'] = peak
            stop = max(peak - trail_mult * atr_val, entry_price)
            if row['Low'] <= stop:
                return 'SL', stop

    elif position < 0:
        if not params['_be_hit_short']:
            if row['Low'] <= entry_price - be_trig * atr_val:
                params['_be_hit_short'] = True
                params['_trough'] = min(params.get('_trough', entry_price), row['Low'])
            else:
                if row['High'] >= entry_price + sl_mult * atr_val:
                    return 'SL', entry_price + sl_mult * atr_val
        if params['_be_hit_short']:
            trough = min(params.get('_trough', entry_price), row['Low'])
            params['_trough'] = trough
            stop = min(trough + trail_mult * atr_val, entry_price)
            if row['High'] >= stop:
                return 'SL', stop

    return 'HOLD', None


def exit_trailing_tp(row, position, entry_price, params, df_slice=None):
    """
    Trailing Take-Profit (profit ratchet).

    Phase 1 — before activation: fixed SL at sl_atr_mult × ATR.
    Phase 2 — once price reaches tp_activation_mult × ATR in profit direction:
               trail the exit at (peak - tp_trail_mult × ATR) for longs.
               Exit tagged 'TP' — locked-in profit exit, never a loss once active.

    Params
    ------
    tp_activation_mult : ATR multiples price must gain before trailing kicks in (default 1.5)
    tp_trail_mult      : ATR multiples to trail behind the running peak/trough (default 0.8)
    sl_atr_mult        : initial hard stop before activation (default 2.0)
    """
    try:
        atr_val = float(row['_atr'])
    except Exception:
        atr_val = row['Close'] * 0.02

    activation = params.get('tp_activation_mult', 1.5)
    trail_dist  = params.get('tp_trail_mult', 0.8)
    init_sl     = params.get('sl_atr_mult', 2.0)

    # Auto-reset state on new trade
    if params.get('_ttp_entry') != entry_price:
        params['_ttp_entry']        = entry_price
        params['_ttp_active_long']  = False
        params['_ttp_active_short'] = False
        params.pop('_peak',   None)
        params.pop('_trough', None)

    if position > 0:
        if not params['_ttp_active_long']:
            if row['Low'] <= entry_price - init_sl * atr_val:
                return 'SL', entry_price - init_sl * atr_val
            if row['High'] >= entry_price + activation * atr_val:
                params['_ttp_active_long'] = True
                params['_peak'] = row['High']
        if params['_ttp_active_long']:
            peak = max(params.get('_peak', entry_price), row['High'])
            params['_peak'] = peak
            trail_level = peak - trail_dist * atr_val
            if row['Low'] <= trail_level:
                return 'TP', trail_level

    elif position < 0:
        if not params['_ttp_active_short']:
            if row['High'] >= entry_price + init_sl * atr_val:
                return 'SL', entry_price + init_sl * atr_val
            if row['Low'] <= entry_price - activation * atr_val:
                params['_ttp_active_short'] = True
                params['_trough'] = row['Low']
        if params['_ttp_active_short']:
            trough = min(params.get('_trough', entry_price), row['Low'])
            params['_trough'] = trough
            trail_level = trough + trail_dist * atr_val
            if row['High'] >= trail_level:
                return 'TP', trail_level

    return 'HOLD', None


def exit_psar_trail(row, position, entry_price, params, df_slice=None):
    """
    Parabolic SAR trailing exit.

    Uses previous bar's SAR as the trailing stop level (current bar's SAR
    has already flipped direction, so it's no longer the correct stop price).
    Trigger: bar's Low touches the stop level (same logic as chandelier exit).
    Falls back to exit_atr_tp_sl if column is missing.
    """
    try:
        # Previous bar's SAR = the actual trailing stop level
        stop = float(row['_psar_prev'])
        if position > 0 and row['Low'] <= stop:
            return 'EXIT', stop
        if position < 0 and row['High'] >= stop:
            return 'EXIT', stop
        return 'HOLD', None
    except Exception:
        return exit_atr_tp_sl(row, position, entry_price, params)


def exit_vol_adaptive_sl(row, position, entry_price, params, df_slice=None):
    """
    Volatility-Adaptive SL — SL width scales with current volatility regime.

    Effective SL = base_sl_mult × vol_ratio × ATR, where
    vol_ratio = current_ATR / rolling_avg_ATR (clamped 0.5–3.0).

    High-vol conditions → wider SL (avoids spike-outs).
    Low-vol conditions  → tighter SL (locks in gains faster).

    Requires '_atr_avg' column pre-computed in generate_signals().

    Params
    ------
    sl_atr_mult : base SL multiplier before vol adjustment (default 2.0)
    tp_atr_mult : fixed TP in ATR multiples from entry (default 4.0, 0=disabled)
    """
    try:
        atr_val = float(row['_atr'])
        atr_avg = float(row['_atr_avg'])
    except Exception:
        atr_val = row['Close'] * 0.02
        atr_avg = atr_val

    base_sl = params.get('sl_atr_mult', 2.0)
    tp_mult = params.get('tp_atr_mult', 4.0)
    vol_ratio = max(0.5, min(3.0, atr_val / atr_avg if atr_avg > 0 else 1.0))
    adaptive_sl = base_sl * vol_ratio * atr_val

    if position > 0:
        tp_level = entry_price + tp_mult * atr_val
        sl_level = entry_price - adaptive_sl
        tp_hit = tp_mult > 0 and row['High'] >= tp_level
        sl_hit = row['Low'] <= sl_level
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_level
            if tp_hit: return 'TP', tp_level
        else:
            if tp_hit: return 'TP', tp_level
            if sl_hit: return 'SL', sl_level
    elif position < 0:
        tp_level = entry_price - tp_mult * atr_val
        sl_level = entry_price + adaptive_sl
        tp_hit = tp_mult > 0 and row['Low'] <= tp_level
        sl_hit = row['High'] >= sl_level
        if _sl_first(row, position):
            if sl_hit: return 'SL', sl_level
            if tp_hit: return 'TP', tp_level
        else:
            if tp_hit: return 'TP', tp_level
            if sl_hit: return 'SL', sl_level

    return 'HOLD', None


def exit_rsi_exit(row, position, entry_price, params, df_slice=None):
    """
    Exit when RSI crosses back through rsi_threshold (default 50) against trade direction.
    Useful for momentum scalps — exit when momentum reverses, not waiting for SL.
    Requires '_rsi' column pre-computed by StrategyDNA.generate_signals().
    """
    try:
        rsi_val = float(row['_rsi'])
        mid     = params.get('rsi_threshold', 50)
        if position > 0 and rsi_val < mid:
            return 'EXIT', None
        if position < 0 and rsi_val > mid:
            return 'EXIT', None
    except Exception:
        pass
    return 'HOLD', None


# ── Registry ──────────────────────────────────────────────────────────────────

EXIT_REGISTRY = {
    'atr_tp_sl':          exit_atr_tp_sl,
    'pct_tp_sl':          exit_pct_tp_sl,
    'rr_ratio':           exit_rr_ratio,
    'max_hold':           exit_max_hold,
    'atr_tp_sl_hold':     exit_atr_tp_sl_with_hold,
    'chandelier':         exit_chandelier,
    'chandelier_tp':      exit_chandelier_with_tp,
    'supertrend_trail':   exit_supertrend_trail,
    'tight_atr':          exit_tight_atr,
    'breakeven_trail':    exit_breakeven_trail,
    'rsi_exit':           exit_rsi_exit,
    'trailing_tp':        exit_trailing_tp,
    'psar_trail':         exit_psar_trail,
    'vol_adaptive_sl':    exit_vol_adaptive_sl,
}


def compute_exit(name: str, row, position, entry_price, params):
    fn = EXIT_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown exit method: {name}")
    return fn(row, position, entry_price, params)
