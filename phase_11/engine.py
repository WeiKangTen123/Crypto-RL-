"""
Phase 11 — Anti-Correlation Crossover / Momentum Rotation Strategy

Signal: Rolling relative-performance spread  S[i] = ret_A(N) - ret_B(N)
        where ret_X(N) = P_X[i] / P_X[i-N] - 1  (N-bar return)

Entry:  S crosses zero after prior divergence ≥ MIN_DIVERGENCE for ≥ MIN_PEAK_BARS.
        Short the previous outperformer, Long the previous underperformer.
        (The user's description: "when one is uptrend, another is downtrend — enter at the cross")

Exit:   |S_trade| ≥ PROFIT_TARGET  →  profit
        S_trade past RECROSS_BUFFER in wrong direction  →  stop (false cross)
        S_trade past HARD_STOP_PCT  →  emergency stop
        hold_bars ≥ MAX_HOLD_BARS  →  time stop

S_trade = (P_A[i]/P_A[entry] - 1) - (P_B[i]/P_B[entry] - 1): measures A vs B perf since entry.
This is directly proportional to dollar P&L, making exit thresholds intuitive.
"""

import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

COINS = ['BTC', 'SOL', 'XRP', 'BNB', 'AVAX', 'ADA', 'DOT', 'LINK']

# Explicitly selected golden pairs — all profitable, sorted by Sharpe
PAIRS = [
    ('BTC',  'DOT'),   # +31.48%  Sharpe 1.076
    ('SOL',  'AVAX'),  # +20.10%  Sharpe 0.529
    ('XRP',  'DOT'),   # +18.21%  Sharpe 0.547
    ('BNB',  'XRP'),   # +16.47%  Sharpe 0.645
    ('SOL',  'XRP'),   # +16.37%  Sharpe 0.353
    ('BTC',  'LINK'),  # +15.84%  Sharpe 0.584
    ('BNB',  'SOL'),   # +12.44%  Sharpe 0.405
    ('AVAX', 'ADA'),   # +12.23%  Sharpe 0.348
    ('BNB',  'DOT'),   # +11.85%  Sharpe 0.401
    ('BNB',  'ADA'),   # +11.34%  Sharpe 0.378
]

DATE_FROM = '2021-01-01'
DATE_TO   = '2026-05-31'
TIMEFRAME = '15m'
TIMEFRAME_MINUTES = {
    '1d': 1440, '4h': 240, '1h': 60, '30m': 30, '15m': 15, '5m': 5, '1m': 1,
}

# ── Entry signal — all bar-count values are in HOURS; engine scales to bars ────
NORM_WINDOW       = 48    # 2-day rolling relative-performance window (intraday cycles)
PRIOR_DIV_WINDOW  = 24    # 1-day look-back to verify prior divergence
SHORT_WINDOW      = 12    # 12h short-term momentum window
MIN_PEAK_BARS     = 4     # minimum 4h of divergence above threshold

MIN_DIVERGENCE    = 0.08   # minimum |S| peak in prior window (8% gap in 2-day returns)
CONFIRM_MOMENTUM  = False  # disabled — short window noise at 15m hurts more than helps
ENTRY_CONFIRM_BARS = 0     # hours AFTER zero-cross to wait before entering (0 = immediate)

# ── Exit parameters ───────────────────────────────────────────────────────────
PROFIT_TARGET    = 0.10   # exit when |S_trade| ≥ 10%
RECROSS_BUFFER   = 0.03   # stop when S_trade ≥ 3% wrong direction
HARD_STOP_PCT    = 0.15   # emergency stop at 15%
MAX_HOLD_BARS    = 24     # 24h time stop
COOLDOWN_BARS    = 0.5    # 30min cooldown after profit/time exits (0 after recross)

# ── Capital ───────────────────────────────────────────────────────────────────
CAPITAL_PER_LEG  = 1000   # USD per leg
LEVERAGE         = 3.0    # Position multiplier applied to capital
TRADING_FEE      = 0.0005 # 0.05% per side (4 fees round trip), per leg per side

