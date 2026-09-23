"""
BTC-USDT futures Gymnasium environment — Session 7.

Observation : float32 array of shape (SEQ_LEN, n_features + N_PORTFOLIO_FEATS)
              Last SEQ_LEN 1h bars of normalised multi-TF features,
              concatenated with rolling portfolio state at each bar.

Action (5D continuous Box[-1, 1]) — Session 17 Risk + Hold Action Space:
  [0] pos_size    linear remap to [POS_SIZE_MIN, POS_SIZE_MAX]         — fraction of equity per trade
  [1] sl_atr_mult linear remap to [SL_ATR_MULT_MIN, SL_ATR_MULT_MAX]  — stop = entry ± mult×ATR
  [2] tp_atr_mult linear remap to [TP_ATR_MULT_MIN, TP_ATR_MULT_MAX]  — target = entry ± mult×ATR
  [3] trail_on    sigmoid(×3) > 0.5                                    — trailing stop flag
  [4] hold_target log-scale remap to [HOLD_TARGET_LOG_MIN, HOLD_TARGET_LOG_MAX] bars
                  → agent chooses per-trade timeout: 8h (scalp) to 30 days (trend ride)

  Portfolio feature [3] = hold_bars / hold_target (progress toward this trade's timeout).
  Combined usage pattern:
    Trend trade:  hold_target=720, trail_on=True, tp_atr_mult=2.0  → trailing stop rides trend
    Scalp:        hold_target=12,  trail_on=False, tp_atr_mult=1.0 → tight TP/SL, quick exit

Direction (rule-based, unchanged from Session 5):
  composite = 0.65 × macro_score + 0.35 × swing_score, gated by regime_score
  IF composite >  ENTRY_THRESHOLD AND regime_score > -0.20 → LONG
  IF composite < -ENTRY_THRESHOLD AND regime_score > -0.20 → SHORT
  ELSE                                                    → FLAT

Risk params are set at entry and govern the trade:
  - Fixed SL: price hits entry ± sl_atr_mult × ATR → close
  - TP:       price hits entry ± tp_atr_mult × ATR → close
  - Trailing: peak tracks favorable price; SL trails by sl_atr_mult × ATR_at_entry

Portfolio feature [2] = SL-distance (replaces old leverage-norm slot):
  = (cur_px − sl_price) / cur_px × position  → positive = above SL, near 0 = near stop

Leverage is fixed at 1.0.  Exposure is captured entirely by pos_size.

Reward decomposition (fraction of equity):
  + bar unrealised PnL  (price_change × pos_size, every bar when holding)
  − entry fee           (FEE_RATE × pos_size, at open)
  − funding cost        (FUNDING_PER_BAR × pos_size, per bar when holding)
  − exit fee            (FEE_RATE × pos_size, at close)
  +/− trend-alignment bonus/penalty (per-bar exit-timing incentive)
  − drawdown penalty    (scales with DD severity)
  − chop penalty        (penalises entries in choppiness > 0.7)
"""

import math
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from DRL_BTC.config import (
    SEQ_LEN, INITIAL_CAPITAL,
    FEE_RATE, FUNDING_PER_BAR,
    MAX_LEVERAGE, MIN_LEVERAGE,
    MAX_POS_FRACTION, MIN_POS_FRACTION,
    ENTRY_THRESHOLD, MAX_DRAWDOWN_KILL,
    DD_PENALTY_SCALE, CHOP_PENALTY, REWARD_SCALE,
    TRAIN_END, VAL_START, VAL_END, TEST_START,
    POS_SIZE_MIN, POS_SIZE_MAX,
    SL_ATR_MULT_MIN, SL_ATR_MULT_MAX,
    TP_ATR_MULT_MIN, TP_ATR_MULT_MAX,
    ATR_FEATURE, ATR_SCALE, MAX_HOLD_BARS, MIN_HOLD_BARS, MAX_EPISODE_BARS,
    HOLD_TARGET_LOG_MIN, HOLD_TARGET_LOG_MAX,
    RISK_BUDGET_DD_10, RISK_BUDGET_DD_20, RISK_BUDGET_DD_30,
    # Pillar 4: Adaptive TP
    ADAPTIVE_TP_TRIGGER, ADAPTIVE_TP_EXTEND, ADAPTIVE_TP_MAX_EXT,
    # Pillar 5: Portfolio Objective
    PORTFOLIO_SORTINO_WEIGHT, PORTFOLIO_SHARPE_WINDOW,
)

