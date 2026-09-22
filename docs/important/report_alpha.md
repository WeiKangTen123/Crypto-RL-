# Alpha Factor Feasibility & Implementation Report

This document reviews the 101 Fully Adaptable Alphas (symbolic factors) and the PDF factor extractions, categorized by their implementability within the `Crypto-RL` backtest architecture.

**Legend:**
- **[IMPLEMENTED]**: Currently coded in `library.py` or available natively via the strategy framework (e.g. `PortfolioBacktestEngine`).
- **[YES - EASY]**: Simple math/pandas operations, completely supported by the OHLCV structure.
- **[YES - MEDIUM]**: Requires intermediate pandas (rolling correlations, custom grouping) or cross-sectional logic, fully supported by `PortfolioBacktestEngine`.
- **[HARD/NO]**: Requires off-chain data (macro events, funding rates, alternative datasets), heavy machine learning (LLM, CNN), or complex non-linear optimization algorithms (NLS).

---

## 1. Fully Adaptable Alphas (WorldQuant Style)

| # | Core Idea | Feasibility | Status | Implementation Notes |
|---|---|---|---|---|
| 1 | Volatility regime reversal signal | [IMPLEMENTED] | **IMPLEMENTED** | Uses `np.where` and rolling std dev. |
| 2 | Volume-change momentum anti-corr | [IMPLEMENTED] | **IMPLEMENTED** | `df.vol.diff().rolling().corr(price_change)` |
| 3 | Open-volume anticorrelation | [IMPLEMENTED] | **IMPLEMENTED** | Basic rank correlation. |
| 4 | Low rank mean-reversion | [IMPLEMENTED] | **IMPLEMENTED** | Time-series rank is easily done via `pd.Series.rank`. |
| 5 | VWAP distance × volume delta | [IMPLEMENTED] | **IMPLEMENTED** | Requires VWAP and ranking. |
| 6 | Open-volume correlation fade | [IMPLEMENTED] | **IMPLEMENTED** | Simple rolling correlation. |
| 7 | Volume surge momentum fade | [IMPLEMENTED] | **IMPLEMENTED** | Conditional logic on volume spikes. |
| 8 | Momentum cross-term reversal | [IMPLEMENTED] | **IMPLEMENTED** | Rolling sums and delays. |
| 9 | Close delta conditional flip | [IMPLEMENTED] | **IMPLEMENTED** | `np.where` on rolling min/max. |
| 10 | Ranked conditional close delta | [IMPLEMENTED] | **IMPLEMENTED** | Rank applied to Alpha #9. |
| 11 | VWAP deviation × volume rank | [IMPLEMENTED] | **IMPLEMENTED** | VWAP is implemented; needs min/max rolling. |
| 12 | Volume-close anti-momentum | YES - EASY | [IMPLEMENTED] | `np.sign(vol.diff()) * -close.diff()` |
| 13 | Volume covariance fade | [IMPLEMENTED] | **IMPLEMENTED** | Rank covariance. |
| 14 | Volume-return anti-correlation fade | [IMPLEMENTED] | **IMPLEMENTED** | Uses percentage returns. |
| 15 | High-volume 3-corr cascade | YES - MEDIUM | Pending | Nested correlations. |
| 16 | High-volume covariance fade | YES - MEDIUM | Pending | Rank covariance between High and Vol. |
| 17 | Triple-interaction momentum | YES - MEDIUM | Pending | TS Rank and Delta combinations. |
| 18 | Intrabar volatility + open-close | YES - MEDIUM | Pending | Intrabar range and correlation. |
| 19 | Long-term return momentum fade | YES - MEDIUM | Pending | Uses 250-day lookback sums. |
| 20 | Three-way gap reversal | YES - MEDIUM | Pending | Open-Delay differences. |
| 21 | Volatility-regime adaptive | YES - MEDIUM | Pending | Regime filters on SMA/std. |
| 22 | Correlation decay × volatility | YES - MEDIUM | Pending | Delta of correlation times std dev. |
| 23 | High MA vs current high | YES - EASY | Pending | `np.where` on SMA. |
| 24 | SMA drift vs price lag | YES - MEDIUM | Pending | Long-term SMA drift calculation. |
| 25 | Return-volume-VWAP cross | YES - MEDIUM | Pending | Multi-feature multiplication. |
| 26 | Volume-high correlation decay | YES - MEDIUM | Pending | Rolling max of correlation. |
| 27 | Volume-VWAP correlation gate | YES - MEDIUM | Pending | Binary conditional on VWAP correlation. |
| 28 | Adv-low mean-revert + close | YES - EASY | Pending | Easy scalar math. |
| 29 | Extreme nested rank decay | HARD | Pending | Overly complex/prone to overfitting. |
| 30 | Volume-weighted bar-direction | YES - MEDIUM | Pending | Requires volume ratios and sign sums. |
| 31 | Rank decay cascade | HARD | Pending | Decay-linear implementation needed. |
| 32 | SMA distance + VWAP corr lag | YES - MEDIUM | Pending | SMA and VWAP correlation. |
| 33 | Open-close ratio rank | YES - EASY | Pending | Simple `rank(1 - (open/close))`. |
| 34 | Return vol ratio + close delta | YES - EASY | Pending | Ratio of rolling standard deviations. |
| 35 | Triple ts_rank momentum | YES - MEDIUM | Pending | Triple time-series ranking. |
| 36 | Weighted multi-factor alpha | YES - MEDIUM | Pending | Multi-factor linear combination. |
| 37 | Gap corr + open-close | YES - MEDIUM | Pending | Correlation with lag. |
| 38 | Close-open ratio momentum | YES - EASY | Pending | Simple rank of ratios. |
| 39 | Delta decay fade × momentum | HARD | Pending | Requires `decay_linear` function. |
| 40 | High volatility corr fade | YES - MEDIUM | Pending | Rank of rolling standard deviation. |
| 41 | Geometric mean - VWAP | YES - EASY | Pending | `np.sqrt(high*low) - vwap`. |
| 42 | VWAP distance ratio | YES - EASY | [IMPLEMENTED] | Extremely easy and elegant ranking. |
| 43 | Vol-rank momentum decay | YES - MEDIUM | Pending | Cross-term TS ranking. |
| 44 | High-volume anticorr | YES - EASY | Pending | Negative correlation function. |
| 45 | Close-volume multi-corr | YES - MEDIUM | Pending | Nested rolling correlations. |
| 47 | Complex vol-rank expression | HARD | Pending | Heavy multi-rank expressions. |
| 49 | SMA drift reversal gate | YES - MEDIUM | Pending | Conditional on MA diffs. |
| 50 | Vol-VWAP corr max fade | YES - MEDIUM | Pending | Max of correlation rank. |
| 51 | SMA drift reversal (tighter) | YES - MEDIUM | Pending | Same as 49 with tighter params. |
| 52 | Low-min momentum cascade | YES - MEDIUM | Pending | Rolling minimums and delays. |
| 54 | Intrabar geometric ratio | YES - EASY | Pending | Pure OHLC math. |
| 55 | %B-ranked anticorr | YES - MEDIUM | Pending | Normalized range correlation. |
| 57 | VWAP decay negation | HARD | Pending | Requires `decay_linear`. |
| 60 | Complex volume scalar | HARD | Pending | Heavy scaling arrays. |
| 83 | NLS-fitted multi-term | HARD | Pending | Requires Non-linear least squares fit. |
| 84 | SignedPower + ts_rank decay | HARD | Pending | Signed power transformations. |
| 88 | Min of two decay chains | HARD | Pending | Double `decay_linear`. |
| 92 | Min of two ts_rank decays | HARD | Pending | Conditional decay logic. |
| 99 | Ranked corr gate | YES - MEDIUM | Pending | Correlation rank comparisons. |
| 101 | OHLC gap ratio | YES - EASY | Pending | `(close-open) / (high-low+0.001)`. |