WARMUP_BARS = NORM_WINDOW + PRIOR_DIV_WINDOW  # default 1h


def _get_scaled_params(timeframe):
    """Scale bar-count params proportionally to timeframe. All hour-based constants × bph → bars."""
    bph = 60.0 / TIMEFRAME_MINUTES.get(timeframe, 60)   # bars per hour
    return dict(
        norm_window        = int(round(NORM_WINDOW      * bph)),
        prior_div_window   = int(round(PRIOR_DIV_WINDOW * bph)),
        short_window       = int(round(SHORT_WINDOW     * bph)),
        min_peak_bars      = int(round(MIN_PEAK_BARS    * bph)),
        max_hold_bars      = int(round(MAX_HOLD_BARS    * bph)),
        recross_buffer     = RECROSS_BUFFER,
        cooldown_bars      = max(1, int(round(COOLDOWN_BARS * bph))),
        min_divergence     = MIN_DIVERGENCE,
        confirm_momentum   = CONFIRM_MOMENTUM,
        entry_confirm_bars = ENTRY_CONFIRM_BARS,
        profit_target      = PROFIT_TARGET,
        hard_stop_pct      = HARD_STOP_PCT,
        capital_per_leg    = CAPITAL_PER_LEG,
        leverage           = LEVERAGE,
        trading_fee        = TRADING_FEE,
        bars_per_hour      = bph,
    )


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_ohlcv(coin, dataset_dir, date_from, date_to, timeframe):
    path = os.path.join(dataset_dir, coin, timeframe, 'spot_ohlcv.parquet')
    df = pd.read_parquet(path)
    df['open_time'] = pd.to_datetime(df['open_time'])
    mask = (df['open_time'] >= date_from) & (df['open_time'] <= date_to)
    return df[mask].sort_values('open_time').reset_index(drop=True)


def load_pair_data(coin_a, coin_b, dataset_dir, date_from, date_to, timeframe):
    """Return (price_a, price_b, times) numpy arrays aligned on open_time."""
    df_a = _load_ohlcv(coin_a, dataset_dir, date_from, date_to, timeframe)
    df_b = _load_ohlcv(coin_b, dataset_dir, date_from, date_to, timeframe)
    df = pd.merge(
        df_a[['open_time', 'close']].rename(columns={'close': 'close_a'}),
        df_b[['open_time', 'close']].rename(columns={'close': 'close_b'}),
        on='open_time', how='inner',
    ).sort_values('open_time').reset_index(drop=True)
    return (
        df['close_a'].values.astype(float),
        df['close_b'].values.astype(float),
        df['open_time'].values,
    )


# ── Signal computation ────────────────────────────────────────────────────────

def compute_relative_spread(price_a, price_b, window):
    """
    S[i] = (P_A[i]/P_A[i-window] - 1) - (P_B[i]/P_B[i-window] - 1)
    Positive  → A outperformed B over the past `window` bars.
    """
    n = len(price_a)
    spread = np.full(n, np.nan)
    spread[window:] = (price_a[window:] / price_a[:n - window] - 1.0) - \
                      (price_b[window:] / price_b[:n - window] - 1.0)
    return spread


def compute_rolling_correlation(price_a, price_b, window):
    """Rolling Pearson correlation of log returns (for dashboard reporting)."""
    ret_a = pd.Series(np.diff(np.log(price_a), prepend=np.nan))
    ret_b = pd.Series(np.diff(np.log(price_b), prepend=np.nan))
    return ret_a.rolling(window).corr(ret_b).values


# ── Metrics helpers ───────────────────────────────────────────────────────────