N_PORTFOLIO_FEATS = 8


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-float(x)))


def _portfolio_reward(returns: list, window: int, scale: float) -> float:
    """Pillar 5: Sortino-weighted portfolio bonus/penalty at each trade close."""
    rets = returns[-window:] if len(returns) > window else list(returns)
    if len(rets) < 3:
        return 0.0
    arr     = np.array(rets, dtype=np.float64)
    mu      = float(arr.mean())
    neg     = arr[arr < 0]
    sigma_d = float(neg.std()) if len(neg) > 1 else 1e-4
    sortino = mu / (sigma_d + 1e-8)
    return float(np.clip(sortino * scale, -0.05, 0.05))


class BTCEnv(gym.Env):
    """
    Single-asset BTC futures environment.

    Parameters
    ----------
    features  : pd.DataFrame  — normalised feature matrix (rows = 1h bars)
    close     : pd.Series     — raw 1h close prices aligned to features.index
    mode      : 'train' | 'val' | 'test'
    date_range: tuple (start_str, end_str) overrides mode-based date slicing
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        features: pd.DataFrame,
        close: pd.Series,
        mode: str = "train",
        date_range: tuple = None,
    ):
        super().__init__()

        idx = features.index
        if date_range is not None:
            start, end = date_range
            mask = (idx >= start) & (idx <= end)
        elif mode == "train":
            mask = idx <= TRAIN_END
        elif mode == "val":
            mask = (idx >= VAL_START) & (idx <= VAL_END)
        else:
            mask = idx >= TEST_START

        self._features = features.loc[mask].astype(np.float32)
        self._close    = close.loc[mask].astype(np.float64)
        self._n_raw    = self._features.shape[1]
        self._n_obs    = self._n_raw + N_PORTFOLIO_FEATS
        self._len      = len(self._features)
        self._mode     = mode

        assert self._len > SEQ_LEN + 1, f"Not enough bars for mode={mode}"

        self.observation_space = spaces.Box(
            low=-5.0, high=5.0,
            shape=(SEQ_LEN, self._n_obs),
            dtype=np.float32,
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0,
            shape=(5,),
            dtype=np.float32,
        )

        # Cache column indices for O(1) lookup every step
        cols = list(self._features.columns)
        self._chop_idx:    int | None = cols.index("choppiness_1h") if "choppiness_1h" in cols else None
        self._macro_idx:   int | None = cols.index("macro_score")   if "macro_score"   in cols else None
        self._swing_idx:   int | None = cols.index("swing_score")   if "swing_score"   in cols else None
        self._regime_idx:  int | None = cols.index("regime_score")  if "regime_score"  in cols else None
        self._atr_pct_idx: int | None = cols.index(ATR_FEATURE)     if ATR_FEATURE     in cols else None

        # Internal episode state — all reset in reset()
        self._step_idx     = SEQ_LEN
        self._ep_start_idx = SEQ_LEN   # set at each reset(); used for MAX_EPISODE_BARS cap
        self._equity       = INITIAL_CAPITAL
        self._peak_eq      = INITIAL_CAPITAL
        self._position     = 0.0    # 0=flat, +1=long, -1=short
        self._entry_px     = 0.0
        self._pos_size     = 0.0    # fraction of equity committed
        self._leverage     = 1.0    # always 1.0; exposure captured by pos_size
        self._hold_bars    = 0
        # Per-trade risk params (set at entry, frozen until exit)
        self._sl_price     = 0.0
        self._tp_price     = 0.0
        self._trail_on     = False
        self._trail_peak   = 0.0    # best price seen since entry (for trailing SL)
        self._sl_atr_mult  = 1.5    # stored for per-bar trailing update
        self._trade_atr    = 0.01   # ATR fraction at entry (for trailing distance)
        # Per-trade quality tracking (reset at each trade open)
        self._trade_mfe    = 0.0    # max favorable excursion (fraction of price, positive)
        self._trade_mae    = 0.0    # max adverse excursion (fraction of price, positive)
        # Dynamic hold target: agent chooses per-trade timeout via action[4]
        self._max_hold_this_trade = MAX_HOLD_BARS  # default; overwritten at each entry
        # Pillar 4: Adaptive TP state
        self._tp_entry_dist  = 0.0  # original TP distance fraction at entry
        self._tp_extensions  = 0    # TP extensions taken this trade
        # Pillar 5: Portfolio Objective — rolling net returns across trades
        self._trade_returns: list[float] = []

    # ── helpers ────────────────────────────────────────────────────────────────

    def _portfolio_feats(self) -> np.ndarray:
        """8 normalised portfolio-state features appended to each obs bar.

        [0] position       -1 / 0 / +1
        [1] pos_size       fraction of equity (0..1)
        [2] sl_distance    (cur−sl)/cur × dir; +ve = above stop, near 0 = near stop
        [3] hold_bars/hold_target    progress toward this trade's chosen timeout (0→1)
        [4] equity_log     log10 growth from initial capital
        [5] neg_dd         negative drawdown (0 to -1)
        [6] unrealised_pnl clipped to [-1, 1]
        [7] is_holding     binary flag
        """
        dd             = (self._peak_eq - self._equity) / (self._peak_eq + 1e-8)
        pos_unrealised = 0.0
        sl_dist        = 0.0
        if self._position != 0 and self._entry_px > 0:
            cur_px = float(self._close.iloc[self._step_idx])
            pos_unrealised = ((cur_px / self._entry_px) - 1.0) * self._position * self._leverage
            if self._sl_price > 0:
                sl_dist = (cur_px - self._sl_price) / (cur_px + 1e-8) * self._position
                sl_dist = float(np.clip(sl_dist, -0.2, 1.0))
        return np.array([
            self._position,
            self._pos_size,
            sl_dist,
            float(min(self._hold_bars, self._max_hold_this_trade)) / float(max(self._max_hold_this_trade, 1)),
            (np.log10(max(self._equity, 1)) - np.log10(INITIAL_CAPITAL)),
            float(np.clip(-dd, -1.0, 0.0)),
            float(np.clip(pos_unrealised, -1.0, 1.0)),
            float(self._position != 0),
        ], dtype=np.float32)

    def _get_obs(self) -> np.ndarray:
        raw  = self._features.iloc[self._step_idx - SEQ_LEN: self._step_idx].values
        port = self._portfolio_feats()
        obs  = np.concatenate([raw, np.tile(port, (SEQ_LEN, 1))], axis=1).astype(np.float32)
        return np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)

    def _close_position(self, close_px: float) -> float:
        """Close open position; update equity; return exit-fee reward term."""
        if self._position == 0:
            return 0.0
        pnl_pct  = (close_px / self._entry_px - 1.0) * self._position * self._leverage
        # Entry fee was charged at open; deduct only exit fee here.
        # Formula: realised = (pnl_pct - FEE_RATE×lev) × pos_size × equity
        # so that exit_fee_equity = FEE_RATE × lev × pos_size × equity (correct notional)
        net_pct  = pnl_pct - FEE_RATE * self._leverage
        realised = net_pct * self._pos_size * self._equity
        self._equity  = max(self._equity + realised, 1.0)
        self._peak_eq = max(self._peak_eq, self._equity)
        exit_fee_rew  = -FEE_RATE * self._leverage * self._pos_size

        self._position      = 0.0
        self._entry_px      = 0.0
        self._pos_size      = 0.0
        self._leverage      = 1.0
        self._hold_bars     = 0
        self._sl_price      = 0.0
        self._tp_price      = 0.0
        self._trail_on      = False
        self._trail_peak    = 0.0
        self._sl_atr_mult   = 1.5
        self._trade_atr     = 0.01
        self._tp_entry_dist = 0.0
        self._tp_extensions = 0
        return exit_fee_rew

    # ── gymnasium API ──────────────────────────────────────────────────────────

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options is not None and "start_idx" in options:
            self._step_idx = int(options["start_idx"])
        elif self._mode == "train":
            max_start = self._len - 1000
            self._step_idx = self.np_random.integers(SEQ_LEN, max(SEQ_LEN + 1, max_start))
        else:
            self._step_idx = SEQ_LEN

        self._equity      = INITIAL_CAPITAL
        self._peak_eq     = INITIAL_CAPITAL
        self._position    = 0.0
        self._entry_px    = 0.0
        self._pos_size    = 0.0
        self._leverage    = 1.0
        self._hold_bars   = 0
        self._sl_price    = 0.0
        self._tp_price    = 0.0
        self._trail_on       = False
        self._trail_peak     = 0.0
        self._sl_atr_mult    = 1.5
        self._trade_atr      = 0.01
        self._trade_mfe           = 0.0
        self._trade_mae           = 0.0
        self._max_hold_this_trade = MAX_HOLD_BARS
        self._tp_entry_dist       = 0.0
        self._tp_extensions       = 0
        self._trade_returns       = []
        self._ep_start_idx        = self._step_idx
        return self._get_obs(), {}

    def step(self, action: np.ndarray):
        action = np.clip(action, -1.0, 1.0)

        # ── decode risk actions ────────────────────────────────────────────────
        # Continuous: linear remap from [-1, 1] → [min, max]
        pos_size_act = float(POS_SIZE_MIN    + (POS_SIZE_MAX    - POS_SIZE_MIN)    * (action[0] + 1.0) / 2.0)
        sl_atr_act   = float(SL_ATR_MULT_MIN + (SL_ATR_MULT_MAX - SL_ATR_MULT_MIN) * (action[1] + 1.0) / 2.0)
        tp_atr_act   = float(TP_ATR_MULT_MIN + (TP_ATR_MULT_MAX - TP_ATR_MULT_MIN) * (action[2] + 1.0) / 2.0)
        # Binary: sigmoid with gain=3 for crisp on/off
        trail_on_act = _sigmoid(action[3] * 3) > 0.5
        # action[4]: hold_target — log scale 8h → 30 days
        # Decoding: -1 → HOLD_TARGET_LOG_MIN bars, +1 → HOLD_TARGET_LOG_MAX bars
        _log_min = math.log(HOLD_TARGET_LOG_MIN)
        _log_max = math.log(HOLD_TARGET_LOG_MAX)
        hold_target_act = int(math.exp(_log_min + (float(action[4]) + 1.0) / 2.0 * (_log_max - _log_min)))
        hold_target_act = max(HOLD_TARGET_LOG_MIN, min(HOLD_TARGET_LOG_MAX, hold_target_act))

        # ── rule-based direction from composite signal ─────────────────────────
        cur_idx = self._step_idx
        new_dir = 0.0
        if self._macro_idx is not None and self._regime_idx is not None:
            macro  = float(self._features.iloc[cur_idx, self._macro_idx])
            regime = float(self._features.iloc[cur_idx, self._regime_idx])
            if self._swing_idx is not None:
                swing    = float(self._features.iloc[cur_idx, self._swing_idx])
                combined = 0.65 * macro + 0.35 * swing
            else:
                combined = macro
            if   combined >  ENTRY_THRESHOLD and regime > -0.20: new_dir =  1.0
            elif combined < -ENTRY_THRESHOLD and regime > -0.20: new_dir = -1.0

        # ── ATR fraction: reverse the normalisation applied by feature_builder ─
        # atr_pct = (ATR14 / close).clip(0, 0.10) / 0.10
        # → real_atr_fraction = feature_value × ATR_SCALE (= feature_value × 0.10)
        atr_frac = 0.01
        if self._atr_pct_idx is not None:
            atr_frac = float(self._features.iloc[cur_idx, self._atr_pct_idx]) * ATR_SCALE
            atr_frac = max(atr_frac, 0.001)
            atr_frac = min(atr_frac, 0.04)   # cap at 4% real ATR: max SL=12%, max equity loss=7.2%

        # ── prices ────────────────────────────────────────────────────────────
        cur_px  = float(self._close.iloc[cur_idx])
        next_px = float(self._close.iloc[min(cur_idx + 1, self._len - 1)])

        step_reward      = 0.0
        position_changed = False
        trade_closed     = False  # set True whenever a trade is closed this step

        # ── trade-quality tracking locals ──────────────────────────────────────
        trade_mfe_at_close  = 0.0   # captured on trade close; 0 otherwise
        trade_mae_at_close  = 0.0
        trade_hold_at_close = 0
        exit_reason         = None  # "sl", "tp", "dir", "timeout", "kill"

        # Update running MFE/MAE with current bar's price
        if self._position != 0 and self._entry_px > 0:
            unreal = (cur_px / self._entry_px - 1.0) * self._position
            self._trade_mfe = max(self._trade_mfe, unreal)
            self._trade_mae = max(self._trade_mae, -unreal)

        # ── handle existing position ───────────────────────────────────────────
        if self._position != 0:
            # Funding carry cost
            funding_cost   = FUNDING_PER_BAR * self._leverage * self._pos_size
            self._equity  -= funding_cost * self._equity
            step_reward   -= funding_cost

            # Trailing stop: update peak then recompute SL price
            if self._trail_on:
                if self._position > 0:
                    self._trail_peak = max(self._trail_peak, cur_px)
                else:
                    self._trail_peak = min(self._trail_peak, cur_px)
                # trail SL = peak adjusted by entry ATR distance
                self._sl_price = self._trail_peak * (
                    1.0 - self._position * self._sl_atr_mult * self._trade_atr
                )

            # Pillar 4: Adaptive TP extension — extend TP when trade is running well
            if (self._tp_extensions < ADAPTIVE_TP_MAX_EXT
                    and self._tp_entry_dist > 0
                    and self._entry_px > 0
                    and self._macro_idx is not None):
                unreal_frac = (cur_px / self._entry_px - 1.0) * self._position
                if unreal_frac >= ADAPTIVE_TP_TRIGGER * self._tp_entry_dist:
                    macro_now = float(self._features.iloc[cur_idx, self._macro_idx])
                    if macro_now * self._position > 0.10:   # trend still supports direction
                        extend_frac   = ADAPTIVE_TP_EXTEND * self._trade_atr
                        self._tp_price = self._tp_price * (
                            1.0 + self._position * extend_frac
                        )
                        self._tp_extensions += 1

            # Exit conditions (rule-based only — exit_signal removed in Session 7)
            sl_hit  = (cur_px <= self._sl_price) if self._position > 0 else (cur_px >= self._sl_price)
            tp_hit  = (self._tp_price > 0) and (
                (cur_px >= self._tp_price) if self._position > 0 else (cur_px <= self._tp_price)
            )
            direction_changed = (
                (new_dir == 0.0) or (new_dir != 0.0 and new_dir != self._position)
            ) and self._hold_bars >= MIN_HOLD_BARS  # block flip exits before minimum hold

            if sl_hit or tp_hit or direction_changed or self._hold_bars >= self._max_hold_this_trade:
                # Capture trade-quality stats before resetting
                trade_mfe_at_close  = self._trade_mfe
                trade_mae_at_close  = self._trade_mae
                trade_hold_at_close = self._hold_bars
                if sl_hit:              exit_reason = "sl"
                elif tp_hit:            exit_reason = "tp"
                elif direction_changed: exit_reason = "dir"
                else:                   exit_reason = "timeout"

                # Pillar 5: record net trade return for portfolio objective
                if self._entry_px > 0 and self._pos_size > 0:
                    gross    = (cur_px / self._entry_px - 1.0) * self._position * self._leverage
                    trade_net = (gross - FEE_RATE * self._leverage * 2) * self._pos_size
                    self._trade_returns.append(float(trade_net))

                self._trade_mfe     = 0.0
                self._trade_mae     = 0.0
                step_reward        += self._close_position(cur_px)
                if exit_reason == "tp":
                    step_reward += 0.015  # TP completion bonus (was 0.005 — 3× increase to overcome per-bar noise)

                # Pillar 5: Sortino-weighted portfolio bonus/penalty at trade close
                if len(self._trade_returns) >= 5:
                    step_reward += _portfolio_reward(
                        self._trade_returns, PORTFOLIO_SHARPE_WINDOW, PORTFOLIO_SORTINO_WEIGHT
                    )

                position_changed    = True
                trade_closed        = True

        # ── Risk Budget Controller (TIA v3 hard cap) ─────────────────────────
        # current_dd needed here (before reward shaping block) for hard cap.
        current_dd = (self._peak_eq - self._equity) / (self._peak_eq + 1e-8)
        if current_dd >= 0.30:   _risk_budget = RISK_BUDGET_DD_30
        elif current_dd >= 0.20: _risk_budget = RISK_BUDGET_DD_20
        elif current_dd >= 0.10: _risk_budget = RISK_BUDGET_DD_10
        else:                    _risk_budget = 1.0
        pos_size_act = pos_size_act * _risk_budget

        # ── chop regime gate: reduce / block entries in ranging markets ───────
        # Consolidation/chop causes whipsaw losses regardless of signal quality.
        # 0.80+ = strongly ranging (raw Choppiness ≈57+): block entry entirely.
        # 0.65–0.80 + no trend (regime_score ≤ 0): halve position size.
        # Does NOT affect flat penalty (actor still learns choppy entries are costly).
        if (self._position == 0 and new_dir != 0.0
                and self._chop_idx is not None and self._regime_idx is not None):
            chop_val = float(self._features.iloc[cur_idx, self._chop_idx])
            regime_v = float(self._features.iloc[cur_idx, self._regime_idx])
            if chop_val > 0.80:
                pos_size_act = 0.0                      # block: severely choppy
            elif chop_val > 0.65 and regime_v <= 0.0:
                pos_size_act *= 0.50                    # scale: moderate chop, no trend

        # ── open new position ─────────────────────────────────────────────────
        # pos_size_act < 0.001 = actor soft-skipped this trade (Session 9: POS_SIZE_MIN=0)
        if self._position == 0 and new_dir != 0.0 and pos_size_act >= 0.001:
            entry_fee      = FEE_RATE * self._leverage * pos_size_act
            self._equity  -= entry_fee * self._equity
            step_reward   -= entry_fee

            self._trade_mfe          = 0.0   # fresh tracking for new trade
            self._trade_mae          = 0.0
            self._position           = new_dir
            self._entry_px           = cur_px
            self._pos_size           = pos_size_act
            self._leverage           = 1.0
            self._hold_bars          = 0
            self._max_hold_this_trade = hold_target_act  # agent's chosen timeout for this trade
            self._trail_on           = trail_on_act
            self._trail_peak         = cur_px
            self._sl_atr_mult        = sl_atr_act
            self._trade_atr          = atr_frac

            sl_dist              = sl_atr_act * atr_frac
            tp_dist              = tp_atr_act * atr_frac
            self._sl_price       = cur_px * (1.0 - new_dir * sl_dist)
            self._tp_price       = cur_px * (1.0 + new_dir * tp_dist)
            self._tp_entry_dist  = tp_dist   # Pillar 4: store original TP distance
            self._tp_extensions  = 0
            position_changed = True

        # ── unrealised PnL (dense per-bar reward signal) ──────────────────────
        if self._position != 0:
            bar_pnl_pct  = ((next_px / cur_px) - 1.0) * self._position * self._leverage * self._pos_size
            step_reward += bar_pnl_pct
            # hold patience bonus: reward staying in a winning trade each bar
            if bar_pnl_pct > 0.002:
                step_reward += 0.0003  # was 0.0001 — 3× increase to incentivise holding winners to TP
            self._hold_bars += 1

        # ── reward shaping ────────────────────────────────────────────────────
        if self._chop_idx is not None and position_changed and self._position != 0:
            chop_val = float(self._features.iloc[cur_idx, self._chop_idx])
            if chop_val > 0.7:
                step_reward -= CHOP_PENALTY

        # Trend-alignment: per-bar bonus when aligned, penalty when macro flips
        if self._position != 0 and self._macro_idx is not None and self._regime_idx is not None:
            macro  = float(self._features.iloc[cur_idx, self._macro_idx])
            regime = float(self._features.iloc[cur_idx, self._regime_idx])
            if regime > 0.2:
                sig_dir = 1.0 if macro > 0.2 else (-1.0 if macro < -0.2 else 0.0)
                if sig_dir != 0.0:
                    step_reward += 0.0015 if sig_dir == self._position else -0.0010

        step_reward *= REWARD_SCALE

        # ── advance ───────────────────────────────────────────────────────────
        self._step_idx += 1
        ep_bars    = self._step_idx - self._ep_start_idx
        terminated = (self._step_idx >= self._len - 1 or
                      (self._mode == "train" and ep_bars >= MAX_EPISODE_BARS))
        truncated  = current_dd >= MAX_DRAWDOWN_KILL

        if truncated:
            if self._position != 0:
                trade_mfe_at_close  = self._trade_mfe
                trade_mae_at_close  = self._trade_mae
                trade_hold_at_close = self._hold_bars
                exit_reason         = "kill"
                self._trade_mfe     = 0.0
                self._trade_mae     = 0.0
                self._close_position(cur_px * (1 - 0.01 * self._leverage))
                trade_closed        = True
            step_reward -= 1.0

        obs  = self._get_obs()
        info = {
            "equity":           self._equity,
            "position":         self._position,
            "drawdown":         current_dd,
            "confidence":       1.0,   # kept for train.py logging compat
            "leverage":         self._leverage,
            "step":             self._step_idx,
            "trade_closed":     trade_closed,
            "trade_mfe":        trade_mfe_at_close,   # max favorable excursion (>0)
            "trade_mae":        trade_mae_at_close,   # max adverse excursion (>0)
            "trade_hold_bars":  trade_hold_at_close,  # bars held when closed
            "trade_exit_why":   exit_reason,          # "sl"/"tp"/"dir"/"timeout"/"kill"
        }
        return obs, float(step_reward), terminated, truncated, info

    def render(self):
        pass