---

## 2. Research PDF Factor Extractions

### 1. IFF 2024 Digital Currencies Report
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| CBECI Hashrate proxy | NO | N/A | Requires on-chain/API difficulty data. |
| Scalability/Congestion Signal | YES - MEDIUM | Pending | Volume-price elasticity proxy. |
| Volatility Regime Indicator | YES - EASY | Pending | 30/90-day RV ratio. |
| DeFi Adoption Index Proxy | YES - MEDIUM | Pending | `PortfolioBacktestEngine` Alt/BTC volume ratio. |
| Regulatory Shock Event Flag | HARD | N/A | Requires external event calendar. |
| ECDSA Vulnerability Tracker | NO | N/A | Exclusively off-chain news driven. |

### 2. Deep Learning / LLMs Survey (Cao et al.)
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Transfer Entropy | HARD | Pending | Computationally expensive for simple vectorization. |
| CMIN Causal Graph | HARD | Pending | Requires multi-timescale TE. |
| PCA Residual (Symbolic) | YES - MEDIUM | Pending | Available via `PortfolioBacktestEngine` cross-sectional PCA. |
| CNN Pattern Recognition | HARD | Pending | Needs PyTorch/TF inference loop. |
| Almgren-Chriss Market Impact | YES - MEDIUM | Pending | Liquidity-adjusted sizing via volume rank. |
| CVaR-based Tail Risk | YES - MEDIUM | Pending | Historical CVaR calculation via rolling quantiles. |

### 3. Bitcoin ETF Event Study
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| CAR Event Study | HARD | N/A | Requires known catalyst dates. |
| Volume Persistence (Wiki Proxy) | YES - EASY | Pending | Rolling 90-day volume slope. |
| Rolling Sharpe Break | YES - MEDIUM | Pending | Rolling Sharpe + CUSUM. |
| Rolling Beta to BTC | YES - MEDIUM | Pending | Cross-asset beta (available in multi-coin engine). |
| Google Trends (Vol Proxy) | YES - EASY | Pending | `Vol_t / Vol_MA90` ratio. |
| Daily Range Regime | YES - EASY | Pending | Rolling `(high - low) / close`. |

