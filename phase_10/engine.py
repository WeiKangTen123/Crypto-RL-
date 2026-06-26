"""
Phase 10 — Quantitative Pairs Trading Engine
Implements: OLS hedge ratio, ADF cointegration test, Z-score spread,
dynamic Bollinger Band thresholds, Ornstein-Uhlenbeck half-life,
MFE/MAE excursion tracking, and TCA-aware fee drag (4 legs per round-trip).

Enhancements (v2):
  1. MIN_ENTRY_Z     — hard Z-score floor; prevents BB-collapse entries near zero
  2. COOLDOWN_BARS   — minimum gap between trades; prevents immediate re-entry churn
  3. MIN_HOLD_BARS   — minimum hold before mean-revert exit; avoids micro-churn
  4. Z_STOP_LOSS     — hard Z-score stop; caps losses on trending/diverging spreads
  5. Rolling ADF     — periodic cointegration re-check; detects OOS regime breakdown
  6. MIN_R2          — OLS R² quality gate; rejects weak hedge ratio fits

Enhancements (v3):
  1. CONFIRM_TURN    — enter only after Z-score starts moving back toward mean
  2. ZSTOP_CIRCUIT   — pause pair after consecutive Z_STOP exits
  3. REVERSAL_TRAIL  — trail profits after Z-score crosses through zero
  4. EXIT_ZSCORE=0   — disable noisy mean-revert exits
"""

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from statsmodels.tsa.stattools import adfuller


COINS      = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'LINK', 'AVAX', 'DOT', 'ADA']
PAIRS      = [(a, b) for i, a in enumerate(COINS) for b in COINS[i + 1:]]
DATE_FROM  = '2023-01-01'
DATE_TO    = '2026-05-31'
TIMEFRAME  = '1h'
TIMEFRAME_MINUTES = {
    '1d': 1440,
    '4h': 240,
    '1h': 60,
    '30m': 30,
    '15m': 15,
    '5m': 5,
    '1m': 1,
}

# ── Engine parameters (Pure Z-Score Optimized) ────────────────────────────────
OLS_WINDOW        = 120    # 120 hours at 1h — stable hedge ratio (optimized)
ZSCORE_WINDOW     = 48     # 48 hours at 1h — rolling z-score mean/std (optimized)
BB_WINDOW         = 20     # bars for Bollinger Band on Z-score (visualization only)
BB_STD            = 2.0    # BB multiplier (visualization only)
EXIT_ZSCORE       = 0.0    # close when |z| falls below this; 0 disables noisy MR exits
CAPITAL_PER_LEG   = 1000   # USD margin allocated per individual leg (coin A or B)
LEVERAGE          = 3.0    # Position multiplier applied to capital
TRADING_FEE       = 0.0005 # 0.05% taker fee per leg (4 legs per round-trip)
ADF_PVALUE_MAX    = 0.05   # standard p-value for cointegration

# ── Enhancement parameters (v2 - Pure Z-Score) ────────────────────────────────
MIN_ENTRY_Z       = 2.5    # entry threshold in σ units (optimized)
COOLDOWN_BARS     = 6      # bars to wait after exit
MIN_HOLD_BARS     = 2      # minimum hold to avoid micro-churn
Z_STOP_LOSS       = 3.0    # structural break stop (enforced rule)
ROLLING_ADF_BARS  = 72     # re-run ADF every 3 days
ROLLING_ADF_PVAL  = 0.10   # standard regime check
MIN_R2            = 0.80   # tighter OLS quality gate (optimized)

# ── Enhancement parameters (v3) ───────────────────────────────────────────────
CONFIRM_TURN      = True   # require z to be moving toward mean before entry
ZSTOP_CIRCUIT_BREAKER = 2  # consecutive Z_STOP exits before pausing entries
ZSTOP_PAUSE_BARS  = 360    # pause duration after circuit breaker (~15 days at 1h)
REVERSAL_TRAIL_Z  = 0.5    # trailing stop distance after z crosses zero
MAX_ENTRY_Z       = Z_STOP_LOSS - 0.10  # avoid entries already sitting at stop risk

# ── Crypto-Specific Exit (Funding Rate Bleed) ─────────────────────────────────
NET_FUNDING_RATE_8H = 0.0001  # 0.01% average net funding bleed per 8 hours on the short leg

# ── Kalman Filter hedge ratio (v4) ────────────────────────────────────────────
USE_KALMAN        = False  # Kalman adapts β every bar — absorbs divergence, kills spread signal
KALMAN_DELTA      = 1e-5   # state noise — lower = slower adaptation, more stable β
KALMAN_VE         = 0.001  # observation noise variance

# ── Daily regime gate (v4) ───────────────────────────────────────────────────
DAILY_REGIME_GATE  = True  # block entries when 24h Z-drift signals trending spread
DAILY_Z_DRIFT_BARS = 24    # look-back in signal bars (24h at 1h TF)
DAILY_Z_DRIFT_MAX  = 3.0   # max Z drift in 24h before blocking entry