def _params_dict(p):
    return {
        'norm_window':       p['norm_window'],
        'prior_div_window':  p['prior_div_window'],
        'short_window':      p['short_window'],
        'min_divergence':    p['min_divergence'],
        'min_peak_bars':     p['min_peak_bars'],
        'confirm_momentum':  p['confirm_momentum'],
        'entry_confirm_bars':p['entry_confirm_bars'],
        'profit_target':     p['profit_target'],
        'recross_buffer':    p['recross_buffer'],
        'hard_stop_pct':     p['hard_stop_pct'],
        'max_hold_bars':     p['max_hold_bars'],
        'cooldown_bars':     p['cooldown_bars'],
        'capital_per_leg':   p['capital_per_leg'],
        'trading_fee':       p['trading_fee'],
        'bars_per_hour':     p['bars_per_hour'],
    }


def _build_equity_ts(trades, n, idx):
    """Cumulative closed P&L at each bar in idx."""
    pnl_bar = np.zeros(n)
    for t in trades:
        pnl_bar[t['exit_bar']] += t['net_pnl']
    cum = np.cumsum(pnl_bar)
    return [float(cum[i]) for i in idx]


def _empty_result(coin_a, coin_b, date_from, date_to, timeframe, avg_corr, n, times, spread, roll_corr, price_a, price_b, p):
    step = max(1, int(6 * p['bars_per_hour']))
    idx  = list(range(0, n, step))
    return {
        'pair': f'{coin_a}-{coin_b}', 'coin_a': coin_a, 'coin_b': coin_b,
        'engine_version': 'v2',
        'date_from': date_from, 'date_to': date_to, 'timeframe': timeframe,
        'total_trades': 0, 'win_rate': 0.0, 'roi': 0.0, 'gross_roi': 0.0,
        'sharpe': 0.0, 'max_drawdown': 0.0, 'avg_hold_bars': 0.0,
        'avg_hold_hours': 0.0, 'avg_correlation': round(avg_corr, 3),
        'exit_reasons': {}, 'params': _params_dict(p),
        'trades': [], 'equity_curve': [],
        'ts': {
            'times':   [str(times[i]) for i in idx],
            'price_a': [float(price_a[i]) for i in idx],
            'price_b': [float(price_b[i]) for i in idx],
            'spread':  [None if np.isnan(spread[i]) else float(spread[i]) for i in idx],
            'corr':    [None if np.isnan(roll_corr[i]) else float(roll_corr[i]) for i in idx],
            'equity':  [0.0] * len(idx),
            'ret_a':   [None] * len(idx),
            'ret_b':   [None] * len(idx),
        },
    }


# ── Core backtest ─────────────────────────────────────────────────────────────