### 4. Financial ML in Emerging Markets
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Amihud Illiquidity Ratio | [IMPLEMENTED] | **IMPLEMENTED** | Coded as `calc_amihud_illiq` in `library.py`. |
| Realized Volatility Ratio | YES - EASY | Pending | `RV_5 / RV_20` |
| 5-Component Market Stress Index | YES - MEDIUM | Pending | Z-scores of RV, Illiq, Corr, Vol. |
| Quantile Regression (Asymmetric) | HARD | Pending | Requires rolling `statsmodels` quantile regression. |
| SHAP Feature Importance | HARD | Pending | Heavy compute for XGBoost on every window. |

### 5. Settlement Ether (Vince)
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Hash Chain Depth Proxy | YES - EASY | Pending | Log of cumulative volume. |
| O(log n) Verification Proxy | YES - EASY | Pending | Volatility compression / Spread narrowing. |

### 6. CAICT Digital Economy 2025
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Global Digital Vitality Index | NO | N/A | Pure macro, off-OHLCV. |
| Mining Difficulty Momentum | NO | N/A | Requires on-chain metrics unless volume-proxied. |
| Rate-Sensitivity Factor | HARD | N/A | Needs FOMC calendar dates. |

### 7. Korean Crypto Market (Presto)
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Kimchi Premium (FOMO Proxy) | YES - EASY | [IMPLEMENTED] | `corr(Vol_change, Price_change)` |
| Listing Pump Fade | YES - MEDIUM | Pending | Detect massive gap opens (>15%) + extreme volume. |
| Upbit Vol Dominance | YES - MEDIUM | Pending | Altcoin/BTC volume ratio. |
| Speculative Preference Ratio | YES - MEDIUM | [IMPLEMENTED] | Handled natively by Portfolio cross-sectional capabilities. |
| Retail Momentum Decay | YES - EASY | Pending | Short 5-day return after 20% 3-day spike. |

### 8. Pairs Trading (de Vries)
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Pearson Corr Filter (≥ 0.8) | YES - MEDIUM | Pending | Handled by `PortfolioBacktestEngine`. |
| Z-score Spread | [IMPLEMENTED] | **IMPLEMENTED** | `calc_zscore` exists in `library.py`. |
| Sum of Squared Differences (SSD)| YES - MEDIUM | Pending | Easy cross-sectional tracking. |
| OLS Cointegration | YES - MEDIUM | Pending | Statsmodels ADF test on rolling window. |
| Skewness & Kurtosis | YES - EASY | Pending | Rolling skew/kurt via pandas. |
| Sortino Tail-Adjust | YES - EASY | Pending | Rolling downside deviation. |

### 9. Multifractal Post-COVID
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Hurst Exponent (H) | [IMPLEMENTED] | **IMPLEMENTED** | Rolling Detrended Fluctuation Analysis (DFA) proxy on volume. |
| Generalized Hurst h(q) | HARD | Pending | Complex multi-scale DFA. |
| Volume/Tx Pearson Proxy | YES - EASY | Pending | `corr(Volume, Volume/Close)` |
| Cross-Return BTC/ETH Regime | YES - MEDIUM | Pending | Rolling correlation BTC/ETH. |
| Volume Leading Price | YES - MEDIUM | Pending | Rolling OLS slope of volume. |

### 10. Time-Series Deep Learning
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Ornstein-Uhlenbeck κ | [IMPLEMENTED] | **IMPLEMENTED** | Coded as `calc_ou_mr_speed` in `library.py`. |
| Generalized PCA Residual | YES - MEDIUM | Pending | Multi-asset PCA. |
| Cross-Scale MA (Scaleformer) | YES - EASY | [IMPLEMENTED] | Cross-scale agreements (5d, 10d, 20d, 60d). |
| Seasonal Decompose (Autoformer)| YES - MEDIUM | Pending | Residual from `price - MA_14`. |
| Max Drawdown (MDD) Sizing | YES - EASY | Pending | Dynamic sizing based on rolling MDD. |

### 11. LLM Sentiment Equity
| Factor | Feasibility | Status | Notes |
|---|---|---|---|
| Candle Sentiment Index | YES - EASY | [IMPLEMENTED] | (POS_days - NEG_days) / N, 20d. |
| Rank-Based Portfolio | [IMPLEMENTED] | **IMPLEMENTED** | Core architecture of `RelativeMomentumRank` strategy `196`. |
| Minimum Coverage Filter | YES - EASY | Pending | Volume > 50th percentile threshold. |
| Alpha Separation (CAPM Beta) | YES - MEDIUM | Pending | Rolling beta to BTC. |
