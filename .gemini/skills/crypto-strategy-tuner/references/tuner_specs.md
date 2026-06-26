# Tuner Specifications

## Classification — Professional Trader Criteria

**You are the classifier. Do NOT use fixed Sharpe thresholds.**
Evaluate the full picture of each strategy before assigning a grade.

### GOOD — Deploy-ready, leave alone
All of the following must be true:
- Sharpe ≥ 1.0 AND in context — a Sharpe of 1.0 in a highly trending 2023 BTC run means less than 1.0 in a ranging market
- Max Drawdown ≤ 35% — beyond this, position sizing makes it undeployable for most account sizes
- Total Trades ≥ 100 — Ernie Chan's reliability benchmark; below this the Sharpe may be statistical noise
- Profit Factor ≥ 1.2 — money in > money out on a per-trade basis
- Win Rate is sensible given the strategy type (e.g. a trend strategy with 30% WR but 3:1 R:R is fine)

### MEDIOCRE — Has potential, worth tuning
One or two weaknesses that optimisation could fix:
- Sharpe 0.3–1.0 with acceptable DD (≤ 40%) and trades ≥ 30
- OR Sharpe ≥ 1.0 but DD is 35–60% (good alpha, bad risk management — params may fix it) and trades ≥ 30
- OR Sharpe ≥ 1.0 but trades 30–99 — statistically thin but above CLT floor; grade_reason must say "low trade count, treat results with caution"
- OR Sharpe 0.3–1.0 with MDD 40–70% and trades ≥ 30 — elevated risk but no BAD threshold triggered; grade_reason must mention MDD risk and paper-trade caution
- OR Profit Factor 1.0–1.2 — marginal edge that tuning might sharpen

### BAD — Broken or no edge
Any of the following disqualifies a strategy:
- Sharpe < 0.3 — no meaningful edge (includes 0.0–0.3 range: positive but too weak to tune)
- Total Return negative over the full scan period
- Total Trades < 30 — below the Central Limit Theorem floor; Sharpe and PF figures are statistically unreliable regardless of their values
- Max Drawdown > 70% — catastrophic, no realistic position size
- Profit Factor < 1.0 — fundamentally losing on every trade

### Key Overrides (apply even if Sharpe looks good)
- If total_trades < 10 → always BAD regardless of Sharpe (pure luck, nothing to tune)
- If max_drawdown > 85% → always BAD regardless of Sharpe (undeployable)
- If profit_factor = 0 → always BAD (means every trade was a loser — no gross wins at all)
- If profit_factor = 99 (displayed as ∞) → all trades were winners, no losers — treat as strong PF (≥ 1.5), do NOT apply BAD override

### Grade Reference Table
| Sharpe Range | Trades | Default Grade | Notes |
|---|---|---|---|
| ≥ 1.0 | ≥ 100 | GOOD (if DD ≤ 35%, PF ≥ 1.2) | Deploy-ready |
| ≥ 1.0 | 30–99 | MEDIOCRE | Statistically thin — low trade count |
| ≥ 1.0 | < 30 | BAD | Below CLT floor — unreliable metrics |
| 0.3–1.0 | ≥ 30 | MEDIOCRE | Worth tuning |
| 0.3–1.0 | < 30 | BAD | Below CLT floor |
| 0.0–0.3 | any | BAD | Positive but no real edge |
| < 0.0 | any | BAD | Losing strategy |

### Grade Display
| Grade | Dashboard | Fine-tune |
|-------|-----------|-----------|
| GOOD | Hidden | No |
| MEDIOCRE | Shown — amber | Yes |
| BAD | Shown — red | Yes (priority) |
| ERROR | Shown — grey | No (fix first) |
| PENDING | Shown — dim | No (awaiting agent) |

---

## Scan Period
Each strategy is scanned using its **own date range from `settings.py`** (`date_from` / `date_to` per STRATEGY_LIBRARY entry).
The CLI fallback (for strategies with no date configured) is `2021-01-01 → 2026-05-31`.

Do NOT pass `--date_from` / `--date_to` overrides unless explicitly requested — let each strategy use its own period.

---