def run_pair_backtest(coin_a, coin_b, dataset_dir,
                      date_from=DATE_FROM, date_to=DATE_TO,
                      timeframe=TIMEFRAME):
    """Run Phase 11 crossover backtest for one pair. Returns results dict."""

    p    = _get_scaled_params(timeframe)
    bph  = p['bars_per_hour']
    WARMUP = p['norm_window'] + p['prior_div_window']

    # Load & align
    price_a, price_b, times = load_pair_data(
        coin_a, coin_b, dataset_dir, date_from, date_to, timeframe
    )
    n = len(price_a)

    # Signals
    spread       = compute_relative_spread(price_a, price_b, p['norm_window'])
    short_spread = compute_relative_spread(price_a, price_b, p['short_window'])
    roll_corr    = compute_rolling_correlation(price_a, price_b, p['norm_window'])
    avg_corr     = float(np.nanmean(roll_corr))

    if n < WARMUP + 10:
        return _empty_result(coin_a, coin_b, date_from, date_to, timeframe,
                             avg_corr, n, times, spread, roll_corr, price_a, price_b, p)

    # ── Trade simulation ──────────────────────────────────────────────────────
    trades        = []
    equity        = 0.0
    equity_curve  = np.zeros(n)
    in_trade      = False
    trade_side    = 0       # +1 = long A / short B;  -1 = short A / long B
    entry_bar     = -1
    entry_pa      = 0.0
    entry_pb      = 0.0
    cooldown      = 0
    pending_side  = 0       # entry staged for confirmation
    pending_bar   = -1      # bar when the cross was detected

    for i in range(WARMUP, n):
        s    = spread[i]
        prev = spread[i - 1]

        if np.isnan(s) or np.isnan(prev):
            equity_curve[i] = equity
            continue
            
        current_balance = (2 * p['capital_per_leg']) + equity
        if current_balance <= 0:
            equity_curve[i] = equity
            break

        # ── NOT in a trade ────────────────────────────────────────────────────
        if not in_trade:
            equity_curve[i] = equity
            if cooldown > 0:
                cooldown -= 1
                pending_side = 0
                continue

            # ── Check pending entry confirmation ──────────────────────────────
            if pending_side != 0 and p['entry_confirm_bars'] > 0:
                bars_since_cross = i - pending_bar
                if bars_since_cross >= p['entry_confirm_bars']:
                    confirmed = (pending_side == -1 and s < 0.0) or \
                                (pending_side == +1 and s > 0.0)
                    if confirmed:
                        in_trade   = True
                        trade_side = pending_side
                        entry_bar  = i
                        entry_pa   = price_a[i]
                        entry_pb   = price_b[i]
                    pending_side = 0
                continue

            # ── Zero-crossing detection ───────────────────────────────────────
            cross_neg = (prev > 0.0 and s <= 0.0)   # S: +→-  ⟹  Short A, Long B
            cross_pos = (prev < 0.0 and s >= 0.0)   # S: -→+  ⟹  Long A, Short B

            if not (cross_neg or cross_pos):
                continue

            # Prior divergence check
            start    = max(0, i - p['prior_div_window'])
            prior    = spread[start:i]
            prior_ok = prior[~np.isnan(prior)]

            if len(prior_ok) < p['min_peak_bars']:
                continue

            if cross_neg:
                valid_div = (np.max(prior_ok) >= p['min_divergence'] and
                             int(np.sum(prior_ok >= p['min_divergence'])) >= p['min_peak_bars'])
                side = -1
            else:
                valid_div = (np.min(prior_ok) <= -p['min_divergence'] and
                             int(np.sum(prior_ok <= -p['min_divergence'])) >= p['min_peak_bars'])
                side = +1

            if not valid_div:
                continue

            # Momentum confirmation (short-window S must agree with entry direction)
            if p['confirm_momentum']:
                ss = short_spread[i]
                if np.isnan(ss):
                    continue
                if side == -1 and ss >= -0.005:
                    continue
                if side == +1 and ss <= +0.005:
                    continue

            if p['entry_confirm_bars'] > 0:
                pending_side = side
                pending_bar  = i
            else:
                in_trade   = True
                trade_side = side
                entry_bar  = i
                entry_pa   = price_a[i]
                entry_pb   = price_b[i]

        # ── IN a trade ────────────────────────────────────────────────────────
        else:
            hold_bars = i - entry_bar

            ret_a   = price_a[i] / entry_pa - 1.0
            ret_b   = price_b[i] / entry_pb - 1.0
            s_trade = ret_a - ret_b
            
            # Realism: Calculate floating PnL for liquidation check
            current_capital_per_leg = current_balance / 2.0
            size_a_u = (current_capital_per_leg * p.get('leverage', 1.0)) / entry_pa
            size_b_u = (current_capital_per_leg * p.get('leverage', 1.0)) / entry_pb
            
            if trade_side == +1:
                float_pnl_a = size_a_u * (price_a[i] - entry_pa)
                float_pnl_b = size_b_u * (entry_pb - price_b[i])
            else:
                float_pnl_a = size_a_u * (entry_pa - price_a[i])
                float_pnl_b = size_b_u * (price_b[i] - entry_pb)
                
            float_pnl = float_pnl_a + float_pnl_b
            equity_curve[i] = equity + float_pnl
            
            liquidated = (current_balance + float_pnl <= 0)

            if trade_side == +1:   # Long A / Short B
                profit   = s_trade >= p['profit_target']
                recross  = s_trade <= -p['recross_buffer']
                hardstop = s_trade <= -p['hard_stop_pct']
            else:                   # Short A / Long B
                profit   = s_trade <= -p['profit_target']
                recross  = s_trade >= +p['recross_buffer']
                hardstop = s_trade >= +p['hard_stop_pct']

            time_stop = hold_bars >= p['max_hold_bars']

            if not (profit or recross or hardstop or time_stop or liquidated):
                continue

            reason  = ('liquidated' if liquidated else
                       'profit'    if profit   else
                       'hard_stop' if hardstop else
                       'recross'   if recross  else 'time_stop')
            exit_pa = price_a[i]
            exit_pb = price_b[i]
            size_a  = (current_capital_per_leg * p.get('leverage', 1.0)) / entry_pa
            size_b  = (current_capital_per_leg * p.get('leverage', 1.0)) / entry_pb

            if trade_side == +1:
                pnl_a = size_a * (exit_pa - entry_pa)
                pnl_b = size_b * (entry_pb - exit_pb)
            else:
                pnl_a = size_a * (entry_pa - exit_pa)
                pnl_b = size_b * (exit_pb - entry_pb)

            fee       = 2 * (current_capital_per_leg * p.get('leverage', 1.0)) * p['trading_fee'] * 2
            gross_pnl = pnl_a + pnl_b
            net_pnl   = gross_pnl - fee
            equity   += net_pnl

            pk_start   = max(0, entry_bar - p['prior_div_window'])
            pk_slice   = spread[pk_start:entry_bar]
            pk_valid   = pk_slice[~np.isnan(pk_slice)]
            prior_peak = float(np.max(np.abs(pk_valid))) if len(pk_valid) > 0 else 0.0

            trades.append({
                'entry_bar':    entry_bar,
                'exit_bar':     i,
                'entry_time':   str(times[entry_bar]),
                'exit_time':    str(times[i]),
                'hold_bars':    hold_bars,
                'hold_hours':   round(hold_bars / bph, 1),
                'trade_side':   trade_side,
                'direction':    'long_a_short_b' if trade_side == +1 else 'short_a_long_b',
                'entry_pa':     float(entry_pa),
                'entry_pb':     float(entry_pb),
                'exit_pa':      float(exit_pa),
                'exit_pb':      float(exit_pb),
                'pnl_a':        float(pnl_a),
                'pnl_b':        float(pnl_b),
                'gross_pnl':    float(gross_pnl),
                'fee':          float(fee),
                'net_pnl':      float(net_pnl),
                'entry_spread': float(spread[entry_bar]) if not np.isnan(spread[entry_bar]) else 0.0,
                'prior_peak':   prior_peak,
                's_trade_exit': float(s_trade),
                'exit_reason':  reason,
                'equity_after': float(equity),
            })

            in_trade = False
            # On recross stop: the lines already crossed back — re-enter immediately on the next valid crossing.
            # On profit/time stop: apply cooldown before re-entering.
            cooldown = 0 if reason == 'recross' else p['cooldown_bars']

    # ── Compute metrics ───────────────────────────────────────────────────────
    if not trades:
        return _empty_result(coin_a, coin_b, date_from, date_to, timeframe,
                             avg_corr, n, times, spread, roll_corr, price_a, price_b, p)

    total_invested = 2 * p['capital_per_leg']
    net_pnls       = np.array([t['net_pnl'] for t in trades])
    win_rate       = float(np.mean(net_pnls > 0)) * 100
    total_roi      = float(np.sum(net_pnls) / total_invested) * 100
    gross_roi      = float(np.sum([t['gross_pnl'] for t in trades]) / total_invested) * 100
    avg_hold_bars  = float(np.mean([t['hold_bars'] for t in trades]))
    avg_hold_hours = avg_hold_bars / bph

    balance_curve_ts = total_invested + equity_curve
    eq_df = pd.DataFrame({'time': times, 'equity': balance_curve_ts})
    eq_df['time'] = pd.to_datetime(eq_df['time'])
    eq_df.set_index('time', inplace=True)
    daily_eq = eq_df['equity'].resample('1D').last().dropna()
    daily_ret = daily_eq.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    
    if len(daily_ret) > 1 and daily_ret.std() > 0:
        sharpe = round((float(daily_ret.mean()) / float(daily_ret.std())) * np.sqrt(365), 3)
    else:
        sharpe = 0.0

    # True Max Drawdown under compounding
    balance_curve = total_invested + equity_curve
    peak_balance = np.maximum.accumulate(balance_curve)
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        dd_pct = (balance_curve - peak_balance) / peak_balance * 100
    
    # Replace NaNs with 0
    dd_pct = np.nan_to_num(dd_pct)
    max_dd  = float(np.min(dd_pct))

    exit_reasons = {}
    for t in trades:
        exit_reasons[t['exit_reason']] = exit_reasons.get(t['exit_reason'], 0) + 1

    # Individual rolling returns for the phase portrait (ret_A, ret_B separately)
    nw = p['norm_window']
    ret_a_full = np.full(n, np.nan)
    ret_b_full = np.full(n, np.nan)
    ret_a_full[nw:] = price_a[nw:] / price_a[:n - nw] - 1.0
    ret_b_full[nw:] = price_b[nw:] / price_b[:n - nw] - 1.0

    # Store per-trade rolling return values at exact entry/exit bars for marker placement
    for t in trades:
        eb, xb = t['entry_bar'], t['exit_bar']
        ra_e, rb_e = ret_a_full[eb], ret_b_full[eb]
        ra_x, rb_x = ret_a_full[xb], ret_b_full[xb]
        t['entry_ret_a'] = float(ra_e) if not np.isnan(ra_e) else None
        t['entry_ret_b'] = float(rb_e) if not np.isnan(rb_e) else None
        t['exit_ret_a']  = float(ra_x) if not np.isnan(ra_x) else None

    step = max(1, int(6 * bph))   # ~6h resolution regardless of timeframe
    idx  = list(range(0, n, step))
    ts = {
        'times':   [str(times[i]) for i in idx],
        'price_a': [float(price_a[i]) for i in idx],
        'price_b': [float(price_b[i]) for i in idx],
        'spread':  [None if np.isnan(spread[i]) else float(spread[i]) for i in idx],
        'corr':    [None if np.isnan(roll_corr[i]) else float(roll_corr[i]) for i in idx],
        'equity':  _build_equity_ts(trades, n, idx),
        'ret_a':   [None if np.isnan(ret_a_full[i]) else float(ret_a_full[i]) for i in idx],
        'ret_b':   [None if np.isnan(ret_b_full[i]) else float(ret_b_full[i]) for i in idx],
    }

    return {
        'pair':             f'{coin_a}-{coin_b}',
        'coin_a':           coin_a,
        'coin_b':           coin_b,
        'engine_version':   'v2',
        'date_from':        date_from,
        'date_to':          date_to,
        'timeframe':        timeframe,
        'total_trades':     len(trades),
        'win_rate':         round(win_rate, 1),
        'roi':              round(total_roi, 4),
        'gross_roi':        round(gross_roi, 4),
        'sharpe':           round(sharpe, 3),
        'max_drawdown':     round(max_dd, 4),
        'avg_hold_bars':    round(avg_hold_bars, 1),
        'avg_hold_hours':   round(avg_hold_hours, 1),
        'avg_correlation':  round(avg_corr, 3),
        'exit_reasons':     exit_reasons,
        'params':           _params_dict(p),
        'trades':           trades,
        'equity_curve':     [{'bar': t['exit_bar'], 'equity': t['equity_after']} for t in trades],
        'ts':               ts,
    }
