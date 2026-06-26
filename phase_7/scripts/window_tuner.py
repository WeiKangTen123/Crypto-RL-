import optuna
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager
from strategy_backtest.metrics import compute_metrics, _extract_numeric

optuna.logging.set_verbosity(optuna.logging.WARNING)

DEFAULT_RANGES = {
    # ── Generic ──────────────────────────────────────────────────────────────
    'period':               (5,    50),
    'length':               (5,    50),
    'lookback':             (5,    50),
    'smoothing':            (2,    20),
    # ── MACD ─────────────────────────────────────────────────────────────────
    'fast':                 (3,    30),
    'slow':                 (15,  100),
    'signal':               (3,    20),
    'macd_fast':            (3,    30),
    'macd_slow':            (15,  100),
    'macd_signal':          (3,    20),
    # ── RSI ──────────────────────────────────────────────────────────────────
    'rsi_period':           (5,    30),
    'rsi_oversold':         (20,   40),
    'rsi_overbought':       (60,   80),
    # ── EMA / SMA ────────────────────────────────────────────────────────────
    'ema_fast':             (5,    30),
    'ema_slow':             (20,  200),
    'ema_period':           (10,  200),
    # ── ATR / Multipliers ────────────────────────────────────────────────────
    'atr_multiplier':       (1.0,  6.0),
    'st_multiplier':        (1.0,  5.0),
    'supertrend_multiplier':(1.0,  5.0),
    # ── SL / TP / Hold ───────────────────────────────────────────────────────
    'sl_pct':               (0.01, 0.20),
    'tp_rr':                (1.0,  5.0),
    'stop_loss_pct':        (0.005, 0.10),
    'take_profit_pct':      (0.01,  0.20),
    # ── Strategy 86 specific ─────────────────────────────────────────────────
    'short_momentum_period': (5, 50),
    'long_reversal_period':  (20, 200),
    'williams_r_period':     (5, 30),
    'tsi_fast_period':       (5, 30),
    'tsi_slow_period':       (15, 60),
    'chop_period':           (5, 30),
    'momentum_threshold_entry': (0.001, 0.05),
    'reversal_threshold_entry': (0.001, 0.1),
    # ── Strategy 76 specific ────────────────────────────────────────────────
    'funding_threshold_long':  (-0.001, 0.0),
    'funding_threshold_short': (0.0, 0.001),
    'exit_threshold_long':     (-0.0002, 0.0002),
    'exit_threshold_short':    (-0.0002, 0.0002),
    'funding_lookback_period': (12, 48),
    # ── Strategy 85 specific ────────────────────────────────────────────────
    'tp_atr_mult':  (1.0, 8.0),
    'sl_atr_mult':  (0.5, 4.0),
    'st_period':    (5, 50),
    'adx_threshold':(15, 40),
    # ── Strategy 10 specific ────────────────────────────────────────────────
    'bb_period':             (10,  100),
    'bb_std':                (1.0, 4.0),
    'intensity_period':      (5,   50),
    'intensity_std':         (1.0, 5.0),
    'taker_ratio_threshold': (0.45, 0.70),
    'max_hold_bars':         (2, 48),
    # ── ADX ─────────────────────────────────────────────────────────────────
    'adx_period':            (5,   50),
    # ── KDJ (Strategy 1) ────────────────────────────────────────────────────
    'kdj_period':            (3, 30),
    'kdj_oversold':          (15,  45),
    'kdj_overbought':        (55,  85),
    'entry_window':          (1,   15),
    'trend_ema_period':      (20, 300),
    # ── Boolean filters (categorical) ────────────────────────────────────────
    'trend_filter':          [True, False],
    'use_trend_filter':      [True, False],
    'require_confirmation':  [True, False],
    # ── Squeeze/FVG (Strategy 2, 5) ─────────────────────────────────────────
    'kc_multiplier':         (1.0,  3.5),
    'atr_multiplier_tp':     (1.0,  8.0),
    'min_gap_pct':           (0.001, 0.03),
    'retrace_depth':         (0.3,  1.0),
    'tp_multiplier':         (1.5, 10.0),
    # ── Multi-TF (Strategy 86) ───────────────────────────────────────────────
    'htf_ema_period':        (100, 1500),
    'tp_pct':                (0.02, 0.20),
}