## Default Fine-tune Trials
Trials are **auto-scaled** by the script: `max(100, n_tunable_params × 25)`.
- 9 tunable params → 225 trials automatically
- 4 tunable params → 100 trials automatically
- Do NOT pass `--trials` unless you need to override (e.g. quick test with `--trials 50`).
- The old fixed values (30 = fast, 100 = deep) are no longer used — auto-scaling always produces better results.

---

## Escalation Rules
- If a strategy returns `ERROR` grade → send HIGH inbox to `@crypto-fullstack` with the error message
- If fine-tune result **Sharpe > original Sharpe** → `finetune.py` automatically updates `settings.py` + strategy file (best known params always saved)
- If fine-tune result **Sharpe ≤ original** → `finetune.py` keeps original params (no update)
- If fine-tune result **Sharpe ≥ 1.0** → send `FINETUNE_PROMOTED` inbox to `@alpha-researcher`

---

## Parameter Search Ranges
These are the ranges used by `finetune.py`. Any strategy param NOT in this list is kept fixed.
Grouped by indicator type for easy reference.

### Generic
| Parameter | Min | Max |
|---|---|---|
| period | 5 | 50 |
| length | 5 | 50 |
| lookback | 5 | 50 |
| smoothing | 2 | 20 |

### MACD
| Parameter | Min | Max |
|---|---|---|
| fast | 3 | 30 |
| slow | 15 | 100 |
| signal | 3 | 20 |
| macd_fast | 3 | 30 |
| macd_slow | 15 | 100 |
| macd_signal | 3 | 20 |
| fast_period | 3 | 30 |
| slow_period | 15 | 100 |

### KDJ
| Parameter | Min | Max |
|---|---|---|
| kdj_period | 5 | 30 |
| kdj_oversold | 10 | 40 |
| kdj_overbought | 60 | 90 |

### RSI / V-RSI
| Parameter | Min | Max |
|---|---|---|
| rsi_period | 5 | 30 |
| rsi_window | 5 | 30 |
| rsi_oversold | 20 | 40 |
| rsi_overbought | 60 | 80 |
| rsi_low | 20 | 40 |
| rsi_high | 60 | 80 |
| rsi_threshold | 30 | 70 |
| vrsi_period | 5 | 30 |
| vrsi_oversold | 15 | 35 |
| vrsi_overbought | 65 | 85 |

### EMA / SMA
| Parameter | Min | Max |
|---|---|---|
| ema_fast | 5 | 30 |
| ema_slow | 20 | 200 |
| ema_med | 10 | 60 |
| ema_period | 10 | 200 |
| ema_trend | 50 | 300 |
| ema_trend_4h | 50 | 300 |
| ema_window | 5 | 50 |
| ema_speed_period | 3 | 20 |
| trend_ema_period | 50 | 300 |
| sma_period | 5 | 50 |
| sma_macro | 50 | 300 |
| sma_macro_period | 50 | 300 |
| major_period | 10 | 50 |
| minor_period | 5 | 30 |

### ADX
| Parameter | Min | Max |
|---|---|---|
| adx_period | 7 | 30 |
| adx_threshold | 15 | 40 |
| adx_threshold_1h | 15 | 40 |
| adx_threshold_4h | 15 | 40 |

### ATR / Multipliers
| Parameter | Min | Max |
|---|---|---|
| atr_period | 5 | 30 |
| atr_multiplier | 1.0 | 6.0 |
| atr_multiplier_sl | 0.5 | 3.0 |
| atr_multiplier_tp | 1.0 | 8.0 |
| multiplier | 1.0 | 6.0 |
| multiplier_l1 | 0.5 | 3.0 |
| multiplier_l2 | 0.5 | 3.0 |
| multiplier_l3 | 0.5 | 3.0 |
| tp_atr_mult | 1.0 | 8.0 |
| sl_atr_mult | 0.5 | 3.0 |
| sl_atr_multiplier | 0.5 | 3.0 |
| sl_multiplier | 0.5 | 3.0 |
| tp_multiplier | 1.0 | 8.0 |
| kc_multiplier | 1.0 | 4.0 |
| st_multiplier | 1.0 | 5.0 |
| supertrend_multiplier | 1.0 | 5.0 |