def timeframe_scale(tf: str) -> int:
    """Scale 1h-tuned bar windows to another timeframe while preserving duration."""
    if tf not in TIMEFRAME_MINUTES:
        raise ValueError(f'Unsupported timeframe: {tf}')
    scale = TIMEFRAME_MINUTES[TIMEFRAME] / TIMEFRAME_MINUTES[tf]
    if scale < 1:
        raise ValueError(f'Timeframe {tf} is slower than base {TIMEFRAME}; use it as signal_tf only.')
    return int(round(scale))


def scaled_params(signal_tf: str, execution_tf: str) -> dict:
    """Return time-equivalent parameters for signal and execution timeframes."""
    signal_scale = timeframe_scale(signal_tf)
    execution_scale = timeframe_scale(execution_tf)
    return {
        'ols_window': OLS_WINDOW * signal_scale,
        'zscore_window': ZSCORE_WINDOW * signal_scale,
        'bb_window': BB_WINDOW * signal_scale,
        'rolling_adf_bars': ROLLING_ADF_BARS * signal_scale,
        'cooldown_bars': COOLDOWN_BARS * execution_scale,
        'min_hold_bars': MIN_HOLD_BARS * execution_scale,
        'daily_drift_bars': DAILY_Z_DRIFT_BARS * execution_scale,
    }


def load_pair_data(dataset_dir, coin_a, coin_b, date_from=DATE_FROM, date_to=DATE_TO, tf=TIMEFRAME):
    """Load and align OHLCV close prices for two coins."""
    def _load(coin):
        import os
        path = os.path.join(dataset_dir, coin, tf, 'spot_ohlcv.parquet')
        df = pd.read_parquet(path)
        col_map = {'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low'}
        df = df.rename(columns=col_map)
        if 'open_time' in df.columns:
            df['open_time'] = pd.to_datetime(df['open_time'])
            df = df.set_index('open_time')
        df = df.sort_index()
        df = df[(df.index >= pd.Timestamp(date_from)) & (df.index <= pd.Timestamp(date_to))]
        return df[['Close']].rename(columns={'Close': coin})

    df_a = _load(coin_a)
    df_b = _load(coin_b)
    merged = df_a.join(df_b, how='inner').dropna()
    return merged


def compute_half_life(spread: np.ndarray) -> float:
    """Ornstein-Uhlenbeck half-life of mean reversion."""
    lag   = spread[:-1]
    delta = np.diff(spread)
    lag   = lag - lag.mean()
    if lag.std() == 0:
        return np.nan
    reg = np.polyfit(lag, delta, 1)
    lam = reg[0]
    if lam >= 0:
        return np.nan
    return -np.log(2) / lam


def compute_rolling_hedge_and_spread(log_a: np.ndarray, log_b: np.ndarray, window: int):
    """
    Rolling OLS: log(P_A) = α + β * log(P_B) + ε
    Returns arrays: beta, alpha, spread (residual ε), r2 (in-window R²)
    """
    n      = len(log_a)
    beta   = np.full(n, np.nan)
    alpha  = np.full(n, np.nan)
    spread = np.full(n, np.nan)
    r2     = np.full(n, np.nan)

    for i in range(window, n):
        la = log_a[i - window:i]
        lb = log_b[i - window:i]
        X  = add_constant(lb)
        try:
            res       = OLS(la, X).fit()
            a, b      = res.params[0], res.params[1]
            alpha[i]  = a
            beta[i]   = b
            spread[i] = log_a[i] - (a + b * log_b[i])
            r2[i]     = res.rsquared
        except Exception:
            pass

    return beta, alpha, spread, r2


def compute_kalman_hedge_and_spread(log_a: np.ndarray, log_b: np.ndarray,
                                     delta: float, Ve: float, warmup: int):
    """
    Kalman filter for time-varying hedge ratio — adapts every bar (O(N)).
    State: [alpha, beta].  Spread = one-step-ahead prediction error.
    delta: state noise (1e-5 = slow/stable, 1e-3 = fast/reactive)
    Ve:    observation noise variance
    warmup: bars before spread is trusted (same as OLS window)
    """
    n     = len(log_a)
    beta  = np.full(n, np.nan)
    alpha = np.full(n, np.nan)
    spread = np.full(n, np.nan)

    Vw    = delta / (1 - delta) * np.eye(2)   # state transition noise
    theta = np.zeros(2)                         # [alpha, beta] initial state
    P     = np.eye(2)                           # initial covariance

    for i in range(1, n):
        F = np.array([1.0, log_b[i]])

        # Predict (prior)
        P_pred = P + Vw
        y_pred = float(F @ theta)
        e      = log_a[i] - y_pred             # one-step-ahead error = spread signal

        # Update (posterior)
        S      = float(F @ P_pred @ F) + Ve
        K      = P_pred @ F / S
        theta  = theta + K * e
        P      = P_pred - np.outer(K, F) @ P_pred

        if i >= warmup:
            alpha[i]  = theta[0]
            beta[i]   = theta[1]
            spread[i] = e

    return beta, alpha, spread


