# FinRL_Crypto — System Overview

> A fork/extension of the **FinRL** framework (AI4Finance Foundation), rebuilt specifically for 24/7 cryptocurrency trading using Deep Reinforcement Learning.

---

## Big Libraries & Why Each One Exists

| Library | Role |
|---|---|
| **PyTorch** | Neural network backbone — all actor/critic networks for every DRL algorithm |
| **ElegantRL** | DRL training engine — *local copy* shipped in `core/train/` and `core/drl_agents/`. Provides the training loop, replay buffer, and evaluator. Not installed from PyPI |
| **Optuna** | Bayesian hyperparameter optimization — automatically searches learning rate, batch size, network size, gamma across 50 trials |
| **CCXT** | Universal crypto exchange connector — talks to Binance for live/paper trading |
| **TA-Lib** | C-based technical analysis — computes RSI, DX, OBV, ATR, Bollinger Bands, EMA instantly on large arrays |
| **Flask** | Web dashboard — the `main_controller` serves the pipeline UI so you can launch every phase from a browser |
| **joblib** | Parallel trial execution — multiple training runs at the same time |
| **scipy / statsmodels** | Statistical validation — t-tests, Sharpe confidence intervals, ECDF for PBO |
| **scikit-learn** | KFold cross-validation splits in `optimize_kcv.py` |
| **plotly / matplotlib / seaborn** | Backtest dashboard charts, learning curves, PBO heatmaps |
| **python-binance / yfinance** | Raw data sources — Binance for crypto OHLCV, Yahoo for macro (DXY, SPY, VIX) |

**DRL Algorithms available:** SAC · PPO · TD3 · DDPG · A2C (all from ElegantRL)

---

## Full Pipeline — Phase by Phase

```
Phase 0 → Phase 1 → Phase 2 → Phase 4 → Phase 5
 Data      Train     Validate  Backtest   PBO Check
```

---

### Phase 0 — Data Collection

**What it does:**
Downloads 7+ years of 4h OHLCV candles for BTC + 5 feature tickers (ETH, DXY, SPY, VIX, JPY) from local parquet files. Computes 30 features per timestamp and saves `price_array`, `tech_array`, `time_array` as pickles.

**30 Features breakdown:**
- **14 per-ticker:** `close`, `volume`, `rsi`, `dx`, `ultosc`, `obv`, `atr`, `bband_width`, `ema_ratio`, `log_return` + 4 raw OHLCV columns
- **15 cross-asset:** price ratio, volume ratio, 20-bar return correlation vs each of ETH / DXY / SPY / VIX / JPY
- **1 VIX panic signal:** `vix_log_return`

| Challenge | Solution |
|---|---|
| Raw price is non-stationary — model cannot generalise across time | Use `log_return` and ratio features instead of raw prices |

---

### Phase 1 — Hyperparameter Optimization

**What it does:**
Uses Optuna to run 50 trials. Each trial samples a set of hyperparameters, trains a DRL agent on the training split, evaluates it on the validation split, and reports the **Sharpe ratio** as the objective.

**3 cross-validation strategies available:**

| Script | Strategy | Description |
|---|---|---|
| `optimize_wf.py` | Walk-Forward | Single train/val split |
| `optimize_kcv.py` | K-Fold CV | 5 splits via scikit-learn KFold |
| `optimize_cpcv.py` | **CPCV** | Combinatorial Purged Cross-Validation (López de Prado) — most rigorous |

**What Optuna searches:**
```
learning_rate    batch_size       gamma            net_dimension
target_step      lookback         norm_cash         norm_stocks
norm_tech        norm_reward      norm_action       drawdown_weight
jitter_weight    holding_penalty
```

**Output:** `train_results/{name}/best_trial` + `stored_agent/actor.pth`

| Challenge | Solution |
|---|---|
| Overfitting to one time period | Multiple time splits in CPCV — model must generalise across different market regimes |

---

### Phase 2 — Statistical Validation

**What it does:**
Loads the Optuna study and performs statistical tests on the best trial's Sharpe ratios across all cross-validation splits.

- Computes mean Sharpe ± 95% confidence interval for DRL vs Buy-and-Hold
- Runs **t-test**: is DRL Sharpe statistically significantly better than HODL?
- Generates an interactive HTML dashboard

| Challenge | Solution |
|---|---|
| A single good Sharpe number could be luck | t-test across multiple CV splits shows whether the edge is consistent and reproducible |

---

### Phase 4 — Backtest

**What it does:**
Loads the best trained model and runs it on completely unseen trade data (2024–2026).

1. Loads `actor.pth` + `best_trial` hyperparams
2. Creates `CryptoEnvCCXT` with trade data
3. Runs inference loop: `state → actor.forward() → action → environment.step()`
4. Computes: Sharpe, Sortino, Max Drawdown, Win Rate, Cumulative Return vs Buy-and-Hold
5. Saves interactive dashboard → `phase_4/dashboard/data.js`

> **For deployment:** only `actor.pth` + `best_trial` are needed. Critic, optimisers, and replay buffer are training artefacts and can be discarded.

---

### Phase 5 — PBO (Probability of Backtest Overfitting)

**What it does:**
Uses the CPCV framework to compute the **probability that the best strategy was selected by luck**.

- Based on López de Prado & Bailey's research
- Takes all trial return paths, forms all possible train/test split combinations
- Checks how often the best in-sample trial is also best out-of-sample
- **PBO < 0.5** → model has genuine edge
- **PBO > 0.5** → likely overfit to training data

| Challenge | Solution |
|---|---|
| Great backtest numbers might just be data mining bias | PBO quantifies the probability of overfitting mathematically |

---

### Main Controller — Flask Dashboard

A web UI that ties all phases together. Launch data downloads, training runs, and view backtest dashboards from a browser instead of running scripts manually.

---

## Challenges & Solutions Summary

| # | Challenge | Solution |
|---|---|---|
| 1 | Non-stationary price data | `log_return`, ratio, and cross-asset features instead of raw prices |
| 2 | Overfitting to one time period | CPCV cross-validation across multiple market regimes |
| 3 | Selecting lucky hyperparameters | Optuna Bayesian search over 50 trials, objective = mean CV Sharpe |
| 4 | Edge could be statistical noise | t-test + 95% CI in Phase 2 validation |
| 5 | Backtest overfitting / data mining bias | PBO analysis in Phase 5 |
| 6 | 24/7 crypto markets (no close) | CCXT environment with reduced cooldown logic vs stock version |
| 7 | Reward hacking (too many trades) | Jitter penalty + holding penalty + drawdown penalty in reward shaping |

---

## One-Line Summary

> *FinRL_Crypto uses ElegantRL's SAC/PPO agents trained with Optuna-tuned hyperparameters across CPCV time splits, validated statistically via t-test and PBO, then backtested on live crypto data through a CCXT-powered environment.*