### Bollinger Bands / Keltner
| Parameter | Min | Max |
|---|---|---|
| bb_period | 10 | 50 |
| bb_std | 1.0 | 3.5 |
| bbw_sma_period | 10 | 50 |
| kc_window | 10 | 50 |
| kc_atr_window | 5 | 30 |
| squeeze_period | 10 | 30 |

### VWAP
| Parameter | Min | Max |
|---|---|---|
| vwap_period | 10 | 100 |
| vwap_std_mult | 0.5 | 3.0 |

### Other Indicators
| Parameter | Min | Max |
|---|---|---|
| fvma_period | 3 | 20 |
| st_period | 5 | 30 |
| supertrend_length | 5 | 30 |
| zlema_period | 5 | 50 |
| zscore_period | 20 | 200 |
| zscore_threshold | 0.5 | 3.0 |
| z_period | 10 | 100 |
| z_threshold | 0.5 | 3.0 |
| aroon_period | 10 | 50 |
| aroon_threshold | 50 | 80 |
| mfi_period | 5 | 30 |
| wt_n1 | 5 | 20 |
| wt_n2 | 10 | 50 |
| pivot_window | 5 | 30 |
| cvd_window | 5 | 50 |
| divergence_lookback | 5 | 30 |
| vol_lookback | 5 | 50 |
| vol_ma_period | 5 | 50 |
| vol_sma_period | 5 | 50 |
| intensity_period | 5 | 30 |
| intensity_std | 1.0 | 3.0 |
| pullback_lookback | 2 | 10 |
| swing_lookback | 5 | 30 |

### Taker / Order Flow
| Parameter | Min | Max |
|---|---|---|
| taker_threshold | 0.5 | 0.7 |
| taker_ratio_threshold | 0.5 | 0.7 |
| taker_high_threshold | 0.5 | 0.75 |
| taker_low_threshold | 0.3 | 0.55 |
| ob_volume_mult | 1.0 | 3.0 |

### FVG / Gap
| Parameter | Min | Max |
|---|---|---|
| fvg_min_pct | 0.001 | 0.05 |
| min_gap_pct | 0.001 | 0.05 |

### SL / TP / Position Management
| Parameter | Min | Max |
|---|---|---|
| sl_pct | 0.005 | 0.05 |
| stop_loss_pct | 0.01 | 0.10 |
| take_profit_pct | 0.02 | 0.20 |
| tp_pct | 0.01 | 0.15 |
| tp_rr | 1.0 | 5.0 |
| tp_rr_ratio | 1.0 | 5.0 |
| rv_threshold | 0.01 | 0.10 |
| vol_threshold | 0.5 | 3.0 |
| vol_multiplier | 1.0 | 3.0 |
| deviation_pct | 0.005 | 0.05 |
| ema_slope_thresh | 0.0 | 2.0 |
| sl_z_threshold | 0.5 | 3.0 |
| touch_band | 0.001 | 0.02 |
| max_hold_bars | 12 | 200 |
| entry_window | 1 | 20 |
| peak_retrace_pct | 0.3 | 0.9 |
| retrace_depth | 0.3 | 0.9 |
| low_lookback | 5 | 50 |

### WAE
| Parameter | Min | Max |
|---|---|---|
| wae_sensitivity | 50 | 300 |
| wae_fast_len | 5 | 30 |
| wae_slow_len | 20 | 80 |
| wae_bb_len | 10 | 50 |
| wae_bb_mult | 1.0 | 3.0 |
| wae_deadzone | 5 | 50 |

### T3 / Stiff / TII
| Parameter | Min | Max |
|---|---|---|
| t3_length | 5 | 50 |
| t3_vf | 0.1 | 1.0 |
| stiff_len | 20 | 100 |
| stiff_threshold | 0.5 | 1.0 |
| tii_lower | 20 | 45 |
| tii_upper | 55 | 80 |

---

## Strategy Classes in `strategy_backtest/strategies/`
See `strategy_backtest/settings.py` for the full STRATEGY_LIBRARY with numeric IDs.