def compute_rolling_r2(log_a: np.ndarray, log_b: np.ndarray, window: int) -> np.ndarray:
    """
    Fast rolling R² via Pearson correlation — equivalent to OLS R² for bivariate regression.
    Used as quality gate when Kalman filter is active (avoids full OLS rerun).
    """
    n  = len(log_a)
    r2 = np.full(n, np.nan)
    for i in range(window, n):
        la = log_a[i - window:i]
        lb = log_b[i - window:i]
        if np.std(lb) > 0 and np.std(la) > 0:
            r2[i] = np.corrcoef(la, lb)[0, 1] ** 2
    return r2


def compute_zscore_and_bands(spread: np.ndarray, zscore_window: int, bb_window: int, bb_std: float):
    """
    Z-score: (spread - rolling_mean) / rolling_std
    Dynamic BB bands applied directly on the Z-score.
    """
    n          = len(spread)
    zscore     = np.full(n, np.nan)
    upper_band = np.full(n, np.nan)
    lower_band = np.full(n, np.nan)

    for i in range(zscore_window, n):
        window_spread = spread[i - zscore_window:i]
        valid = window_spread[~np.isnan(window_spread)]
        if len(valid) < zscore_window // 2:
            continue
        mu  = float(np.mean(valid))
        sig = float(np.std(valid))
        if sig > 0:
            zscore[i] = (spread[i] - mu) / sig

    for i in range(zscore_window + bb_window, n):
        zw    = zscore[i - bb_window:i]
        valid = zw[~np.isnan(zw)]
        if len(valid) >= bb_window // 2:
            upper_band[i] = np.mean(valid) + bb_std * np.std(valid)
            lower_band[i] = np.mean(valid) - bb_std * np.std(valid)

    return zscore, upper_band, lower_band


def _daily_sharpe(daily_dict: dict) -> float:
    """Sharpe ratio computed on daily PnL — correct annualization for pairs trading."""
    arr = np.array(list(daily_dict.values()), dtype=float)
    if len(arr) < 2 or arr.std() == 0:
        return 0.0
    return float(arr.mean() / arr.std() * np.sqrt(252))


def _profit_factor(rets: pd.Series) -> float:
    wins   = rets[rets > 0]
    losses = rets[rets <= 0]
    if losses.sum() == 0:
        return float('inf')
    return float(abs(wins.sum() / losses.sum()))


def _leg_equity_curve(trades: list, start: float, pnl_key: str) -> list:
    """Step-function equity curve for one leg, updated at each trade close."""
    bal    = start
    result = []
    for t in sorted(trades, key=lambda x: x['exit_time']):
        bal += t[pnl_key]
        result.append({'time': t['exit_time'][:16], 'equity': round(bal, 4)})
    return result