MIN_TRADES  = 5   # Reject trials with fewer trades — avoids single-trade luck
PATIENCE    = 6   # Stop early if best Sharpe doesn't improve for this many consecutive trials


class _EarlyStopping:
    """Stop Optuna study when best value hasn't improved for `patience` trials."""
    def __init__(self, patience=PATIENCE):
        self.patience   = patience
        self._best      = None
        self._stagnant  = 0

    def __call__(self, study, trial):
        current_best = study.best_value
        if self._best is None or current_best > self._best + 1e-6:
            self._best     = current_best
            self._stagnant = 0
        else:
            self._stagnant += 1
        if self._stagnant >= self.patience:
            study.stop()


def optimize_window(df, strat_cls, base_params, risk_cfg, n_trials=30):
    """
    Run a mini Optuna study for a single window.

    Improvements over naive approach:
    - Respects strat_cls.OPTIMIZATION_RANGES (merges over DEFAULT_RANGES, same as finetune.py)
    - Calls strat_cls.validate_params to reject degenerate param combos early
    - TPE sampler with n_startup_trials=5  (was 10) → doubles smart search
    - multivariate=True  → considers parameter correlations
    - seed=42            → reproducible results
    - Early stopping     → stops when no improvement for PATIENCE trials
    - Returns best_trial_number so callers can gauge convergence quality

    Returns (best_params, best_sharpe, best_trial_number)
    """
    # Merge: strategy-specific ranges override defaults for named keys (same logic as finetune.py)
    ranges = dict(DEFAULT_RANGES)
    if hasattr(strat_cls, 'OPTIMIZATION_RANGES'):
        ranges.update(strat_cls.OPTIMIZATION_RANGES)

    tunable = {k: v for k, v in base_params.items() if k in ranges}
    fixed   = {k: v for k, v in base_params.items() if k not in ranges}

    if not tunable:
        return base_params, 0.0, 0

    rm = RiskManager(
        risk_per_trade=risk_cfg['risk_per_trade'],
        leverage=risk_cfg['leverage'],
        trading_fee=risk_cfg['trading_fee'],
    )

    def objective(trial):
        trial_params = dict(fixed)
        for k, v in tunable.items():
            r = ranges[k]
            if isinstance(r, list):
                # Categorical param (e.g. mode=['strict', 'relaxed'])
                trial_params[k] = trial.suggest_categorical(k, r)
            elif isinstance(v, int):
                lo, hi = r
                trial_params[k] = trial.suggest_int(k, int(lo), int(hi))
            else:
                lo, hi = r
                trial_params[k] = trial.suggest_float(k, float(lo), float(hi))

        # Reject degenerate param combos early (e.g. MACD fast ≈ slow, tp < sl)
        if hasattr(strat_cls, 'validate_params') and not strat_cls.validate_params(trial_params):
            return -999.0

        try:
            engine = BacktestEngine(
                df, strat_cls(df, **trial_params), rm,
                initial_balance=risk_cfg['initial_balance']
            )
            equity = engine.run()
            if not equity or len(equity) < 2:
                return -999.0
            if len(engine.trades or []) < MIN_TRADES:
                return -999.0
            m  = compute_metrics(equity, risk_cfg['initial_balance'],
                                 timestamps=engine.df.index, trades=engine.trades)
            nm = _extract_numeric(m)
            return float(nm.get('Sharpe Ratio', -999))
        except Exception:
            return -999.0

    sampler = optuna.samplers.TPESampler(
        n_startup_trials=5,    # was 10 — halves random warmup, doubles smart search
        multivariate=True,     # considers param correlations (e.g. SL + TP together)
        seed=42,               # reproducible results per window
    )

    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.optimize(
        objective,
        n_trials=n_trials,
        callbacks=[_EarlyStopping(patience=PATIENCE)],
        show_progress_bar=False,
    )

    best_params = dict(fixed)
    best_params.update(study.best_params)

    # Trial number where the best was found (1-indexed for readability)
    best_trial_num    = (study.best_trial.number + 1) if study.best_trial else n_trials
    # Actual trials run — less than n_trials only if _EarlyStopping fired
    actual_trials_run = len(study.trials)

    return best_params, study.best_value, best_trial_num, actual_trials_run