def run_pair_backtest(coin_a: str, coin_b: str, dataset_dir: str,
                      date_from=DATE_FROM, date_to=DATE_TO,
                      timeframe=TIMEFRAME, signal_timeframe=None,
                      max_hold_override=None) -> dict:
    """
    Full pairs trading backtest for one pair.
    Each trade = 1 spread position = 2 simultaneous legs (Coin A + Coin B).
    Fees: 4 legs total per round-trip (open A, open B, close A, close B).
    """
    signal_tf = signal_timeframe or timeframe
    execution_tf = timeframe
    params = scaled_params(signal_tf, execution_tf)

    bars_per_8h = (8 * 60) / TIMEFRAME_MINUTES[execution_tf]
    funding_rate_per_bar = NET_FUNDING_RATE_8H / bars_per_8h

    signal_df = load_pair_data(dataset_dir, coin_a, coin_b, date_from, date_to, tf=signal_tf)
    df = signal_df if signal_tf == execution_tf else load_pair_data(
        dataset_dir, coin_a, coin_b, date_from, date_to, tf=execution_tf
    )

    min_signal_bars = params['ols_window'] + params['zscore_window'] + params['bb_window'] + 50
    if len(signal_df) < min_signal_bars or len(df) < 100:
        return {'pair': f'{coin_a}-{coin_b}', 'error': 'Insufficient data', 'cointegrated': False}

    log_a  = np.log(signal_df[coin_a].values)
    log_b  = np.log(signal_df[coin_b].values)
    signal_times = signal_df.index
    times = df.index

    # ── Step 1: Hedge ratio + spread (Kalman or rolling OLS) ─────────────────
    if USE_KALMAN:
        beta, alpha_arr, spread = compute_kalman_hedge_and_spread(
            log_a, log_b, KALMAN_DELTA, KALMAN_VE, params['ols_window']
        )
        r2 = compute_rolling_r2(log_a, log_b, params['ols_window'])
    else:
        beta, alpha_arr, spread, r2 = compute_rolling_hedge_and_spread(
            log_a, log_b, params['ols_window']
        )

    # ── Step 2: ADF test on in-sample spread (first 60%) ─────────────────────
    cutoff    = int(len(spread) * 0.60)
    is_spread = spread[params['ols_window']:cutoff]
    is_spread = is_spread[~np.isnan(is_spread)]
    adf_result   = adfuller(is_spread, maxlag=1, autolag=None) if len(is_spread) > 30 else None
    adf_pvalue   = float(adf_result[1]) if adf_result else 1.0
    cointegrated = adf_pvalue < ADF_PVALUE_MAX

    half_life = float(np.nanmedian([
        compute_half_life(is_spread[i:i + 500])
        for i in range(0, len(is_spread) - 500, 200)
        if len(is_spread[i:i + 500]) > 100
    ])) if len(is_spread) > 600 else np.nan

    # ── Step 3: Z-score + dynamic bands ──────────────────────────────────────
    zscore, upper_band, lower_band = compute_zscore_and_bands(
        spread, params['zscore_window'], params['bb_window'], BB_STD
    )

    # Rolling ADF regime is computed on signal bars, then forward-filled to
    # execution bars for multi-timeframe runs.
    signal_regime_ok = np.ones(len(signal_df), dtype=bool)
    regime_ok = True
    last_adf_bar = 0
    for j in range(len(signal_df)):
        if (j - last_adf_bar) >= params['rolling_adf_bars'] and not np.isnan(spread[j]):
            last_adf_bar = j
            w = spread[max(0, j - params['ols_window']):j]
            v = w[~np.isnan(w)]
            if len(v) > 100:
                try:
                    regime_ok = adfuller(v, maxlag=1, autolag=None)[1] < ROLLING_ADF_PVAL
                except Exception:
                    pass
        signal_regime_ok[j] = regime_ok

    signal_frame = pd.DataFrame({
        'beta': beta,
        'spread': spread,
        'zscore': zscore,
        'upper_band': upper_band,
        'lower_band': lower_band,
        'r2': r2,
        'regime_ok': signal_regime_ok,
    }, index=signal_times)
    aligned_signal = signal_frame.reindex(times, method='ffill')

    # ── Step 4: Bar-by-bar trade simulation ──────────────────────────────────
    initial_balance = CAPITAL_PER_LEG * 2
    balance         = float(initial_balance)
    equity_curve    = []
    trades          = []

    in_trade      = False
    trade_side    = 0
    entry_idx     = None
    entry_z       = None
    entry_r2      = None
    entry_pa      = None
    entry_pb      = None
    entry_beta    = None
    reversal_best_z = None
    size_a        = 0.0
    size_b        = 0.0
    entry_fee_a   = 0.0
    entry_fee_b   = 0.0
    mfe = mae     = 0.0
    expected_profit = 0.0
    accumulated_funding = 0.0

    # Enhancement state
    last_exit_idx  = -(params['cooldown_bars'] + 1)  # allow entry from bar 0
    consecutive_zstops = 0
    zstop_pause_until  = -1

    half_life_exec_bars = (
        half_life * TIMEFRAME_MINUTES[signal_tf] / TIMEFRAME_MINUTES[execution_tf]
        if (not np.isnan(half_life) and half_life > 0) else np.nan
    )
    if max_hold_override is not None:
        max_hold = int(max_hold_override)
    elif not np.isnan(half_life_exec_bars) and half_life_exec_bars > 0:
        max_hold = int(half_life_exec_bars * 2)
    else:
        max_hold = 168 * timeframe_scale(execution_tf)

    price_a = df[coin_a].values
    price_b = df[coin_b].values

    for i in range(len(df)):
        pa = price_a[i]
        pb = price_b[i]
        sig = aligned_signal.iloc[i]
        z  = sig['zscore']
        ub = sig['upper_band']
        lb = sig['lower_band']
        current_r2 = sig['r2']
        current_beta = sig['beta']
        current_regime_ok = bool(sig['regime_ok']) if pd.notna(sig['regime_ok']) else False
        t  = times[i]
        running = 0.0

        if in_trade:
            pnl_a_u = size_a * (pa - entry_pa) * trade_side
            pnl_b_u = size_b * (entry_pb - pb) * trade_side
            running = pnl_a_u + pnl_b_u
            mfe = max(mfe, running)
            mae = min(mae, running)
            
            # Realism: Account Margin Liquidation (Cross Margin)
            if balance + running <= 0:
                reason = 'LIQUIDATED'
                z_stop = funding_exit = reversal_trail = z_exit = time_stop = z_reversal = False

        circuit_ok = i >= zstop_pause_until
        turn_ok = True
        if CONFIRM_TURN:
            prev_z = aligned_signal['zscore'].iloc[i - 1] if i > 0 else np.nan
            turn_ok = (not np.isnan(prev_z) and
                       ((z >  MIN_ENTRY_Z and z < prev_z) or
                        (z < -MIN_ENTRY_Z and z > prev_z)))

        # Daily regime gate: block entry if Z drifted too far in last 24h
        z_drift_ok = True
        if DAILY_REGIME_GATE:
            drift_bars = params['daily_drift_bars']
            if i >= drift_bars:
                prev_z_daily = aligned_signal['zscore'].iloc[i - drift_bars]
                if not np.isnan(prev_z_daily):
                    z_drift_ok = abs(z - prev_z_daily) <= DAILY_Z_DRIFT_MAX

        # ── Entry ─────────────────────────────────────────────────────────────
        if (not in_trade and
                current_regime_ok and
                circuit_ok and
                z_drift_ok and
                not np.isnan(z) and
                not np.isnan(current_r2) and current_r2 >= MIN_R2 and
                abs(z) >= MIN_ENTRY_Z and
                abs(z) <= MAX_ENTRY_Z and
                (i - last_exit_idx) >= params['cooldown_bars'] and
                turn_ok):
            b           = current_beta if not np.isnan(current_beta) else 1.0
            trade_side  = -1 if z > 0 else +1
            current_capital_per_leg = balance / 2.0
            size_a      = (current_capital_per_leg * LEVERAGE) / pa
            size_b      = abs(b) * (current_capital_per_leg * LEVERAGE) / pb
            entry_fee_a = size_a * pa * TRADING_FEE
            entry_fee_b = size_b * pb * TRADING_FEE
            balance    -= (entry_fee_a + entry_fee_b)
            in_trade    = True
            entry_idx   = i
            entry_z     = z
            entry_r2    = current_r2
            entry_pa    = pa
            entry_pb    = pb
            entry_beta  = b
            reversal_best_z = None
            mfe = mae   = 0.0
            expected_profit = abs(sig['spread']) * (CAPITAL_PER_LEG * LEVERAGE) if not np.isnan(sig['spread']) else 0.0
            accumulated_funding = 0.0

        # ── Exit ──────────────────────────────────────────────────────────────
        elif in_trade:
            current_short_value = size_b * pb if trade_side == 1 else size_a * pa
            accumulated_funding += current_short_value * funding_rate_per_bar
            
            hold_bars  = i - entry_idx
            time_stop  = hold_bars >= max_hold
            funding_exit = (expected_profit > 0 and accumulated_funding >= expected_profit)
            
            current_net_est = None
            if not np.isnan(z):
                exit_fee_a_est = size_a * pa * TRADING_FEE
                exit_fee_b_est = size_b * pb * TRADING_FEE
                current_net_est = running - entry_fee_a - entry_fee_b - exit_fee_a_est - exit_fee_b_est - accumulated_funding
            # Pure formula: exit when Z crosses back through zero
            z_exit     = (not np.isnan(z) and
                          hold_bars >= params['min_hold_bars'] and
                          ((trade_side == -1 and z <= 0) or
                           (trade_side ==  1 and z >= 0)))
            # Enhancement 4: hard Z-stop if spread diverges further past threshold
            z_stop     = (not np.isnan(z) and
                          ((trade_side == -1 and z >  Z_STOP_LOSS) or
                           (trade_side ==  1 and z < -Z_STOP_LOSS)))

            if not np.isnan(z):
                if trade_side == -1 and z <= 0:
                    reversal_best_z = z if reversal_best_z is None else min(reversal_best_z, z)
                elif trade_side == 1 and z >= 0:
                    reversal_best_z = z if reversal_best_z is None else max(reversal_best_z, z)

            reversal_trail_armed = (reversal_best_z is not None and
                                    ((trade_side == -1 and reversal_best_z <= -REVERSAL_TRAIL_Z) or
                                     (trade_side ==  1 and reversal_best_z >=  REVERSAL_TRAIL_Z)))
            reversal_trail = (not np.isnan(z) and
                              reversal_trail_armed and
                              reversal_best_z is not None and
                              current_net_est is not None and
                              current_net_est > 0 and
                              ((trade_side == -1 and z >= reversal_best_z + REVERSAL_TRAIL_Z) or
                               (trade_side ==  1 and z <= reversal_best_z - REVERSAL_TRAIL_Z)))
            z_reversal = (not np.isnan(z) and
                          ((trade_side ==  1 and z >  MIN_ENTRY_Z) or
                           (trade_side == -1 and z < -MIN_ENTRY_Z)))

            if 'reason' not in locals() or reason != 'LIQUIDATED':
                reason = None
            if reason == 'LIQUIDATED': pass
            elif z_stop:             reason = 'Z_STOP'
            elif funding_exit:     reason = 'FUNDING_BLEED'
            elif reversal_trail:   reason = 'REVERSAL_TRAIL'
            elif z_exit:           reason = 'MEAN_REVERT'
            elif time_stop:        reason = 'TIME_STOP'
            elif z_reversal:       reason = 'REVERSAL'

            if reason:
                pnl_a      = size_a * (pa - entry_pa) * trade_side
                pnl_b      = size_b * (entry_pb - pb) * trade_side
                exit_fee_a = size_a * pa * TRADING_FEE
                exit_fee_b = size_b * pb * TRADING_FEE
                fee_a      = entry_fee_a + exit_fee_a
                fee_b      = entry_fee_b + exit_fee_b
                total_fee  = fee_a + fee_b + accumulated_funding
                net_pnl_a  = pnl_a - fee_a - (accumulated_funding / 2)
                net_pnl_b  = pnl_b - fee_b - (accumulated_funding / 2)
                net        = net_pnl_a + net_pnl_b
                balance   += (pnl_a + pnl_b - exit_fee_a - exit_fee_b - accumulated_funding)

                trades.append({
                    'entry_time':  str(times[entry_idx]),
                    'exit_time':   str(t),
                    'side':        'LONG_SPREAD'  if trade_side == 1 else 'SHORT_SPREAD',
                    'side_a':      'LONG'  if trade_side == 1 else 'SHORT',
                    'side_b':      'SHORT' if trade_side == 1 else 'LONG',
                    'coin_a':      coin_a,
                    'coin_b':      coin_b,
                    'entry_pa':    round(entry_pa, 4),
                    'entry_pb':    round(entry_pb, 4),
                    'exit_pa':     round(pa, 4),
                    'exit_pb':     round(pb, 4),
                    'hedge_ratio': round(entry_beta, 4),
                    'entry_z':     round(entry_z, 4),
                    'entry_r2':    round(entry_r2, 4),
                    'exit_z':      round(float(z), 4) if not np.isnan(z) else None,
                    'hold_bars':   hold_bars,
                    'pnl_a':       round(pnl_a, 4),
                    'pnl_b':       round(pnl_b, 4),
                    'fee_a':       round(fee_a, 4),
                    'fee_b':       round(fee_b, 4),
                    'funding_fee': round(accumulated_funding, 4),
                    'fee':         round(total_fee, 4),
                    'net_pnl_a':   round(net_pnl_a, 4),
                    'net_pnl_b':   round(net_pnl_b, 4),
                    'net_pnl':     round(net, 4),
                    'mfe':         round(mfe, 4),
                    'mae':         round(mae, 4),
                    'reason':      reason,
                })
                if reason == 'Z_STOP':
                    consecutive_zstops += 1
                    if consecutive_zstops >= ZSTOP_CIRCUIT_BREAKER:
                        zstop_pause_until = i + ZSTOP_PAUSE_BARS * timeframe_scale(execution_tf)
                        consecutive_zstops = 0
                else:
                    consecutive_zstops = 0
                in_trade      = False
                trade_side    = 0
                last_exit_idx = i   # Enhancement 2: start cooldown
                reversal_best_z = None
                mfe = mae     = 0.0
                accumulated_funding = 0.0

        current_equity = balance + (running if in_trade else 0.0)
        equity_curve.append({'time': str(t), 'equity': round(current_equity, 4)})
        
        if balance <= 0:
            break

    # ── Step 5: Core metrics ──────────────────────────────────────────────────
    final_balance = balance
    total_pnl     = final_balance - initial_balance
    roi           = (total_pnl / initial_balance) * 100

    eq       = pd.Series([e['equity'] for e in equity_curve])
    roll_max = eq.cummax()
    dd       = (eq - roll_max) / roll_max * 100
    max_dd   = float(dd.min())

    rets     = pd.Series([t['net_pnl']   for t in trades])
    rets_a   = pd.Series([t['net_pnl_a'] for t in trades])
    rets_b   = pd.Series([t['net_pnl_b'] for t in trades])

    win_rate   = len(rets[rets > 0]) / len(rets) * 100 if len(rets) > 0 else 0
    profit_fac = _profit_factor(rets)
    avg_hold   = float(pd.Series([t['hold_bars'] for t in trades]).mean()) if trades else 0

    # ── Step 6: Daily Percentage Return Sharpe (correct for compounding) ─────
    if len(equity_curve) > 0:
        eq_df = pd.DataFrame(equity_curve)
        eq_df['time'] = pd.to_datetime(eq_df['time'])
        eq_df.set_index('time', inplace=True)
        daily_eq = eq_df['equity'].resample('D').last().dropna()
        daily_ret = daily_eq.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(daily_ret) > 1 and daily_ret.std() != 0:
            sharpe = round((daily_ret.mean() / daily_ret.std()) * np.sqrt(365), 3)
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    sharpe_a = 0.0
    sharpe_b = 0.0

    # ── Step 7: Calmar ratio ──────────────────────────────────────────────────
    n_days       = (pd.Timestamp(date_to) - pd.Timestamp(date_from)).days
    annualized_r = roi / (n_days / 365)
    calmar       = round(annualized_r / abs(max_dd), 3) if max_dd != 0 else 0.0

    # ── Step 8: Per-coin breakdown ────────────────────────────────────────────
    pnl_a_sum  = round(sum(t['pnl_a']     for t in trades), 2)
    pnl_b_sum  = round(sum(t['pnl_b']     for t in trades), 2)
    fee_a_sum  = round(sum(t['fee_a']     for t in trades), 2)
    fee_b_sum  = round(sum(t['fee_b']     for t in trades), 2)
    net_a      = round(sum(t['net_pnl_a'] for t in trades), 2)
    net_b      = round(sum(t['net_pnl_b'] for t in trades), 2)
    roi_a      = round(net_a / CAPITAL_PER_LEG * 100, 2)
    roi_b      = round(net_b / CAPITAL_PER_LEG * 100, 2)

    wins_a     = len([t for t in trades if t['net_pnl_a'] > 0])
    wins_b     = len([t for t in trades if t['net_pnl_b'] > 0])
    win_rate_a = round(wins_a / len(trades) * 100, 1) if trades else 0
    win_rate_b = round(wins_b / len(trades) * 100, 1) if trades else 0

    pf_a = round(_profit_factor(rets_a), 3) if len(rets_a) > 0 else None
    pf_b = round(_profit_factor(rets_b), 3) if len(rets_b) > 0 else None
    # Cap inf
    pf_a = pf_a if pf_a != float('inf') else None
    pf_b = pf_b if pf_b != float('inf') else None

    # Fee drag: fees / |gross_pnl|. Cap at 9999 for display.
    fee_drag_a = round(min(fee_a_sum / abs(pnl_a_sum) * 100, 9999), 1) if pnl_a_sum != 0 else 9999
    fee_drag_b = round(min(fee_b_sum / abs(pnl_b_sum) * 100, 9999), 1) if pnl_b_sum != 0 else 9999

    # ── Step 9: Exit breakdown ────────────────────────────────────────────────
    n_t      = len(trades)
    mr_n     = sum(1 for t in trades if t['reason'] == 'MEAN_REVERT')
    ts_n     = sum(1 for t in trades if t['reason'] == 'TIME_STOP')
    rev_n    = sum(1 for t in trades if t['reason'] == 'REVERSAL')
    trail_n  = sum(1 for t in trades if t['reason'] == 'REVERSAL_TRAIL')
    zstop_n  = sum(1 for t in trades if t['reason'] == 'Z_STOP')
    fund_n   = sum(1 for t in trades if t['reason'] == 'FUNDING_BLEED')
    liq_n    = sum(1 for t in trades if t['reason'] == 'LIQUIDATED')
    exit_mr_pct    = round(mr_n    / n_t * 100, 1) if n_t else 0
    exit_ts_pct    = round(ts_n    / n_t * 100, 1) if n_t else 0
    exit_rev_pct   = round(rev_n   / n_t * 100, 1) if n_t else 0
    exit_trail_pct = round(trail_n / n_t * 100, 1) if n_t else 0
    exit_zstop_pct = round(zstop_n / n_t * 100, 1) if n_t else 0
    exit_fund_pct  = round(fund_n  / n_t * 100, 1) if n_t else 0
    exit_liq_pct   = round(liq_n   / n_t * 100, 1) if n_t else 0

    # ── Step 10: Regime split ─────────────────────────────────────────────────
    n_bars   = len(df)
    is_end   = n_bars * 6 // 10
    oos1_end = n_bars * 8 // 10

    def _split_pnl(cutoff_start, cutoff_end):
        def _idx(ts_str):
            pos = times.searchsorted(pd.Timestamp(ts_str))
            return min(pos, len(times) - 1)
        subset = [t for t in trades
                  if cutoff_start <= _idx(t['entry_time']) < cutoff_end]
        return round(sum(t['net_pnl'] for t in subset), 2), len(subset)

    is_pnl,   is_n   = _split_pnl(0, is_end)
    oos1_pnl, oos1_n = _split_pnl(is_end, oos1_end)
    oos2_pnl, oos2_n = _split_pnl(oos1_end, n_bars)

    valid_betas = beta[~np.isnan(beta)]
    median_beta = float(np.median(valid_betas)) if len(valid_betas) > 0 else np.nan

    # ── Step 11: Time-series data ─────────────────────────────────────────────
    zscore_series = [
        {'time':  str(signal_times[i]),
         'z':     round(float(zscore[i]), 4),
         'upper': round(float(upper_band[i]), 4) if not np.isnan(upper_band[i]) else None,
         'lower': round(float(lower_band[i]), 4) if not np.isnan(lower_band[i]) else None}
        for i in range(0, len(signal_df), max(1, 24 * timeframe_scale(signal_tf)))
        if not np.isnan(zscore[i])
    ]

    # Full price series for Pairs Dance Chart — sampled every 12 bars (12h resolution)
    # Gives ~2500 continuous points across 3.5 years; avoids the sparse-trade artifact
    price_series = [
        {'time': str(times[i]),
         'pa':   round(float(price_a[i]), 4),
         'pb':   round(float(price_b[i]), 4)}
        for i in range(0, len(df), 12)
    ]

    # Per-leg equity curves (step-function at each trade close)
    eq_curve_a = _leg_equity_curve(trades, CAPITAL_PER_LEG, 'net_pnl_a')
    eq_curve_b = _leg_equity_curve(trades, CAPITAL_PER_LEG, 'net_pnl_b')

    return {
        'pair':          f'{coin_a}-{coin_b}',
        'coin_a':        coin_a,
        'coin_b':        coin_b,
        'cointegrated':  cointegrated,
        'adf_pvalue':    round(adf_pvalue, 4),
        'half_life_bars': round(half_life, 1) if not np.isnan(half_life) else None,
        'median_hedge_ratio': round(median_beta, 4) if not np.isnan(median_beta) else None,
        # Combined account
        'initial_balance': initial_balance,
        'final_balance':   round(final_balance, 2),
        'roi':             round(roi, 2),
        'sharpe':          sharpe,
        'sharpe_a':        sharpe_a,
        'sharpe_b':        sharpe_b,
        'calmar':          calmar,
        'max_drawdown':    round(max_dd, 2),
        'total_trades':    len(trades),
        'win_rate':        round(win_rate, 1),
        'profit_factor':   round(profit_fac, 3) if profit_fac != float('inf') else None,
        'avg_hold_bars':   round(avg_hold, 1),
        'total_fees':      round(fee_a_sum + fee_b_sum, 2),
        # Exit breakdown
        'exit_mr_pct':     exit_mr_pct,
        'exit_ts_pct':     exit_ts_pct,
        'exit_rev_pct':    exit_rev_pct,
        'exit_trail_pct':  exit_trail_pct,
        'exit_zstop_pct':  exit_zstop_pct,
        'exit_fund_pct':   exit_fund_pct,
        'exit_liq_pct':    exit_liq_pct,
        # Coin A breakdown
        'coin_a_pnl':      pnl_a_sum,
        'coin_a_fees':     fee_a_sum,
        'coin_a_net':      net_a,
        'coin_a_roi':      roi_a,
        'coin_a_sharpe':   sharpe_a,
        'coin_a_win_rate': win_rate_a,
        'coin_a_pf':       pf_a,
        'coin_a_fee_drag': fee_drag_a,
        # Coin B breakdown
        'coin_b_pnl':      pnl_b_sum,
        'coin_b_fees':     fee_b_sum,
        'coin_b_net':      net_b,
        'coin_b_roi':      roi_b,
        'coin_b_sharpe':   sharpe_b,
        'coin_b_win_rate': win_rate_b,
        'coin_b_pf':       pf_b,
        'coin_b_fee_drag': fee_drag_b,
        # Regime split
        'is_pnl':    is_pnl,   'is_trades':   is_n,
        'oos1_pnl':  oos1_pnl, 'oos1_trades': oos1_n,
        'oos2_pnl':  oos2_pnl, 'oos2_trades': oos2_n,
        # Time-series
        'price_series':    price_series,
        'zscore_series':   zscore_series,
        'equity_curve':    equity_curve[::24],
        'equity_curve_a':  eq_curve_a,
        'equity_curve_b':  eq_curve_b,
        'trades':          trades,
        'params': {
            'engine_version':    'v4',
            'ols_window':       params['ols_window'],
            'zscore_window':    params['zscore_window'],
            'bb_window':        params['bb_window'],
            'bb_std':           BB_STD,
            'exit_zscore':      EXIT_ZSCORE,
            'trading_fee':      TRADING_FEE,
            'capital_per_leg':  CAPITAL_PER_LEG,
            'leverage':         LEVERAGE,
            'date_from':        date_from,
            'date_to':          date_to,
            'timeframe':        execution_tf,
            'signal_timeframe': signal_tf,
            'execution_timeframe': execution_tf,
            'min_entry_z':      MIN_ENTRY_Z,
            'cooldown_bars':    params['cooldown_bars'],
            'min_hold_bars':    params['min_hold_bars'],
            'z_stop_loss':      Z_STOP_LOSS,
            'rolling_adf_bars': params['rolling_adf_bars'],
            'rolling_adf_pval': ROLLING_ADF_PVAL,
            'min_r2':           MIN_R2,
            'confirm_turn':     CONFIRM_TURN,
            'zstop_circuit_breaker': ZSTOP_CIRCUIT_BREAKER,
            'zstop_pause_bars': ZSTOP_PAUSE_BARS,
            'reversal_trail_z': REVERSAL_TRAIL_Z,
            'max_entry_z':      MAX_ENTRY_Z,
            'use_kalman':       USE_KALMAN,
            'kalman_delta':     KALMAN_DELTA,
            'kalman_ve':        KALMAN_VE,
            'daily_regime_gate':  DAILY_REGIME_GATE,
            'daily_z_drift_max':  DAILY_Z_DRIFT_MAX,
        },
    }
