"""
Strategy library for the Crypto-RL technical backtest module.

Data is loaded from: Crypto-RL/dataset/{coin}/{timeframe}/spot_ohlcv.parquet
(same parquet files used by the DRL training pipeline).
"""

import os

# Path to the shared dataset (one level above this file's package root)
DATASET_DIR = os.path.join(os.path.dirname(__file__), '..', 'dataset')

# --- Optimizer Settings ---
OPTIMIZER_SETTINGS = {
    "n_workers": os.cpu_count(),
    "top_n": 10,
    "min_trades": 5,
    "primary_objective": "Sharpe Ratio",
    "output_csv": "optimize/results.csv",
}

STRATEGY_LIBRARY = {
    "246": {
        "id": "CusumSharpeBreakout",
        "desc": "CUSUM Sharpe Breakout (Regime Shift Detector)",
        "class": "CusumSharpeBreakout",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "sharpe_window": 20, "cusum_thresh": 1.0, "sl_pct": 0.08, "tp_pct": 0.3
        },
    },
    "245": {
        "id": "CapmAlphaSeparation",
        "desc": "CAPM Alpha Separation (Idiosyncratic Alpha Tracker)",
        "class": "CapmAlphaSeparation",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "beta_window": 50, "alpha_z_window": 50, "alpha_thresh": 3.0, "sl_pct": 0.05, "tp_pct": 0.2
        },
    },
    "244": {
        "id": "CminCausalGraph",
        "desc": "CMIN Causal Graph (Lead-Lag Network)",
        "class": "CminCausalGraph",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "window": 200, "leader_trend_p": 20, "follower_thresh": 0.2, "sl_pct": 0.08, "tp_pct": 0.1
        },
    },
    "243": {
        "id": "GrangerTEProxy",
        "desc": "Transfer Entropy (Granger Causality Proxy)",
        "class": "GrangerTEProxy",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "window": 50, "te_thresh": 0.3, "trend_window": 10, "sl_pct": 0.15, "tp_pct": 0.3
        },
    },
    "242": {
        "id": "WalkForwardRF",
        "desc": "Walk-Forward Random Forest Machine Learning (SHAP Proxy)",
        "class": "WalkForwardRF",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "train_window": 2000, "retrain_interval": 100, "n_estimators": 10, "max_depth": 5, "prob_thresh": 0.55, "sl_pct": 0.15, "tp_pct": 0.15
        },
    },
    "241": {
        "id": "FractalVarianceRatio",
        "desc": "Fractal Variance Ratio (Hurst Exponent Proxy)",
        "class": "FractalVarianceRatio",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "window": 100, "q1": 15, "q2": 30, "q3": 80, "trend_thresh": 1.1, "trend_lookback": 20, "sl_pct": 0.05, "tp_pct": 0.3
        },
    },
    "240": {
        "id": "MarketStressIndex",
        "desc": "5-Component Market Stress Index (Financial ML)",
        "class": "MarketStressIndex",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "window": 50, "z_period": 500, "long_thresh": 7.0, "short_thresh": -5.0, "sl_pct": 0.05, "tp_pct": 0.15
        },
    },
    "239": {
        "id": "TripleTsRank",
        "desc": "Triple TS Rank Momentum (WorldQuant Alpha #35)",
        "class": "TripleTsRank",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vol_p": 15, "bp_p": 50, "ret_p": 100, "long_thresh": 0.8, "short_thresh": 0.2, "sl_pct": 0.05, "tp_pct": 0.3
        },
    },
    "238": {
        "id": "CorrelationMatrixGate",
        "desc": "Correlation Matrix Gate (WorldQuant Alpha #74)",
        "class": "CorrelationMatrixGate",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "adv_p": 15, "sum_p": 20, "corr_left_p": 20, "corr_right_p": 15, "blend_ratio": 0.1, "sl_pct": 0.15, "tp_pct": 0.2
        },
    },
    "237": {
        "id": "ExtremeNestedDecay",
        "desc": "Extreme Nested Rank Decay (WorldQuant Alpha #29)",
        "class": "ExtremeNestedDecay",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "left_delta_p": 7, "left_ts_p": 3, "right_decay_p": 10, "long_thresh": 0.6, "short_thresh": 0.3, "sl_pct": 0.08, "tp_pct": 0.3
        },
    },
    "236": {
        "id": "RankDecayCascade",
        "desc": "Rank Decay Cascade (WorldQuant Alpha #31)",
        "class": "RankDecayCascade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "long_delta_p": 15, "decay_p": 15, "short_delta_p": 2, "long_thresh": 1.9, "short_thresh": 0.6, "sl_pct": 0.03, "tp_pct": 0.3
        },
    },
    "235": {
        "id": "DeltaDecayFade",
        "desc": "Delta Decay Fade × Momentum (WorldQuant Alpha #39)",
        "class": "DeltaDecayFade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "adv_p": 20, "decay_p": 30, "delta_p": 14, "macro_p": 1000, "long_thresh": -0.2, "short_thresh": -1.0, "sl_pct": 0.03, "tp_pct": 0.1
        },
    },
    "234": {
        "id": "VWAPSignedPower",
        "desc": "SignedPower VWAP Momentum (WorldQuant Alpha #84)",
        "class": "VWAPSignedPower",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vwap_max_p": 15, "ts_rank_p": 60, "delta_p": 10, "long_thresh": 1.2, "short_thresh": 0.9, "sl_pct": 0.15, "tp_pct": 0.2
        },
    },
    "233": {
        "id": "MinDecayChains",
        "desc": "Min of Two Decay Chains (WorldQuant Alpha #92)",
        "class": "MinDecayChains",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "cond_decay_p": 30, "cond_tsrank_p": 50, "adv_p": 10, "corr_p": 14, "corr_decay_p": 6, "corr_tsrank_p": 6,
            "long_thresh": 0.8, "short_thresh": 0.3, "sl_pct": 0.05, "tp_pct": 0.2
        },
    },
    "232": {
        "id": "ComplexVolumeScalar",
        "desc": "Complex Volume Scalar (WorldQuant Alpha #60)",
        "class": "ComplexVolumeScalar",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "p1": 25, "long_thresh": 0.1, "short_thresh": -0.25, "sl_pct": 0.04, "tp_pct": 0.1
        },
    },
    "231": {
        "id": "RollingQuantileRegression",
        "desc": "Rolling Asymmetric Quantile Regression (Deep Learning / ML Factor)",
        "class": "RollingQuantileRegression",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "lookback": 100, "step_size": 24, "q_lower": 0.05, "q_upper": 0.95, "asym_thresh": 3.0,
            "sl_pct": 0.1, "tp_pct": 0.2
        },
    },
    "230": {
        "id": "ComplexVolRankMomentum",
        "desc": "Complex Vol-Rank VWAP Momentum (WorldQuant Alpha #47)",
        "class": "ComplexVolRankMomentum",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "adv_p": 200, "sma_p": 200, "delay_p": 50,
            "long_thresh": 0.9, "short_thresh": 0.6, "sl_pct": 0.15, "tp_pct": 0.2
        },
    },
    "229": {
        "id": "VwapDecayNegation",
        "desc": "VWAP Decay Negation (WorldQuant Alpha #57)",
        "class": "VwapDecayNegation",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "p1": 300, "p2": 100,
            "long_thresh": 0.6, "short_thresh": 0.5, "sl_pct": 0.2, "tp_pct": 0.5
        },
    },
    "228": {
        "id": "DoubleDecayMin",
        "desc": "Double Decay Chain Minimum (WorldQuant Alpha #88)",
        "class": "DoubleDecayMin",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2021-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "p1": 10, "p2": 50, "p3": 50, "p4": 30, "p5": 10, "adv_p": 5,
            "long_thresh": 0.4, "short_thresh": 0.5, "sl_pct": 0.15, "tp_pct": 0.3
        },
    },
    "227": {
        "id": "DecayLinearMomentum",
        "desc": "Delta Decay Fade x Momentum (WorldQuant Alpha #39)",
        "class": "DecayLinearMomentum",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 30, "decay_p": 3, "adv_p": 200, "ret_sum_p": 250,
            "long_thresh": 0.9, "short_thresh": 0.5, "sl_pct": 0.01, "tp_pct": 0.2
        },
    },
    "226": {
        "id": "Return_Vol_Ratio",
        "desc": "Return Vol Ratio + Close Delta (WorldQuant Alpha #34)",
        "class": "ReturnVolRatio",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "short_vol_p": 10, "long_vol_p": 100, "long_thresh": 0.6, "short_thresh": -0.6,
            "sl_pct": 0.1, "tp_pct": 0.2
        },
    },
    "225": {
        "id": "Ohlc_Gap_Ratio",
        "desc": "OHLC gap ratio (WorldQuant Alpha #101)",
        "class": "OhlcGapRatio",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "long_thresh": 0.95, "short_thresh": -0.7,
            "sl_pct": 0.05, "tp_pct": 0.2
        },
    },
    "224": {
        "id": "Close_Open_Ratio_Mom",
        "desc": "Close-open ratio momentum (WorldQuant Alpha #38)",
        "class": "CloseOpenRatioMom",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rank_p": 50, "long_thresh": 0.95, "short_thresh": 0.3,
            "sl_pct": 0.15, "tp_pct": 0.2
        },
    },
    "223": {
        "id": "Open_Close_Ratio_Rank",
        "desc": "Open-close ratio rank (WorldQuant Alpha #33)",
        "class": "OpenCloseRatioRank",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rank_p": 5, "long_thresh": 0.6, "short_thresh": 0.05,
            "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "222": {
        "id": "Vol_Close_Anti_Mom",
        "desc": "Volume-close anti-momentum (WorldQuant Alpha #12)",
        "class": "VolCloseAntiMom",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 1, "long_thresh": 20.0, "short_thresh": -20.0,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "221": {
        "id": "Geom_Mean_Vwap",
        "desc": "Geometric mean - VWAP (WorldQuant Alpha #41). Sharpe +0.66, ROI +10.2%, MDD 6.5%, 176 trades (MEDIOCRE). PF=1.06.",

        "class": "GeomMeanVwap",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "long_thresh": 50.0, "short_thresh": -20.0,
            "sl_pct": 0.08, "tp_pct": 0.1
        },
    },
    "220": {
        "id": "Adv_Low_Mean_Revert",
        "desc": "Adv-low mean-revert + close (WorldQuant Alpha #28). Sharpe -0.09, ROI -5.0%, MDD 17.4%, 604 trades (BAD). PF=1.12.",

        "class": "AdvLowMeanRevert",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "adv_p": 40, "corr_p": 5, "long_thresh": 0.1, "short_thresh": -0.5,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "219": {
        "id": "Close_Return_Cond_Gap",
        "desc": "Close-return conditional gap (WorldQuant Alpha #19). Sharpe +0.26, ROI +7.8%, MDD 18.2%, 397 trades (BAD). PF=0.94.",

        "class": "CloseReturnCondGap",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 7, "sum_p": 20, "rank_p": 10, "long_thresh": 0.8, "short_thresh": -0.5,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "218": {
        "id": "Stddev_Gap_Cross",
        "desc": "Standard deviation gap cross (WorldQuant Alpha #18). Sharpe +0.51, ROI +43.7%, MDD 41.6%, 332 trades (MEDIOCRE). PF=1.56.",

        "class": "StddevGapCross",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "std_p": 3, "ts_p": 5, "rank_p": 5, "long_thresh": -0.5, "short_thresh": -1.5,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "217": {
        "id": "High_Vol_3Corr_Cascade",
        "desc": "High-volume 3-corr cascade (WorldQuant Alpha #15). Sharpe -0.49, ROI -45.1%, MDD 67.7%, 299 trades (BAD). PF=0.70.",

        "class": "HighVol3CorrCascade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "corr_p": 10, "sum_p": 5, "rank_p": 5, "long_thresh": -1.0, "short_thresh": -2.5,
            "sl_pct": 0.08, "tp_pct": 0.1
        },
    },
    "216": {
        "id": "Vol_Return_Anticorr_Fade",
        "desc": "Vol-return anticorr fade (WQ Alpha #14) — -rank(delta(returns,3)) * corr(open,vol,10). Sharpe +1.28, ROI +96.0%, MDD 20.1%, 351 trades (BAD). PF=0.98.",

        "class": "VolReturnAnticorrFade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 5, "corr_p": 20, "rank_p": 5, "long_thresh": 0.6, "short_thresh": -0.4,
            "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "215": {
        "id": "Volume_Covariance_Fade",
        "desc": "Volume covariance fade (WQ Alpha #13) — -rank(cov(rank(close),rank(vol),5)). Sharpe -0.39, ROI -38.6%, MDD 62.0%, 698 trades (BAD). PF=0.62.",

        "class": "VolumeCovarianceFade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "cov_p": 10, "rank_p": 5, "long_thresh": -0.2, "short_thresh": -0.8,
            "sl_pct": 0.03, "tp_pct": 0.1
        },
    },
    "214": {
        "id": "VWAP_Deviation_Vol_Rank",
        "desc": "VWAP deviation × vol rank (WQ Alpha #11) — (rank(ts_max(vwap-close,3))+rank(ts_min(vwap-close,3)))*rank(delta(vol,3)). Sharpe +0.11, ROI +1.1%, MDD 29.4%, 669 trades (BAD). PF=0.90.",

        "class": "VWAPDeviationVolRank",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ts_p": 5, "rank_p": 10, "long_thresh": 1.5, "short_thresh": 0.4,
            "sl_pct": 0.05, "tp_pct": 0.15
        },
    },
    "213": {
        "id": "Ranked_Conditional_Close_Delta",
        "desc": "Ranked conditional close delta (WQ Alpha #10) — rank(Alpha#9 conditional flip). Sharpe +0.51, ROI +43.9%, MDD 42.6%, 331 trades (MEDIOCRE). PF=1.66.",

        "class": "RankedConditionalCloseDelta",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 2, "ts_p": 3, "rank_p": 5, "long_thresh": 0.7, "short_thresh": 0.2,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "212": {
        "id": "Close_Delta_Conditional_Flip",
        "desc": "Close delta conditional flip (WQ Alpha #9) — momentum in trends, fade in ranges. Sharpe +0.22, ROI +7.2%, MDD 31.8%, 512 trades (BAD). PF=0.98.",

        "class": "CloseDeltaConditionalFlip",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 1, "ts_p": 3, "long_thresh": 0.03, "short_thresh": -0.01,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "211": {
        "id": "Momentum_Cross_Term_Reversal",
        "desc": "Momentum cross-term reversal (WQ Alpha #8) — -rank(2*rank(corr(ts_rank(close),ts_rank(vol)))-rank(delta(close))). Sharpe +0.93, ROI +42.6%, MDD 16.1%, 518 trades (MEDIOCRE). PF=1.12.",

        "class": "MomentumCrossTermReversal",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ts_p": 10, "corr_p": 5, "delta_p": 5, "rank_p": 20, "long_thresh": -0.2, "short_thresh": -0.8,
            "sl_pct": 0.05, "tp_pct": 0.15
        },
    },
    "210": {
        "id": "Vol_Surge_Momentum_Fade",
        "desc": "Vol surge momentum fade (WQ Alpha #7) — fade price move when vol > adv. Sharpe +0.52, ROI +24.1%, MDD 15.5%, 751 trades (BAD). PF=0.80.",

        "class": "VolSurgeMomentumFade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "sma_p": 30, "delta_p": 10, "ts_p": 60, "long_thresh": 0.5, "short_thresh": -0.6,
            "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "209": {
        "id": "Open_Volume_Corr_Fade",
        "desc": "Open-volume corr fade (WQ Alpha #6) — -corr(open,vol,10) Pearson. Sharpe +1.33, ROI +64.3%, MDD 12.7%, 239 trades (BAD). PF=0.93.",

        "class": "OpenVolumeCorrFade",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "corr_p": 20, "long_thresh": 0.7, "short_thresh": -0.6,
            "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "208": {
        "id": "Volatility_Regime_Reversal",
        "desc": "Volatility regime reversal (WQ Alpha #1) — rank(argmax(ret<0?std(ret,20):close, 5))-0.5. Sharpe +0.71, ROI +55.8%, MDD 28.1%, 633 trades (MEDIOCRE). PF=1.26.",

        "class": "VolatilityRegimeReversal",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "std_p": 30, "argmax_p": 3, "ts_p": 20, "long_thresh": 0.3, "short_thresh": -0.3,
            "sl_pct": 0.05, "tp_pct": 0.15
        },
    },
    "207": {
        "id": "VWAP_Dist_Vol_Delta",
        "desc": "VWAP dist × vol delta (WQ Alpha #5) — rank(open-SMA(vwap))*sign(close-vwap)*rank(|close-vwap|)*rank(delta(vol)). Sharpe -0.11, ROI -10.7%, MDD 28.8%, 409 trades (BAD). PF=0.74.",

        "class": "VWAPDistVolDelta",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ts_p": 5, "long_thresh": 0.7, "short_thresh": -0.6,
            "sl_pct": 0.03, "tp_pct": 0.1
        },
    },
    "206": {
        "id": "Low_Rank_Mean_Reversion",
        "desc": "Low rank mean-reversion (WQ Alpha #4) — -ts_rank(low, ts_period). Sharpe -0.57, ROI -48.6%, MDD 64.8%, 531 trades (BAD). PF=0.55.",

        "class": "LowRankMeanReversion",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ts_period": 5, "long_thresh": -0.2, "short_thresh": -0.8,
            "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "205": {
        "id": "Open_Volume_Anticorr",
        "desc": "Open-volume anticorr (WQ Alpha #3) — -corr(ts_rank(open),ts_rank(vol),corr_p). Sharpe +0.46, ROI +24.0%, MDD 26.7%, 125 trades (BAD). PF=0.88.",

        "class": "OpenVolumeAnticorr",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ts_p": 20, "corr_p": 20, "long_thresh": 0.8, "short_thresh": -0.6,
            "sl_pct": 0.08, "tp_pct": 0.15
        },
    },
    "204": {
        "id": "Volume_Change_Momentum",
        "desc": "Volume-change momentum anticorr (WQ Alpha #2) — -corr(ts_rank(delta(log(vol))),ts_rank((close-open)/open),corr_p). Sharpe +0.43, ROI +20.1%, MDD 23.8%, 335 trades (BAD). PF=0.85.",

        "class": "VolumeChangeMomentum",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "delta_p": 3, "corr_p": 6, "ts_p": 10, "long_thresh": 0.8, "short_thresh": -0.6,
            "sl_pct": 0.12, "tp_pct": 0.1
        },
    },
    "203": {
        "id": "Volume_Hurst_Exponent",
        "desc": "Volume Hurst exponent h(2) coupled with trend filter. Sharpe +0.60, ROI +10.9%, MDD 4.6%, 122 trades (MEDIOCRE). PF=1.04.",

        "class": "VolumeHurstExponent",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "hurst_period": 60, "hurst_thresh": 0.52, "sma_period": 20,
            "sl_pct": 0.05, "tp_pct": 0.05
        },
    },
    "202": {
        "id": "Candle_Sentiment_Index",
        "desc": "Candle Sentiment Index (CSI) breakout. Sharpe +1.17, ROI +45.8%, MDD 11.4%, 289 trades (GOOD). PF=1.33.",

        "class": "CandleSentimentIndex",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "csi_period": 30, "long_thresh": 0.2, "short_thresh": -0.3,
            "sl_pct": 0.05, "tp_pct": 0.05
        },
    },
    "201": {
        "id": "OU_Mean_Reversion",
        "desc": "OU mean-reversion speed κ to filter VWAP trades. Sharpe +0.30, ROI +12.4%, MDD 19.8%, 583 trades (BAD). PF=0.81.",

        "class": "OUMeanReversion",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ou_period": 20, "vwap_period": 10, "entry_z": 2.0, "min_kappa": 30,
            "sl_pct": 0.05, "tp_pct": 0.1
        },
    },
    "200": {
        "id": "Multi_Scale_MA_Confluence",
        "desc": "4-scale MA agreement signal (Multi-Scale MA Confluence). Sharpe +0.88, ROI +46.2%, MDD 12.8%, 383 trades (MEDIOCRE). PF=1.22.",

        "class": "MultiScaleMAConfluence",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ma1": 3, "ma2": 20, "ma3": 40, "ma4": 60, "ma_type": "SMA",
            "sl_pct": 0.05, "tp_pct": 0.06
        },
    },
    "199": {
        "id": "Volume_Close_Anti_Momentum",
        "desc": "Alpha #12: Volume-close anti-momentum (Cross-Sectional sign(delta(vol,1)) * (-delta(close,1))). Sharpe -0.23, ROI -13.8%, MDD 25.9%, 771 trades (BAD). PF=0.79.",

        "class": "VolumeCloseAntiMomentum",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "smoothing_period": 5, "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "198": {
        "id": "Volume_FOMO_Rank",
        "desc": "Kimchi Premium FOMO Proxy (Cross-Sectional corr(Volume, Price)). Sharpe +0.19, ROI +5.4%, MDD 15.6%, 454 trades (BAD). PF=0.83.",

        "class": "VolumeFOMORank",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "corr_period": 28, "delta_period": 3, "sl_pct": 0.05, "tp_pct": 0.1
        },
    },
    "197": {
        "id": "VWAP_Distance_Ratio",
        "desc": "Alpha #42: VWAP Distance Ratio (Cross-Sectional rank(vwap-close) / rank(vwap+close)). Sharpe -0.05, ROI -5.4%, MDD 20.1%, 1108 trades (BAD). PF=0.87.",

        "class": "VwapDistanceRatio",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 3,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "smoothing_period": 10, "sl_pct": 0.03, "tp_pct": 0.15
        },
    },
    "145": {
        "id":   "MDVB_BTC_4H",
        "desc": "McGinley Dynamic Volume Breakout (MDVB). Sharpe +0.16, ROI +2.9%, MDD 35.1%, 71 trades (BAD). PF=1.09.",

        "class": "MDVBStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "mcg_slow": 43, "mcg_fast": 16, "chop_period": 19,
            "chop_threshold": 34.0079, "vrsi_period": 11, "adx_period": 25, "adx_threshold": 26.1983
        },
    },
    "146": {
        "id":   "OBFC_BTC_4H",
        "desc": "Institutional Order Block Mitigation with Fisher Confirmation (OBFC). Sharpe +0.03, ROI -1.8%, MDD 31.0%, 38 trades (BAD). PF=1.04.",

        "class": "OBFCStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ob_lookback": 5, "fisher_period": 11, "ema_period": 198, "atr_period": 11, "tp_atr_mult": 4.4383, "sl_atr_mult": 1.2993
        },
    },
    "147": {
        "id":   "HVE_SOL_4H",
        "desc": "Hammer Volume Exhaustion Reversion (HVE). Sharpe +0.07, ROI -0.4%, MDD 33.1%, 54 trades (BAD). PF=1.00.",

        "class": "HVEStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "dc_period": 13, "vrsi_period": 10, "vrsi_thresh": 30.6496, "vol_z_thresh": 1.9701, "vol_z_period": 22
        },
    },
    "1": {
        "id":   "MACD_KDJ_DAILY_PROFIT",
        "desc": "Highest Return Version (Daily Timeframe, ~1560% Total Return). Sharpe +0.77, ROI +375.1%, MDD 55.6%, 29 trades (BAD). PF=1.97.",

        "class": "MACDKDJStrategy",
        "data": {"coins": "BTC", "timeframes": "1d", "date_from": "2018-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 100, "risk_per_trade": 0.15, "leverage": 30,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "macd_fast": 4, "macd_slow": 49, "macd_signal": 14,
            "kdj_period": 23, "kdj_oversold": 18, "kdj_overbought": 71,
            "stop_loss_pct": 0.0799, "take_profit_pct": None,
            "entry_window": 14, "max_hold_bars": 102, "trend_filter": True, "trend_ema_period": 81,
        },
    },
    "2": {
        "id":   "BB_SQUEEZE_BREAKOUT_1H",
        "desc": "Optimized Bollinger Band Breakout + Squeeze Momentum (1H). Sharpe -0.75, ROI -94.0%, MDD 96.1%, 227 trades (BAD). PF=0.64.",

        "class": "BB_Squeeze_Breakout_Strategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"bb_period": 29, "bb_std": 3.4961, "kc_multiplier": 1.718, "atr_multiplier_tp": 4.3568},
    },
    "3": {
        "id":   "MACD_KDJ_ADX_ATR_BTC_4H",
        "desc": "MACD + KDJ + ADX + ATR (4H, optimized risk). Sharpe +0.13, ROI -47.5%, MDD 95.8%, 29 trades (BAD). PF=0.98.",

        "class": "MACDKDJ_ADX_ATR_Strategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.20, "leverage": 30,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "macd_fast": 19, "macd_slow": 25, "macd_signal": 10,
            "kdj_period": 24, "kdj_oversold": 15, "kdj_overbought": 82,
            "entry_window": 16, "trend_filter": True, "trend_ema_period": 215,
            "adx_period": 17, "adx_threshold": 29.7996,
            "atr_period": 11, "atr_multiplier_sl": 3.1631, "atr_multiplier_tp": 6.3957,
            "max_hold_bars": 51,
            "exit_mode": "FIXED_RR",
        },
    },
    "4": {
        "id":   "MTF_MACD_KDJ_ADX_ATR_BTC",
        "desc": "Multi-Timeframe MACD+KDJ+ADX+ATR (1H signals, 4H trend filters). Sharpe -3.33, ROI -92.8%, MDD 93.8%, 429 trades (BAD). PF=0.57.",

        "class": "MTF_MACDKDJ_ADX_ATR_Strategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "macd_fast": 5, "macd_slow": 63, "macd_signal": 19,
            "kdj_period": 25, "kdj_oversold": 12, "kdj_overbought": 76,
            "entry_window": 19, "adx_threshold_1h": 17.4943, "adx_threshold_4h": 18.5091,
            "ema_trend_4h": 97, "atr_multiplier_sl": 0.5639, "atr_multiplier_tp": 5.6043,
            "exit_mode": "FIXED_RR",
        },
    },
    "5": {
        "id":   "FVG_RECOVERY_SNIPER_BTC_1D",
        "desc": "Fair Value Gap Recovery Sniper (1D, 2% gap, 80% retrace). Sharpe +0.19, ROI +6.2%, MDD 44.5%, 30 trades (BAD). PF=1.05.",

        "class": "FVG_Recovery_Strategy",
        "data": {"coins": "BTC", "timeframes": "1d", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "min_gap_pct": 0.0241, "retrace_depth": 0.6789, "require_confirmation": True,
            "tp_multiplier": 4.1718, "use_trend_filter": True, "ema_period": 171,
        },
    },
    "6": {
        "id":   "VRSI_MEAN_REVERSION_BTC_5M",
        "desc": "Volume-Weighted RSI Mean Reversion (5M). Sharpe -1.62, ROI -34.7%, MDD 35.2%, 33 trades (BAD). PF=0.34.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vrsi_period": 67, "vrsi_oversold": 5.9741, "vrsi_overbought": 89.0952,
            "vwap_period": 382, "vwap_std_mult": 5.8956, "sl_pct": 0.0819,
            "entry_filter": "NONE", "exit_mode": "VWAP_REVERT",
            "max_hold_bars": 13, "consecutive_signals": 1, "adx_period": 34, "adx_threshold": 44
        },
    },
    "6_15M": {
        "id":   "TEST_VRSI_BTC_15M",
        "desc": "Test: VRSI on 15m. Sharpe -1.62, ROI -34.7%, MDD 35.2%, 33 trades (BAD). PF=0.34.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"vrsi_period": 77, "vwap_period": 365, "exit_mode": "VRSI_RESET", "entry_filter": "ADX_BLOCKER"}
    },
    "6_30M": {
        "id":   "TEST_VRSI_BTC_30M",
        "desc": "Test: VRSI on 30m. Sharpe -1.62, ROI -34.7%, MDD 35.2%, 33 trades (BAD). PF=0.34.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "30m", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"vrsi_period": 13, "vwap_period": 184, "exit_mode": "VRSI_RESET", "entry_filter": "NONE"}
    },
    "6_1H": {
        "id":   "TEST_VRSI_BTC_1H",
        "desc": "Test: VRSI on 1h. Sharpe -1.62, ROI -34.7%, MDD 35.2%, 33 trades (BAD). PF=0.34.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"vrsi_period": 31, "vwap_period": 216, "exit_mode": "VRSI_RESET", "entry_filter": "NONE"}
    },
    "7": {
        "id":   "VRSI_MEAN_REVERSION_BTC_4H_OPT",
        "desc": "V-RSI Mean Reversion optimized for 4H (positive Sharpe). Sharpe -0.36, ROI -23.5%, MDD 49.1%, 34 trades (BAD). PF=0.65.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vrsi_period": 21, "vrsi_oversold": 12.9479, "vrsi_overbought": 77.6071,
            "vwap_period": 123, "vwap_std_mult": 3.6217, "sl_pct": 0.0657,
            "use_trend_filter": True, "ema_period": 17,
        },
    },
    "8": {
        "id":   "VRSI_MEAN_REVERSION_BTC_1H_OPT",
        "desc": "V-RSI Mean Reversion optimized for 1H (positive Sharpe). Sharpe -0.90, ROI -36.9%, MDD 38.4%, 55 trades (BAD). PF=0.47.",

        "class": "MeanReversionVRSI",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vrsi_period": 54, "vrsi_oversold": 13.4704, "vrsi_overbought": 87.7028,
            "vwap_period": 65, "vwap_std_mult": 3.0629, "sl_pct": 0.0978,
            "use_trend_filter": True, "ema_period": 78,
        },
    },
    "9": {
        "id":   "BTC_SWING_EMA_MACD_4H",
        "desc": "BTC Swing (EMA200 + RSI21 > 55 + MACD, 4H). Sharpe -0.75, ROI -64.4%, MDD 76.9%, 93 trades (BAD). PF=0.71.",

        "class": "BTCSwingEMAMACD",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 10000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_window": 200, "rsi_window": 21, "rsi_threshold": 55.0,
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "tp_pct": 0.12, "sl_pct": 0.03,
        },
    },
    "10": {
        "id":   "TIP_BREAKOUT_BTC_1H",
        "desc": "Taker-Intensity Participation Breakout (1H, 50-1.5 BB, 0.53 Taker). Sharpe -2.25, ROI -71.8%, MDD 75.4%, 182 trades (BAD). PF=0.50.",

        "class": "TIPBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        13,
            "bb_std":           3.498,
            "intensity_period": 25,
            "intensity_std":    2.9627,
            "taker_threshold":  0.549,
            "sl_atr_mult":      0.6481,
            "tp_atr_mult":      5.3595,
            "max_hold_bars":    56,
        },
    },
    "11": {
        "id":   "DUAL_EMA_VOLATILITY_BTC_1D",
        "desc": "Dual EMA Crossover + Volatility Expansion (1D, 5-21 EMA, 200 SMA). Sharpe +0.87, ROI +52.0%, MDD 11.6%, 13 trades (BAD). PF=3.99.",

        "class": "DualEMAVolatilityStrategy",
        "data": {"coins": "BTC", "timeframes": "1d", "date_from": "2018-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 10000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast": 11, "ema_slow": 25, "sma_macro": 71,
            "intensity_period": 9, "intensity_std": 1.0668,
            "rsi_period": 14, "rsi_threshold": 35.6577,
        },
    },
    "12": {
        "id":   "VWAP_ATR_REVERSION_BTC_4H",
        "desc": "VWAP Mean Reversion (4H, high-return optimized). Sharpe -0.45, ROI -26.1%, MDD 35.9%, 49 trades (BAD). PF=0.51.",

        "class": "VWAPATRReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2020-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "multiplier": 5.0239, "sl_multiplier": 2.4912, "atr_period": 86,
            "max_hold_bars": 626, "ema_slope_thresh": 0.2703,
            "use_pattern_filter": False, "use_vol_filter": False,
        },
    },
    "13": {
        "id":   "MACRO_TAKER_FLOW_EXHAUSTION_4H",
        "desc": "Macro Taker-Flow Exhaustion Reversal (4H, optimized ROI). Sharpe -0.34, ROI -28.6%, MDD 52.1%, 28 trades (BAD). PF=0.77.",

        "class": "MacroTakerFlowExhaustionStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2020-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "lookback": 46, "ema_period": 129,
            "taker_high_threshold": 0.6982, "taker_low_threshold": 0.423, "sl_pct": 0.0127,
        },
    },
    "14": {
        "id":   "MACD_KDJ_ETH_4H",
        "desc": "MACD + KDJ optimized for ETH (4H). Sharpe +0.67, ROI +136.9%, MDD 34.9%, 37 trades (MEDIOCRE). PF=1.85.",

        "class": "MACDKDJStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "macd_fast": 11, "macd_slow": 81, "macd_signal": 18,
            "kdj_period": 15, "kdj_oversold": 17, "kdj_overbought": 79,
            "stop_loss_pct": 0.02, "take_profit_pct": None,
            "entry_window": 8, "max_hold_bars": 63, "trend_filter": True, "trend_ema_period": 217,
        },
    },
    "15": {
        "id":   "DUAL_EMA_ETH_4H_TREND",
        "desc": "Dual EMA Crossover optimized for ETH trend (4H). Sharpe +0.69, ROI +78.1%, MDD 27.4%, 55 trades (MEDIOCRE). PF=1.60.",

        "class": "DualEMAVolatilityStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast": 26, "ema_slow": 20, "sma_macro": 200,
            "intensity_period": 20, "intensity_std": 1.0,
            "rsi_period": 11, "rsi_threshold": 80.0,
        },
    },
    "16": {
        "id":   "ETH_LAYERED_REVERSION_15M",
        "desc": "ETH Layered Mean Reversion (15M, 3-layer grid, scalp). Sharpe +0.07, ROI -0.8%, MDD 20.0%, 175 trades (BAD). PF=1.01.",

        "class": "ETHLayeredReversionStrategy",
        "data": {"coins": "ETH", "timeframes": "15m", "date_from": "2024-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 10000, "risk_per_trade": 0.08, "leverage": 4,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period": 7, "multiplier_l1": 7.7223, "multiplier_l2": 11.566, "multiplier_l3": 11.0262,
            "tp_pct": 0.147, "sl_pct": 0.0904, "rsi_period": 23,
            "rsi_oversold": 25.2543, "rsi_overbought": 81.0669, "entry_mode": "SINGLE",
        },
    },
    "17": {
        "id":   "TAKER_EMA_PULLBACK_BTC_15M",
        "desc": "Taker-EMA Pullback (15M, long-only, EMA50 touch + taker support + pattern). Sharpe -2.40, ROI -96.7%, MDD 97.5%, 275 trades (BAD). PF=0.51.",

        "class": "TakerEMAPullbackStrategy",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast": 5, "ema_slow": 193,
            "taker_threshold": 0.6405, "pullback_lookback": 2,
            "sl_pct": 0.1905, "touch_band": 0.0028,
            "tp_rr": 3.7837, "swing_lookback": 28, "max_hold_bars": 160,
        },
    },
    "18": {
        "id":   "MACD_KDJ_BNB_4H",
        "desc": "Autonomous Research: MACD + KDJ for BNB (4H Trend) - Optimized. Sharpe +0.52, ROI +67.8%, MDD 28.0%, 195 trades (MEDIOCRE). PF=1.19.",

        "class": "MACDKDJStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "macd_fast": 18, "macd_slow": 28, "macd_signal": 16,
            "kdj_period": 28, "kdj_oversold": 38, "kdj_overbought": 89,
            "stop_loss_pct": 0.0957, "take_profit_pct": 0.0822,
        },
    },
    "19": {
        "id":   "ETH_MOMENTUM_SQUEEZE_4H",
        "desc": "ETH Momentum Bollinger Keltner Squeeze (4H). Sharpe -0.02, ROI -9.4%, MDD 50.1%, 19 trades (BAD). PF=0.92.",

        "class": "ETHMomentumSqueezeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        21,
            "bb_std":           2.9261,
            "intensity_period": 24,
            "intensity_std":    2.1973,
            "taker_threshold":  0.5312,
            "sl_atr_mult":      0.89,
            "tp_atr_mult":      1.4066,
            "max_hold_bars":    175,
        },
    },
    "20": {
        "id":   "SUPERTREND_PRO_BTC_4H",
        "desc": "Supertrend Pro Strategy (4H, BTC). Sharpe +0.72, ROI +203.9%, MDD 75.3%, 373 trades (BAD). PF=1.10.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        21,
            "multiplier":        0.7045,
            "adx_period":        17,
            "adx_threshold":     21,
            "bb_period":         19,
            "bb_std":            1.0839,
            "kc_multiplier":     2.3069,
        },
    },
    "21": {
        "id":   "KELTNER_RSI_REVERSION_BTC_1H",
        "desc": "Keltner Channel RSI Mean Reversion (1H, BTC). Sharpe -0.20, ROI -4.4%, MDD 8.2%, 28 trades (BAD). PF=0.79.",

        "class": "KeltnerRSIReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "kc_window":          10,
            "kc_multiplier":      1.3381,
            "kc_atr_window":      23,
            "rsi_window":         21,
            "rsi_oversold":       15.6805,
            "rsi_overbought":     84.0376,
            "sl_atr_multiplier":  0.8826,
        },
    },
    "22": {
        "id":   "SUPER_FVMA_BTC_4H",
        "desc": "Super FVMA Momentum (4H, BTC). Sharpe +0.25, ROI +17.7%, MDD 59.1%, 94 trades (BAD). PF=1.10.",

        "class": "SuperFVMAStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":          10,
            "st_multiplier":      3.5,
            "fvma_period":        20,
            "macd_fast":          12,
            "macd_slow":          26,
            "macd_signal":        9,
            "sl_atr_multiplier":  1.0,
        },
    },
    "23": {
        "id":   "EMA_CROSSOVER_BTC_4H",
        "desc": "EMA Crossover Strategy (4H, BTC). Sharpe +0.26, ROI -3.3%, MDD 62.8%, 160 trades (BAD). PF=1.06.",

        "class": "EMACrossoverStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast_period":       12,
            "slow_period":       100,
            "volatility_filter": "NONE",
            "direction_mode":    "BOTH",
        },
    },
    "24": {
        "id":   "SUPER_FVMA_BNB_4H",
        "desc": "Super FVMA Momentum (4H, BNB). Sharpe +0.69, ROI +189.6%, MDD 53.5%, 103 trades (MEDIOCRE). PF=1.33.",

        "class": "SuperFVMAStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":          10,
            "st_multiplier":      3.5,
            "fvma_period":        20,
            "macd_fast":          12,
            "macd_slow":          26,
            "macd_signal":        9,
            "sl_atr_multiplier":  1.0,
        },
    },
    "25": {
        "id":   "SUPER_FVMA_SOL_4H",
        "desc": "Super FVMA Momentum (4H, SOL). Sharpe +0.99, ROI +798.2%, MDD 54.8%, 85 trades (MEDIOCRE). PF=2.04.",

        "class": "SuperFVMAStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":          10,
            "st_multiplier":      3.5,
            "fvma_period":        20,
            "macd_fast":          12,
            "macd_slow":          26,
            "macd_signal":        9,
            "sl_atr_multiplier":  1.0,
        },
    },
    "26": {
        "id":   "ENVELOPE_MEAN_REVERSION_BTC_1H",
        "desc": "Envelope Mean Reversion (1H, BTC). Sharpe +0.83, ROI +69.3%, MDD 21.1%, 51 trades (MEDIOCRE). PF=1.87.",

        "class": "EnvelopeMeanReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "sma_period":     9,
            "deviation_pct":  0.0546,
            "use_vol_filter": False,
            "vol_ma_period":  26,
            "sl_pct":         0.1761,
        },
    },
    "27": {
        "id":   "TAKER_INTENSITY_MOMENTUM_BTC_1H",
        "desc": "Taker Buy Intensity Momentum (1H, BTC). Sharpe -2.32, ROI -96.4%, MDD 97.2%, 437 trades (BAD). PF=0.64.",

        "class": "TakerBuyIntensityMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "taker_ratio_threshold": 0.6172,
            "vol_ma_period":         30,
            "trend_ema_period":      41,
            "atr_period":            11,
            "atr_multiplier_tp":     9.546,
            "atr_multiplier_sl":     1.8541,
        },
    },
    "28": {
        "id":   "RSI_MEAN_REVERSION_DAILY_BTC",
        "desc": "RSI Mean Reversion Daily (1D, BTC). Sharpe +0.32, ROI +29.9%, MDD 40.0%, 74 trades (MEDIOCRE). PF=1.21.",

        "class": "RSIMeanReversionDailyStrategy",
        "data": {"coins": "BTC", "timeframes": "1d", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period":    5,
            "rsi_low":       30.0,
            "rsi_high":      70.0,
            "max_hold_bars": 5,
        },
    },
    "143": {
    "id":   "VRSI_MEAN_REVERSION_SOL_1H",
    "desc": "V-RSI Mean Reversion for SOL (1H) - Relaxed for Ranging. Sharpe -0.66, ROI -90.3%, MDD 92.5%, 1309 trades (BAD). PF=0.87.",

    "class": "MeanReversionVRSI",
    "data": {"coins": "SOL", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "vrsi_period": 14, "vrsi_oversold": 25.0, "vrsi_overbought": 75.0,
        "vwap_period": 100, "vwap_std_mult": 1.3, "sl_pct": 0.02,
        "use_trend_filter": False, "ema_period": 200,
    },
    },
    "29": {
    "id":   "VWAP_ATR_REVERSION_XRP_4H",
    "desc": "VWAP Mean Reversion for XRP (4H). Sharpe +0.50, ROI +66.1%, MDD 41.3%, 42 trades (MEDIOCRE). PF=2.47.",

    "class": "VWAPATRReversionStrategy",
    "data": {"coins": "XRP", "timeframes": "4h", "date_from": "2020-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 100, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "multiplier": 4.6707, "sl_multiplier": 5.3156, "atr_period": 67,
        "max_hold_bars": 118, "ema_slope_thresh": 0.1171,
        "use_pattern_filter": False, "use_vol_filter": False,
    },
    },
    "30": {
    "id":   "LIQUIDITY_SWEEP_REVERSAL_BTC_4H",
    "desc": "Liquidity Sweep & Reversal (4H, BTC). Sharpe +0.31, ROI +28.6%, MDD 50.0%, 145 trades (MEDIOCRE). PF=1.07.",

    "class": "LiquiditySweepReversalStrategy",
    "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 32, "cvd_window": 44, "atr_multiplier_tp": 3.5429, "atr_multiplier_sl": 2.736, "direction_mode": "LONG_ONLY",
    },
    },
    "31": {
    "id":   "LIQUIDITY_SWEEP_REVERSAL_ETH_4H",
    "desc": "Liquidity Sweep & Reversal (4H, ETH). Sharpe +0.63, ROI +191.2%, MDD 63.0%, 110 trades (MEDIOCRE). PF=1.17.",

    "class": "LiquiditySweepReversalStrategy",
    "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 27, "cvd_window": 34, "atr_multiplier_tp": 5.5647, "atr_multiplier_sl": 2.7211,
    },
    },
    "32": {
    "id":   "LIQUIDITY_SWEEP_REVERSAL_BNB_4H",
    "desc": "Liquidity Sweep & Reversal (4H, BNB). Sharpe +0.65, ROI +136.1%, MDD 62.3%, 226 trades (MEDIOCRE). PF=1.11.",

    "class": "LiquiditySweepReversalStrategy",
    "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 27, "cvd_window": 22, "atr_multiplier_tp": 4.4696, "atr_multiplier_sl": 0.6528,
    },
    },
    "33": {
    "id":   "LIQUIDITY_SWEEP_REVERSAL_SOL_4H",
    "desc": "Liquidity Sweep & Reversal (4H, SOL). Sharpe +0.53, ROI +100.1%, MDD 65.0%, 372 trades (MEDIOCRE). PF=1.04.",

    "class": "LiquiditySweepReversalStrategy",
    "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 16, "cvd_window": 17, "atr_multiplier_tp": 1.6021, "atr_multiplier_sl": 0.6337,
    },
    },
    "34": {
    "id":   "LIQUIDITY_SWEEP_REVERSAL_XRP_4H",
    "desc": "Liquidity Sweep & Reversal (4H, XRP). Sharpe +0.40, ROI +42.1%, MDD 58.2%, 93 trades (MEDIOCRE). PF=1.09.",

    "class": "LiquiditySweepReversalStrategy",
    "data": {"coins": "XRP", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 28, "cvd_window": 15, "atr_multiplier_tp": 6.9515, "atr_multiplier_sl": 2.4671,
    },
    },
    "35": {
    "id":   "VWAP_ATR_REVERSION_BNB_4H",
    "desc": "VWAP Mean Reversion for BNB (4H). Sharpe +1.28, ROI +196.6%, MDD 17.1%, 40 trades (MEDIOCRE). PF=11.50.",

    "class": "VWAPATRReversionStrategy",
    "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2020-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "multiplier": 5.2412, "sl_multiplier": 6.619, "atr_period": 64,
        "max_hold_bars": 262, "ema_slope_thresh": 0.2363,
        "use_pattern_filter": False, "use_vol_filter": False,
    },
    },
    "36": {
    "id":   "VWAP_ATR_REVERSION_SOL_4H",
    "desc": "VWAP Mean Reversion for SOL (4H). Sharpe +0.64, ROI +159.6%, MDD 46.4%, 39 trades (MEDIOCRE). PF=2.90.",

    "class": "VWAPATRReversionStrategy",
    "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2020-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "multiplier": 5.0637, "sl_multiplier": 6.3075, "atr_period": 65,
        "max_hold_bars": 595, "ema_slope_thresh": 0.0206,
        "use_pattern_filter": False, "use_vol_filter": False,
    },
    },
    "37": {
        "id":   "DMI_ADX_BTC_4H",
        "desc": "DMI ADX Trend Strength Strategy (BTC 4H). Sharpe -0.54, ROI -57.9%, MDD 69.0%, 60 trades (BAD). PF=0.71.",

        "class": "DMIADXStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"adx_period": 17, "adx_threshold": 29.6427, "atr_period": 15, "atr_multiplier_sl": 0.6643, "atr_multiplier_tp": 1.3245},
    },
    "38": {
        "id":   "FVG_MITIGATION_BTC_4H",
        "desc": "FVG Mitigation Reversal Strategy (BTC 4H). Sharpe +0.87, ROI +235.1%, MDD 48.7%, 77 trades (MEDIOCRE). PF=1.27.",

        "class": "FVGMitigationReversalStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"min_gap_pct": 0.0422, "tp_multiplier": 4.2292},
    },
    "39": {
        "id":   "DMI_ADX_BNB_4H",
        "desc": "DMI ADX Trend Strength Strategy (BNB 4H). Sharpe +0.33, ROI +21.2%, MDD 59.2%, 36 trades (MEDIOCRE). PF=1.05.",

        "class": "DMIADXStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"adx_period": 11, "adx_threshold": 37.9728, "atr_period": 19, "atr_multiplier_sl": 2.9337, "atr_multiplier_tp": 7.3586},
    },
    "40": {
        "id":   "DMI_ADX_SOL_4H",
        "desc": "DMI ADX Trend Strength Strategy (SOL 4H). Sharpe +0.31, ROI +23.1%, MDD 60.2%, 37 trades (MEDIOCRE). PF=1.09.",

        "class": "DMIADXStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"adx_period": 33, "adx_threshold": 23.5593, "atr_period": 25, "atr_multiplier_sl": 0.7367, "atr_multiplier_tp": 3.2907},
    },
    "41": {
        "id":   "DMI_ADX_XRP_4H",
        "desc": "DMI ADX Trend Strength Strategy (XRP 4H). Sharpe +0.83, ROI +213.9%, MDD 28.5%, 35 trades (MEDIOCRE). PF=2.35.",

        "class": "DMIADXStrategy",
        "data": {"coins": "XRP", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {"adx_period": 38, "adx_threshold": 23.1341, "atr_period": 21, "atr_multiplier_sl": 2.9964, "atr_multiplier_tp": 1.1718},
    },
    "42": {
        "id":   "BBW_VOLATILITY_BREAKOUT_BTC_1H",
        "desc": "Bollinger Band Width Volatility Breakout (1H). Sharpe -1.45, ROI -87.7%, MDD 92.4%, 479 trades (BAD). PF=0.67.",

        "class": "BBWVolatilityBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
        "bb_period":        25,
        "bb_std":           2.9619,
        "intensity_period": 11,
        "intensity_std":    2.5257,
        "taker_threshold":  0.6152,
        "sl_atr_mult":      2.5977,
        "tp_atr_mult":      3.5793,
        "max_hold_bars":    173,
    },
    },
    "43": {
        "id":   "DYNAMIC_SWING_VWAP_BTC_1H",
        "desc": "Dynamic Swing Anchored VWAP (1H, BTC). Sharpe -2.53, ROI -96.1%, MDD 96.8%, 593 trades (BAD). PF=0.51.",

        "class": "DynamicSwingAnchoredVWAPStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "swing_lookback":    50,
            "atr_period":        28,
            "sl_atr_multiplier": 1.352,
            "tp_rr_ratio":       4.855,
            "vol_sma_period":    25,
            "breakout_mode":     "VOLUME_CONFIRMED",
        },
    },
    "44": {
        "id":   "RSI_TREND_FILTER_BTC_4H",
        "desc": "RSI Trend Filter Strategy (4H, BTC). Sharpe +0.06, ROI +0.8%, MDD 15.4%, 42 trades (BAD). PF=1.04.",

        "class": "RSITrendFilterStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_period":      174,
            "rsi_period":      9,
            "rsi_oversold":    22,
            "rsi_overbought":  71,
            "take_profit_pct": 0.1607,
            "stop_loss_pct":   0.0822,
        },
    },
    "45": {
        "id":   "ICT_HOLY_TRINITY_BTC_1H",
        "desc": "ICT Holy Trinity Confluence (1H, BTC). Sharpe +0.06, ROI -10.3%, MDD 61.1%, 93 trades (BAD). PF=0.99.",

        "class": "ICTHolyTrinityConfluenceStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":      15,
            "st_multiplier":  4.8084,
            "macd_fast":      16,
            "macd_slow":      23,
            "macd_signal":    7,
            "rsi_period":     19,
            "rsi_upper":      76,
            "rsi_lower":      38,
            "swing_lookback": 36,
            "fvg_min_pct":    0.021,
        },
    },
    "46": {
        "id":   "ICT_HOLY_TRINITY_ETH_1H",
        "desc": "ICT Holy Trinity Confluence (1H, ETH). Sharpe +0.41, ROI +34.2%, MDD 47.3%, 153 trades (MEDIOCRE). PF=1.09.",

        "class": "ICTHolyTrinityConfluenceStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":      13,
            "st_multiplier":  2.4405,
            "macd_fast":      9,
            "macd_slow":      26,
            "macd_signal":    8,
            "rsi_period":     11,
            "rsi_upper":      72,
            "rsi_lower":      25,
            "swing_lookback": 50,
            "fvg_min_pct":    0.0301,
        },
    },
    "47": {
        "id":   "AROON_RSI_BTC_4H",
        "desc": "Aroon RSI Strategy (4H, BTC). Sharpe +0.21, ROI +12.5%, MDD 32.9%, 52 trades (BAD). PF=1.14.",

        "class": "AroonRSIStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "aroon_period":     18,
            "rsi_period":       28,
            "ema_period":       178,
            "aroon_threshold":  52,
            "rsi_lower":        27,
            "rsi_upper":        78,
            "tp_atr_mult":      7.789,
            "sl_atr_mult":      0.662,
        },
    },
    "48": {
        "id":   "WAVETREND_MFI_BTC_1H",
        "desc": "WaveTrend MFI Divergence (1H, BTC). Sharpe +0.10, ROI +2.5%, MDD 27.5%, 43 trades (BAD). PF=1.05.",

        "class": "WaveTrendMFIDivergenceStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "wt_n1":              14,
            "wt_n2":              19,
            "wt_oversold":        -10,
            "wt_overbought":      43,
            "mfi_period":         29,
            "ema_period":         128,
            "divergence_lookback":19,
            "tp_rr":              2.4448,
            "sl_atr_mult":        2.6629,
            "signal_mode":        "STRICT_DIVERGENCE",
        },
    },
    "49": {
        "id":   "EMA_CROSSOVER_BNB_4H",
        "desc": "EMA Crossover Strategy (4H, BNB). Sharpe +0.20, ROI -8.2%, MDD 62.9%, 122 trades (BAD). PF=0.98.",

        "class": "EMACrossoverStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast_period": 12,
            "slow_period": 100,
        },
    },
    "50": {
        "id":   "EMA_CROSSOVER_SOL_4H",
        "desc": "EMA Crossover Strategy (4H, SOL). Sharpe +0.74, ROI +155.5%, MDD 68.3%, 129 trades (MEDIOCRE). PF=1.21.",

        "class": "EMACrossoverStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast_period": 12,
            "slow_period": 100,
        },
    },
    "52": {
        "id":   "WAVETREND_MFI_ETH_1H",
        "desc": "WaveTrend MFI Divergence (1H, ETH). Sharpe +0.46, ROI +31.5%, MDD 19.4%, 51 trades (MEDIOCRE). PF=1.43.",

        "class": "WaveTrendMFIDivergenceStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "wt_n1":              12,
            "wt_n2":              14,
            "wt_oversold":        -10,
            "wt_overbought":      64,
            "mfi_period":         17,
            "ema_period":         93,
            "divergence_lookback":15,
            "tp_rr":              4.0437,
            "sl_atr_mult":        1.2181,
        },
    },
    "53": {
        "id":   "WAVETREND_MFI_BNB_1H",
        "desc": "WaveTrend MFI Divergence (1H, BNB). Sharpe +0.38, ROI +24.2%, MDD 19.0%, 54 trades (MEDIOCRE). PF=1.22.",

        "class": "WaveTrendMFIDivergenceStrategy",
        "data": {"coins": "BNB", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "wt_n1":              5,
            "wt_n2":              11,
            "wt_oversold":        -10,
            "wt_overbought":      76,
            "mfi_period":         16,
            "ema_period":         26,
            "divergence_lookback":13,
            "tp_rr":              4.2167,
            "sl_atr_mult":        1.4918,
        },
    },
    "54": {
        "id":   "WAVETREND_MFI_XRP_1H",
        "desc": "WaveTrend MFI Divergence (1H, XRP). Sharpe +1.41, ROI +98.3%, MDD 6.7%, 40 trades (MEDIOCRE). PF=3.67.",

        "class": "WaveTrendMFIDivergenceStrategy",
        "data": {"coins": "XRP", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "wt_n1":              14,
            "wt_n2":              19,
            "wt_oversold":        -10,
            "wt_overbought":      62,
            "mfi_period":         8,
            "ema_period":         144,
            "divergence_lookback":7,
            "tp_rr":              1.1175,
            "sl_atr_mult":        1.5295,
        },
    },
    "56": {
        "id":   "SUPERTREND_PRO_ETH_4H_V1",
        "desc": "Supertrend Pro Strategy (4H, ETH) v1. Sharpe +2.22, ROI +12835.4%, MDD 22.4%, 268 trades (GOOD). PF=1.78.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        27,
            "multiplier":        0.5012,
            "adx_period":        8,
            "adx_threshold":     28,
            "bb_period":         11,
            "bb_std":            3.3745,
            "kc_multiplier":     2.8914,
        },
    },
    "57": {
        "id":   "SUPERTREND_PRO_SOL_4H",
        "desc": "Supertrend Pro Strategy (4H, SOL). Sharpe +1.65, ROI +63427.7%, MDD 52.2%, 515 trades (MEDIOCRE). PF=1.15.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        27,
            "multiplier":        0.5004,
            "adx_period":        9,
            "adx_threshold":     16,
            "bb_period":         21,
            "bb_std":            2.7988,
            "kc_multiplier":     2.6983,
        },
    },
    "58": {
        "id":   "ZSCORE_STAT_ARB_BTC_1H",
        "desc": "Z-Score Statistical Arbitrage (1H, BTC). Sharpe -0.14, ROI -14.0%, MDD 21.1%, 68 trades (BAD). PF=0.86.",

        "class": "ZScoreStatArbStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "z_period":           86,
            "z_threshold":        4.4442,
            "use_candle_confirm": False,
            "trend_filter_period":0,
            "sl_atr_mult":        4.8693,
        },
    },
    "59": {
        "id":   "EMA_RIBBON_RSI_BTC_1H",
        "desc": "EMA Ribbon RSI Momentum (1H, BTC). Sharpe -0.60, ROI -47.6%, MDD 49.3%, 125 trades (BAD). PF=0.76.",

        "class": "EMARibbonRSIMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast":       31,
            "ema_med":        58,
            "ema_slow":       174,
            "rsi_period":     28,
            "rsi_threshold":  73,
        },
    },
    "60": {
        "id":   "FISHER_TRANSFORM_BTC_1H",
        "desc": "Fisher Transform Strategy (1H, BTC). Sharpe -4.42, ROI -100.0%, MDD 100.0%, 8729 trades (BAD). PF=0.62.",

        "class": "FisherTransformStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "period": 16,
        },
    },
    "61": {
        "id":   "SUPERTREND_PRO_ETH_4H_V2",
        "desc": "Supertrend Pro Strategy (4H, ETH) v2. Sharpe +2.22, ROI +12835.4%, MDD 22.4%, 268 trades (GOOD). PF=1.78.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        27,
            "multiplier":        0.5012,
            "adx_period":        8,
            "adx_threshold":     28,
            "bb_period":         11,
            "bb_std":            3.3745,
            "kc_multiplier":     2.8914,
        },
    },
    "62": {
        "id":   "SUPERTREND_PRO_BNB_4H",
        "desc": "Supertrend Pro Strategy (4H, BNB). Sharpe +1.41, ROI +2619.2%, MDD 64.2%, 433 trades (MEDIOCRE). PF=1.10.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        29,
            "multiplier":        0.5013,
            "rv_threshold":      0.062,
            "rsi_period":        23,
            "rsi_low":           39,
            "rsi_high":          67,
            "atr_multiplier_sl": 1.9936,
            "atr_multiplier_tp": 7.0833,
        },
    },
    "63": {
        "id": "ORDER_BLOCK_SMC_BTC_4H",
        "desc": "Order Block (SMC) Reversal Strategy (4H, BTC) - Optimized. Sharpe +0.25, ROI +10.8%, MDD 19.8%, 37 trades (BAD). PF=1.17.",

        "class": "OrderBlockSMCStrategy",
    "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "lookback": 7, "ob_volume_mult": 2.8206, "tp_rr": 3.821
        },
    },
    "64": {
        "id": "AVSO_MOMENTUM_BTC_4H",
        "desc": "Adaptive Volatility-Scaled Oscillator Momentum (4H, BTC). Sharpe -0.09, ROI -35.5%, MDD 62.1%, 198 trades (BAD). PF=0.95.",

        "class": "AVSOMomentumStrategy",
    "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "length": 8, "smoothing": 25, "vol_lookback": 44, "vol_threshold": 0.9888, "atr_multiplier_sl": 2.9186
        },
    },
    "65": {
            "id": "MULTI_TF_RSI_DIV_BTC_1H",
            "desc": "Multi-TF RSI Divergence (1H base, 4H filter). Sharpe -0.31, ROI -11.0%, MDD 17.9%, 20 trades (BAD). PF=0.74.",

            "class": "MultiTFRSIDivergenceStrategy",
    "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
            "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                     "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
            "params": {
                "rsi_period": 10, "lookback": 31, "pivot_window": 25, "rsi_low": 37.1362, "rsi_high": 60.5831, "sl_atr_mult": 2.7497, "tp_rr": 3.8574
            },
        },
            "66": {
        "id": "ZERO_LAG_TREND_SPEED_SOL_4H",
        "desc": "Zero-Lag Trend Speed Momentum (SOL 4H, Elite Speed Demon). Sharpe +0.86, ROI +562.1%, MDD 63.7%, 32 trades (MEDIOCRE). PF=1.75.",

        "class": "ZeroLagTrendSpeedStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "zlema_period": 36,
            "ema_speed_period": 58,
            "zscore_period": 233,
            "zscore_threshold": 3.3946,
            "atr_period": 9,
            "atr_multiplier_sl": 1.358,
            "atr_multiplier_tp": 15.0,
            "direction_mode": "long_only",
            "use_adx_filter": False,
            "exit_mode": "fixed_only",
            "use_taker_filter": True,
            "taker_threshold": 0.55
        },
    },
    "67": {
        "id": "T3_NEXUS_STIFF_BTC_1H",
        "desc": "T3 Nexus + Stiff Surge Momentum (BTC 1H). Sharpe -1.33, ROI -99.8%, MDD 99.8%, 510 trades (BAD). PF=0.27.",

        "class": "T3NexusStiffStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.15, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "t3_length": 32, "t3_vf": 0.937,
            "wae_sensitivity": 250, "wae_fast_len": 10, "wae_slow_len": 60,
            "wae_bb_len": 16, "wae_bb_mult": 1.1012, "wae_deadzone": 14,
            "stiff_len": 37, "stiff_threshold": 0.9263
        },
    },
    "68": {
        "id": "FUNDING_RATE_MEAN_REVERSION_BTC_4H",
        "desc": "Funding Rate Mean Reversion (BTC 4H, ranging market). Sharpe +0.18, ROI +5.0%, MDD 12.6%, 58 trades (BAD). PF=1.04.",

        "class": "MeanReversionFundingRateStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31", "candle_types": ["funding_rate"]},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "funding_threshold_long": -0.00005,
            "funding_threshold_short": 0.0003,
            "exit_threshold_long": 0.0,
            "exit_threshold_short": 0.0001,
            "funding_lookback_period": 24,
            "adx_period": 36,
            "adx_threshold": 16,
            "stop_loss_pct": 0.076,
            "take_profit_pct": 0.1691,
        },
    },
    "70": {
        "id": "FUNDING_RATE_MEAN_REVERSION_ETH_4H",
        "desc": "Funding Rate Mean Reversion (ETH 4H, ranging market). Sharpe +0.14, ROI +3.4%, MDD 19.2%, 74 trades (BAD). PF=1.01.",

        "class": "MeanReversionFundingRateStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31", "candle_types": ["funding_rate"]},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "funding_threshold_long": -0.00005,
            "funding_threshold_short": 0.0003,
            "exit_threshold_long": 0.0,
            "exit_threshold_short": 0.0001,
            "funding_lookback_period": 24,
            "adx_period": 28,
            "adx_threshold": 22,
            "stop_loss_pct": 0.0854,
            "take_profit_pct": 0.1768,
        },
    },
    "71": {
        "id": "FUNDING_RATE_MEAN_REVERSION_BNB_4H",
        "desc": "Funding Rate Mean Reversion (BNB 4H, ranging market). Sharpe +0.73, ROI +85.0%, MDD 34.1%, 84 trades (MEDIOCRE). PF=1.14.",

        "class": "MeanReversionFundingRateStrategy",
        "data": {"coins": "BNB", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31", "candle_types": ["funding_rate"]},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "funding_threshold_long": -0.00005,
            "funding_threshold_short": 0.0003,
            "exit_threshold_long": 0.0,
            "exit_threshold_short": 0.0001,
            "funding_lookback_period": 24,
            "adx_period": 12,
            "adx_threshold": 38,
            "stop_loss_pct": 0.0513,
            "take_profit_pct": 0.1287,
        },
    },
            "72": {
        "id": "FUNDING_RATE_MEAN_REVERSION_SOL_4H",
        "desc": "Funding Rate Mean Reversion (SOL 4H, ranging market). Sharpe +1.08, ROI +145.8%, MDD 19.1%, 48 trades (MEDIOCRE). PF=1.96.",

        "class": "MeanReversionFundingRateStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "funding_threshold_long": -0.00005,
            "funding_threshold_short": 0.0003,
            "exit_threshold_long": 0.0,
            "exit_threshold_short": 0.0001,
            "funding_lookback_period": 24,
            "adx_period": 3,
            "adx_threshold": 24,
            "stop_loss_pct": 0.035,
            "take_profit_pct": 0.1423
        },
    },
    "73": {
        "id": "FUNDING_RATE_MEAN_REVERSION_XRP_4H",
        "desc": "Funding Rate Mean Reversion (XRP 4H, ranging market). Sharpe +1.27, ROI +138.8%, MDD 15.6%, 52 trades (MEDIOCRE). PF=2.17.",

        "class": "MeanReversionFundingRateStrategy",
        "data": {"coins": "XRP", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31", "candle_types": ["funding_rate"]},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "funding_threshold_long": -0.00005,
            "funding_threshold_short": 0.0003,
            "exit_threshold_long": 0.0,
            "exit_threshold_short": 0.0001,
            "funding_lookback_period": 24,
            "adx_period": 10,
            "adx_threshold": 20,
            "stop_loss_pct": 0.0679,
            "take_profit_pct": 0.1692,
        },
    },
    "80": {
        "id": "SUPERTREND_PRO_BTC_4H_V2",
        "desc": "Supertrend Pro for BTC (4H, v2 — default params, validated). Sharpe -0.68, ROI -47.1%, MDD 52.6%, 52 trades (BAD). PF=0.50.",

        "class": "SupertrendProStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 14,
            "rsi_low": 30,
            "rsi_high": 70
        }
    },
    "69": {
        "id": "VWAP_RSI_REVERSION_BTC_1H",
        "desc": "VWAP RSI Reversion (BTC 1H, quick backtest). Sharpe -0.29, ROI -12.0%, MDD 14.6%, 40 trades (BAD). PF=0.66.",

        "class": "VWAPRSIReversionStrategy",
    "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vwap_deviation_pct": 0.02, "rsi_period": 17, "rsi_oversold": 36.8798,
            "rsi_overbought": 75.8611, "adx_period": 7, "adx_thresh": 30.0,
            "sl_pct": 0.1654, "max_hold_bars": 158
        },
    },
    "74": {
    "id":   "HARMONIC_DIVERGENCE_BTC_4H",
    "desc": "Harmonic Divergence Strategy (BTC 4H, prototype). Sharpe -0.02, ROI -27.3%, MDD 51.1%, 171 trades (BAD). PF=1.02.",

    "class": "HarmonicDivergenceStrategy",
    "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "rsi_period": 6,
        "divergence_lookback": 14,
        "oversold_threshold": 35,
        "overbought_threshold": 70,
        "take_profit_pct": 0.16,
        "stop_loss_pct": 0.0985
    },
    },
            "75": {
        "id": "SCAN_NEW_TEST_STRATEGY",
        "desc": "Testing Scan New Logic (clone of 82). Sharpe -0.08, ROI -46.0%, MDD 67.5%, 192 trades (BAD). PF=0.96.",

        "class": "HarmonicDivergenceStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 15,
            "divergence_lookback": 6,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "take_profit_pct": 0.1576,
            "stop_loss_pct": 0.0539
        },
    },
    "76": {
        "id": "NOWO_ICHIMOKU_MTF_BTC_5M",
        "desc": "Nowo Ichimoku MTF (5m execution, 1h trend filter). Sharpe -3.25, ROI -100.0%, MDD 100.0%, 4251 trades (BAD). PF=0.23.",

        "class": "NowoIchimokuMTFStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "tenkan_period": 5, "kijun_period": 22, "senkou_b_period": 187,
            "displacement": 26, "informative_tf": "1h",
            "sl_atr_mult": 2.6857, "tp_rr": 20.664, "signal_mode": "CONSERVATIVE", "exit_mode": "CLOUD_CROSS",
            "atr_period": 45
        },
    },
    "77": {
        "id": "SUPERTREND_ATR_MOMENTUM_BTC_4H",
        "desc": "Supertrend ATR Momentum (BTC 4H, trend breakout). Sharpe -0.10, ROI -23.1%, MDD 45.1%, 180 trades (BAD). PF=0.96.",

        "class": "SupertrendATRMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period": 30, "st_multiplier": 1.8619, "adx_period": 9,
            "adx_threshold": 27.5287, "atr_period": 6, "tp_atr_mult": 3.9746, "sl_atr_mult": 2.5038
        },
    },
    "78": {
        "id": "MULTI_TF_MOMENTUM_REVERSAL_BTC_4H",
        "desc": "Multi-Timeframe Momentum-Reversal Strategy (BTC 4H, prototype). Sharpe -0.81, ROI -89.4%, MDD 94.2%, 898 trades (BAD). PF=0.92.",

        "class": "MultiTFMomentumReversalStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "short_momentum_period": 15,
            "long_reversal_period": 90,
            "williams_r_period": 14,
            "tsi_fast_period": 13,
            "tsi_slow_period": 25,
            "chop_period": 14,
            "momentum_threshold_entry": 0.008,
            "reversal_threshold_entry": 0.04,
            "williams_r_oversold": -80,
            "williams_r_overbought": -20,
            "tsi_oversold": -20,
            "tsi_overbought": 20,
            "chop_overbought": 61.8,
            "chop_oversold": 38.2,
            "take_profit_pct": 0.1883,
            "stop_loss_pct": 0.0138,
        },
    },
    "79": {
        "id": "GOLDEN_ZONE_FIB_BOS_BTC_1H",
        "desc": "Golden Zone Fibonacci BOS Strategy (BTC 1H, prototype). Sharpe -0.47, ROI -58.6%, MDD 67.0%, 188 trades (BAD). PF=0.81.",

        "class": "GoldenZoneFibBOSStrategy",
    "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "swing_window": 24,
            "fib_retrace": 0.731,
            "fib_ext": 2.1687,
            "sl_fib": 1.2724,
            "rsi_period": 12,
            "rsi_long": 43,
            "rsi_short": 62
        },
    },
    "180": {
        "id": "GRID_TRADING_BTC",
        "desc": "Grid Trading Strategy for BTC (Prototype). Sharpe -0.76, ROI -2.8%, MDD 3.0%, 127 trades (BAD). PF=0.79.",

        "class": "GridTradingBTCStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 10000, "risk_per_trade": 0.05, "leverage": 1,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "grid_levels": [28000, 29000, 30000, 31000, 32000],
            "grid_spacing": 1000,
            "order_size": 0.001,
            "stop_loss_pct": 0.0437,
            "initial_balance": 10000
        },
    },
    "181": {
        "id":   "TIME_SERIES_MOMENTUM_BTC_4H",
        "desc": "Time-Series Momentum Strategy (BTC 4H, prototype). Sharpe -1.00, ROI -97.0%, MDD 97.8%, 3443 trades (BAD). PF=0.89.",

        "class": "TimeSeriesMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "momentum_period": 30,
            "momentum_threshold_entry": 0.003,
            "take_profit_pct": 0.04,
            "stop_loss_pct": 0.005
        },
    },
    "81": {
        "id":   "MULTI_TF_RSI_MACD_DIV_BTC_1H",
        "desc": "Multi-TF RSI/MACD Divergence Strategy (BTC 1H, 800 EMA HTF filter). Sharpe -0.32, ROI -13.9%, MDD 23.3%, 37 trades (BAD). PF=0.85.",

        "class": "MultiTFRSIMACDDivergenceStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "htf_ema_period": 800,
            "rsi_period": 15,
            "macd_fast": 5,
            "macd_slow": 39,
            "macd_signal": 13,
            "lookback": 40,
            "sl_pct": 0.0281,
            "tp_pct": 0.0709
        },
    },
    "82": {
        "id":   "MULTI_TF_RSI_MACD_DIV_BNB_1H",
    "desc": "Multi-TF RSI/MACD Divergence Strategy (BNB 1H). Sharpe +0.59, ROI +25.1%, MDD 14.8%, 38 trades (MEDIOCRE). PF=1.42.",

    "class": "MultiTFRSIMACDDivergenceStrategy",
    "data": {"coins": "BNB", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-01"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "htf_ema_period": 800, "rsi_period": 12, "macd_fast": 4, "macd_slow": 40, "macd_signal": 3,
        "lookback": 43, "sl_pct": 0.0174, "tp_pct": 0.0772
    },
},
    "83": {
        "id":   "RWA_MOMENTUM_BTC_4H",
        "desc": "RWA Momentum Strategy (BTC 4H) — optimized:. Sharpe +0.11, ROI +1.0%, MDD 56.7%, 85 trades (BAD). PF=1.03.",

        "class": "RWAMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast": 27, "ema_slow": 61,
            "breakout_lookback": 10, "vol_ma_period": 43, "vol_multiplier": 1.6592,
            "rsi_period": 8, "rsi_min": 45.0, "rsi_max": 80.0,
            "atr_period": 29, "atr_contraction_period": 20,
            "tp_atr_mult": 2.975, "sl_atr_mult": 2.4767, "max_hold_bars": 121,
        },
    },
    "85": {
        "id":   "DONCHIAN_BREAKOUT_BTC_4H",
        "desc": "Donchian Channel Breakout (BTC 4H) — classic Turtle Trader breakout. Sharpe -1.37, ROI -82.7%, MDD 84.8%, 532 trades (BAD). PF=0.72.",

        "class": "DonchianBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "lookback": 7, "vol_ma_period": 48, "vol_multiplier": 1.6514,
            "atr_period": 29, "atr_multiplier_sl": 0.0032, "tp_atr_mult": 7.6708, "max_hold_bars": 20,
            "adx_period": 7, "adx_threshold": 15.8315,
        },
    },
    "84": {
        "id":   "RWA_MOMENTUM_ETH_4H",
        "desc": "RWA Momentum Strategy (ETH 4H) — EMA trend + ATR consolidation + volume breakout. Sharpe +0.72, ROI +131.8%, MDD 54.0%, 49 trades (MEDIOCRE). PF=1.33.",

        "class": "RWAMomentumStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "ema_fast": 25, "ema_slow": 124,
            "breakout_lookback": 20, "vol_ma_period": 45, "vol_multiplier": 1.8744,
            "rsi_period": 16, "rsi_min": 50.0, "rsi_max": 75.0,
            "atr_period": 21, "atr_contraction_period": 20,
            "tp_atr_mult": 5.9532, "sl_atr_mult": 2.5874, "max_hold_bars": 188,
        },
    },
    "86": {
        "id":   "TIP_BREAKOUT_ETH_1H",
        "desc": "Taker-Intensity Participation Breakout (ETH, 1H). Sharpe +0.09, ROI -4.7%, MDD 68.8%, 373 trades (BAD). PF=1.01.",

        "class": "TIPBreakoutStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        46,
            "bb_std":           1.1743,
            "intensity_period": 24,
            "intensity_std":    2.8712,
            "taker_threshold":  0.5541,
            "sl_atr_mult":      1.77,
            "tp_atr_mult":      3.7271,
            "max_hold_bars":    157,
        },
    },
    "87": {
        "id":   "VWAP_ATR_REVERSION_BTC_1H",
        "desc": "VWAP Mean Reversion (BTC, 1H) - Paper Trade Port. Sharpe +0.81, ROI +3.5%, MDD 1.1%, 13 trades (BAD). PF=3.20.",

        "class": "VWAPATRReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.015, "leverage": 5,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "multiplier": 2.895, "sl_multiplier": 5.954, "atr_period": 82,
            "max_hold_bars": 424, "ema_slope_thresh": 0.4465,
            "use_pattern_filter": True, "use_vol_filter": True, "exit_mode": "ATR_TRAILING",
        },
    },
    "88": {
        "id": "NOWO_ICHIMOKU_MTF_BTC_1H",
        "desc": "Nowo Ichimoku MTF (1h execution, 4h trend filter). Sharpe -0.76, ROI -90.9%, MDD 91.7%, 689 trades (BAD). PF=0.80.",

        "class": "NowoIchimokuMTFStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "tenkan_period": 7, "kijun_period": 38, "senkou_b_period": 47,
            "displacement": 26, "informative_tf": "4h",
            "sl_atr_mult": 2.7802, "tp_rr": 21.4376, "signal_mode": "CONSERVATIVE", "exit_mode": "CLOUD_CROSS", "atr_period": 47
        },
    },
    "89": {
        "id": "NOWO_ICHIMOKU_MTF_BTC_4H",
        "desc": "Nowo Ichimoku MTF (4h execution, 1d trend filter). Sharpe +0.48, ROI +81.5%, MDD 48.3%, 101 trades (MEDIOCRE). PF=1.34.",

        "class": "NowoIchimokuMTFStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "tenkan_period": 12, "kijun_period": 18, "senkou_b_period": 109,
            "displacement": 26, "informative_tf": "1d",
            "sl_atr_mult": 2.4556, "tp_rr": 24.584, "signal_mode": "HTF_CLOUD_ONLY", "exit_mode": "CLOUD_CROSS", "atr_period": 28
        },
    },
    "90": {
        "id": "ETH_MOMENTUM_BREAKOUT_1H",
        "desc": "ETH Momentum Breakout (1h execution, squeeze + volume). Sharpe +0.04, ROI -2.2%, MDD 28.7%, 29 trades (BAD). PF=1.01.",

        "class": "ETHMomentumBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "squeeze_duration": 3,
            "entry_confirmation": "VOLUME_SPIKE",
            "exit_strategy": "ATR_TRAILING_STOP",
            "bb_period": 45, "bb_std": 2.2327, "kc_period": 20, "kc_mult": 1.5,
            "rsi_period": 13, "atr_period": 8,
        },
    },
    "91": {
    "id":   "CHOPPINESS_KELTNER_BREAKOUT",
    "desc": "Choppiness Index & Keltner Channel Breakout Strategy. Sharpe -2.00, ROI -98.5%, MDD 98.6%, 1017 trades (BAD). PF=0.56.",

    "class": "ChoppinessKeltnerBreakoutStrategy",
    "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "chop_period": 14, "kc_period": 20, "kc_mult": 2.0,
        "chop_threshold": 50.0, "sl_atr_multiplier": 2.6586
    },
    },
    "92": {
    "id": "ORDER_BLOCK_SMC_BTC_4H_V2_A",
    "desc": "Order Block (SMC) Reversal Strategy (BTC 4H, Refined). Sharpe -0.23, ROI -13.7%, MDD 28.7%, 57 trades (BAD). PF=0.89.",

    "class": "OrderBlockSMCStrategy",
    "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "lookback": 20, "ob_volume_mult": 2.9013, "tp_rr": 3.1671
    },
    },
    "93": {
    "id": "SMC_ORDER_BLOCK_REVERSAL_BTC_1H_A",
    "desc": "Order Block (SMC) Reversal Strategy (BTC 1H, Library-based). Sharpe -1.90, ROI -89.2%, MDD 89.6%, 359 trades (BAD). PF=0.82.",

    "class": "SMCOrderBlockReversal",
    "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
    "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
             "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
    "params": {
        "atr_period": 23, "atr_multiplier": 1.2135, "tp_pct": 0.048, "sl_pct": 0.0551
    },
    },
    "94": {
        "id": "ETH_MOMENTUM_BREAKOUT_1H_V2",
        "desc": "ETH Momentum Breakout (1H, BB + KC Squeeze, ETH coin). Sharpe -0.02, ROI -9.9%, MDD 35.8%, 93 trades (BAD). PF=0.90.",

        "class": "ETHMomentumBreakoutStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":           16,
            "bb_std":              3.3453,
            "kc_period":           20,
            "kc_mult":             1.5,
            "rsi_period":          18,
            "atr_period":          14,
            "tp_rr":               11.6536,
            "squeeze_duration":    3,
            "entry_confirmation":  "RSI_FILTER",
            "exit_mode":           "FIXED_RR",
        },
    },
    "95": {
        "id":   "CHOPPINESS_KELTNER_BTC_1H",
        "desc": "Choppiness Keltner Breakout (1H, BTC). Sharpe -2.00, ROI -98.5%, MDD 98.6%, 1017 trades (BAD). PF=0.56.",

        "class": "ChoppinessKeltnerBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "chop_period":       14,
            "kc_period":         20,
            "kc_mult":           2.0,
            "chop_threshold":    50.0,
            "sl_atr_multiplier": 2.6586,
        },
    },
    "96": {
        "id":   "ORDER_BLOCK_SMC_BTC_4H_V2",
        "desc": "Order Block SMC Strategy (4H, BTC) v2. Sharpe -0.23, ROI -13.7%, MDD 28.7%, 57 trades (BAD). PF=0.89.",

        "class": "OrderBlockSMCStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "lookback":        20,
            "ob_volume_mult":  2.9013,
            "tp_rr":           3.1671,
        },
    },
    "97": {
        "id":   "SMC_ORDER_BLOCK_REVERSAL_BTC_1H",
        "desc": "SMC Order Block Reversal (1H, BTC). Sharpe -1.90, ROI -89.2%, MDD 89.6%, 359 trades (BAD). PF=0.82.",

        "class": "SMCOrderBlockReversal",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":     23,
            "atr_multiplier": 1.2135,
            "tp_pct":         0.048,
            "sl_pct":         0.0551,
        },
    },
    "98": {
        "id":   "ETH_MOMENTUM_BREAKOUT_1H_V3",
        "desc": "ETH Momentum Breakout (1H, ETH) v3. Sharpe -1.20, ROI -23.9%, MDD 27.8%, 34 trades (BAD). PF=0.34.",

        "class": "ETHMomentumBreakoutStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":           24,
            "bb_std":              2.8323,
            "kc_period":           20,
            "kc_mult":             1.5,
            "rsi_period":          15,
            "atr_period":          20,
            "tp_rr":               2.2541,
            "squeeze_duration":    8,
            "entry_confirmation":  "RSI_FILTER",
            "exit_mode":           "FIXED_RR",
        },
    },
    "99": {
        "id":   "RSI_DIVERGENCE_REVERSAL_BTC_4H",
        "desc": "RSI Divergence Reversal — bullish/bearish price-RSI divergence with taker confirmation (BTC 4H). Sharpe +0.03, ROI -7.7%, MDD 39.5%, 62 trades (BAD). PF=0.98.",

        "class": "RSIDivergenceReversalStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 21, "lookback": 14, "pivot_window": 3,
            "rsi_threshold_low": 48, "rsi_threshold_high": 60,
            "taker_threshold": 0.4929, "tp_rsi": 64, "sl_atr_mult": 3.6708,
            "mode": "short_only", "use_taker_filter": True,
        },
    },
    "100": {
        "id":   "RSI_REVERSION_BTC_1H",
        "desc": "Simple RSI Mean Reversion — long below oversold, short above overbought (BTC 1H). Sharpe -0.53, ROI -70.5%, MDD 79.7%, 194 trades (BAD). PF=0.80.",

        "class": "RSIReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 9, "rsi_oversold": 38, "rsi_overbought": 73,
            "ema_period": 62, "atr_period": 10, "atr_multiplier_sl": 0.6644,
            "mode": "ema200",
        },
    },
    "101": {
        "id":   "RSI_EMA_CROSSOVER_BTC_1H",
        "desc": "RSI-filtered EMA Crossover — fast/slow EMA cross with RSI momentum gate (BTC 1H). Sharpe -1.23, ROI -93.5%, MDD 95.0%, 405 trades (BAD). PF=0.69.",

        "class": "RsiEmaCrossoverStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 15, "ema_fast": 12, "ema_slow": 90,
            "rsi_oversold": 50, "rsi_overbought": 76,
            "atr_period": 14, "atr_multiplier_sl": 2.4792,
            "mode": "momentum",
        },
    },
    "102": {
        "id":   "SQUEEZE_MOMENTUM_BTC_4H",
        "desc": "Squeeze Momentum — BB/KC squeeze with taker intensity confirmation (BTC 4H). Sharpe -0.37, ROI -61.9%, MDD 75.1%, 359 trades (BAD). PF=0.91.",

        "class": "SqueezeMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        29,
            "bb_std":           2.5105,
            "intensity_period": 8,
            "intensity_std":    1.5203,
            "taker_threshold":  0.5331,
            "sl_atr_mult":      2.2611,
            "tp_atr_mult":      7.2605,
            "max_hold_bars":    34,
        },
    },
    "103": {
        "id":   "DYNAMIC_VWAP_ATR_SCALPER_BTC_1H",
        "desc": "Dynamic VWAP ATR Scalper (1H, BTC). Sharpe -0.94, ROI -18.7%, MDD 20.8%, 35 trades (BAD). PF=0.44.",

        "class": "DynamicVWAPATRScalperStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_period":        19,
            "atr_multiplier":    1.408,
            "rsi_period":        29,
            "rsi_oversold":      27.3103,
            "rsi_overbought":    78.7521,
            "vol_ma_period":     12,
            "vol_multiplier":    2.6575,
            "atr_multiplier_sl": 1.0793,
            "max_hold_bars":     65,
            "mode":              "reversion",
        },
    },
    "104": {
        "id":   "VOLUME_PRICE_CORR_EXTREMAS_V2_BTC_4H",
        "desc": "Volume-Price Correlation Extremas v2 — dual-window correlation signal with momentum/reversal modes (BTC 4H). Sharpe +0.18, ROI -15.3%, MDD 69.8%, 226 trades (BAD). PF=1.01.",

        "class": "VolumePriceCorrelationExtremasStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "window_1": 25, "window_2": 30, "alpha_threshold": 0.5047,
            "mode": "reversion", "atr_period": 20,
            "tp_multiplier": 5.9141, "sl_multiplier": 2.8397,
        },
    },
    "105": {  # mode added; OPTIMIZATION_RANGES will let Optuna switch it
        "id":   "TRIPLE_CONFIRM_FVMA_BTC_4H",
        "desc": "Triple Confirmation FVMA — Zero-lag MACD + SuperTrend + FVMA triple-confirm entries (BTC 4H). Sharpe -0.45, ROI -63.0%, MDD 81.5%, 372 trades (BAD). PF=0.89.",

        "class": "TripleConfirmFVMAStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "supertrend_length": 10, "supertrend_multiplier": 4.5104,
            "fvma_period": 3, "macd_fast": 15, "macd_slow": 45, "macd_signal": 10,
            "tp_atr_mult": 3.2155, "sl_atr_mult": 2.1828,
            "mode": "macd_st",
        },
    },
    "106": {
        "id": "MTF_SUPPORT_SNIPER_BTC_5M",
        "desc": "MTF Support Sniper (5m execution at 1D/4H macro support). Sharpe +0.12, ROI +1.6%, MDD 5.2%, 43 trades (BAD). PF=1.13.",

        "class": "MTFSupportSniperStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "htf_vwap_period": 1262,
            "htf_ema_period": 2131,
            "zone_pct": 0.0171,
            "vrsi_period": 19,
            "vrsi_oversold": 28.8642,
            "sl_pct": 0.0267,
            "tp_pct": 0.1881,
            "max_hold_bars": 669
        }
    },
    "107": {
        "id": "LORENTZIAN_CLASS_MOMENTUM",
        "desc": "Lorentzian Classification Momentum Strategy",
        "class": "LorentzianClassificationMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-05-31", "date_to": "2026-05-31"},

        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "k_neighbors": 5,
            "history_window": 2000,
            "rsi_period": 14,
            "cci_period": 14,
            "adx_period": 14,
            "ema_period": 200,
            "adx_threshold": 20,
            "entry_filter": "ADX_ABOVE_20",
            "exit_mode": "ATR_TRAILING_STOP",
            "tp_rr": 2.0,
            "sl_atr_mult": 1.0
        }
    },
    "108": {
        "id": "INSTITUTIONAL_MOMENTUM_CONSOLIDATION_BREAKOUT",
        "desc": "Institutional Momentum Consolidation Breakout Strategy. Sharpe -0.46, ROI -7.0%, MDD 11.0%, 23 trades (BAD). PF=0.59.",

        "class": "InstitutionalMomentumConsolidationBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast_ema": 9, "slow_ema": 100, "bb_period": 30, "bb_std": 3.3237,
            "kc_period": 30, "kc_mult": 1.9301, "min_consolidation": 3, "vol_ma_period": 20,
            "tp_atr_mult": 2.0335, "exit_mode": "FIXED_RR"
        }
    },
    "109": {
        "id": "Z_SCORE_STAT_ARB_1H",
        "desc": "Z-Score Statistical Arbitrage — mean-reversion with candle confirm + trend filter (1H). Sharpe -1.38, ROI -29.8%, MDD 30.9%, 36 trades (BAD). PF=0.26.",

        "class": "ZScoreStatArbStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "z_period": 95, "z_threshold": 2.0022, "sl_atr_mult": 2.7657,
            "use_candle_confirm": False, "trend_filter_period": 200
        }
    },
    "110": {
        "id": "TAKER_BUY_INTENSITY_MOMENTUM",
        "desc": "Taker Buy Intensity Momentum Strategy. Sharpe -1.01, ROI -84.4%, MDD 87.9%, 295 trades (BAD). PF=0.74.",

        "class": "TakerBuyIntensityMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "taker_ratio_threshold": 0.6171,
            "vol_ma_period": 48,
            "trend_ema_period": 73,
            "atr_period": 6,
            "atr_multiplier_tp": 8.5221,
            "atr_multiplier_sl": 2.8861,
            "exit_mode": "ATR_ONLY"
        }
    },
    "111": {
        "id": "ETH_MOMENTUM_SQUEEZE",
        "desc": "ETH Momentum Bollinger Keltner Squeeze. Sharpe -0.68, ROI -29.8%, MDD 33.3%, 84 trades (BAD). PF=0.67.",

        "class": "ETHMomentumSqueezeStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        21,
            "bb_std":           2.9261,
            "intensity_period": 24,
            "intensity_std":    2.1973,
            "taker_threshold":  0.5312,
            "sl_atr_mult":      0.89,
            "tp_atr_mult":      1.4066,
            "max_hold_bars":    175,
        },
    },
    "112": {
        "id":   "LORENTZIAN_MOMENTUM_BTC_1H",
        "desc": "Lorentzian Classification Momentum (1H, BTC). Sharpe -19.59, ROI -100.0%, MDD 100.0%, 4485 trades (BAD). PF=0.02.",
        "class": "LorentzianClassificationMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "k_neighbors":     5,
            "history_window":  2000,
            "rsi_period":      14,
            "cci_period":      14,
            "adx_period":      14,
            "ema_period":      200,
            "adx_threshold":   20,
            "entry_filter":    "ADX_ABOVE_20",
            "exit_mode":       "ATR_TRAILING_STOP",
            "tp_rr":           2.0,
            "sl_atr_mult":     1.0,
            "invert_signals":  True
        },
    },

    "113": {
        "id":   "FORGE_ETH_BB_BREAKOUT_EMA_ATR",
        "desc": "Forge #2 — ETH 4H BB breakout + EMA trend filter, ATR exit. 190% ROI,. Sharpe +0.79, ROI +107.0%, MDD 33.1%, 150 trades (MEDIOCRE). PF=1.30.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "bb_breakout",
            "filters":     ["ema_trend_long"],
            "exit_method": "atr_tp_sl",
            "bb_period":    32,
            "bb_std":       2.2014,
            "atr_period":    8,
            "tp_atr_mult":   3.2101,
            "sl_atr_mult":   1.4482,
            "ema_trend":    99,
        },
    },

    "114": {
        "id":   "FORGE_ETH_RSI_TREND_STABLE",
        "desc": "Forge #3 — ETH 4H RSI trend + ATR expansion + EMA filter, RR exit. Lowest MDD 23%,. Sharpe +0.15, ROI +3.1%, MDD 33.6%, 68 trades (BAD). PF=1.05.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "rsi_trend",
            "filters":     ["atr_expansion", "ema_trend_long"],
            "exit_method": "rr_ratio",
            "rsi_period":    8,
            "rsi_threshold": 33,
            "atr_period":    24,
            "vol_ma_period": 22,
            "ema_trend":     233,
            "sl_pct":        0.1325,
            "tp_rr":         4.69,
        },
    },

    "115": {
        "id":   "FORGE_ETH_HMA_STDIR_ATR_HOLD",
        "desc": "Forge #4 — ETH 4H HMA cross (new) + Supertrend dir filter, ATR+hold exit. 283% ROI,. Sharpe +0.64, ROI +112.9%, MDD 51.6%, 130 trades (MEDIOCRE). PF=1.19.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "hma_cross",
            "filters":     ["supertrend_dir"],
            "exit_method": "atr_tp_sl_hold",
            "ema_fast":       12,
            "ema_slow":      183,
            "st_period":      27,
            "st_multiplier":  3.4483,
            "atr_period":     14,
            "sl_atr_mult":    2.6263,
            "tp_atr_mult":    7.9901,
            "max_hold_bars":  105,
        },
    },

    "116": {
        "id":   "FORGE_ETH_BB_ATR_STABLE",
        "desc": "Forge #5 — ETH 4H BB breakout, ATR TP/SL. 279% ROI,. Sharpe +0.97, ROI +147.1%, MDD 33.7%, 180 trades (MEDIOCRE). PF=1.41.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "bb_breakout",
            "filters":     [],
            "exit_method": "atr_tp_sl",
            "bb_period":    40,
            "bb_std":       2.6586,
            "atr_period":    7,
            "tp_atr_mult":   3.1624,
            "sl_atr_mult":   0.5059,
        },
    },

    "117": {
        "id":   "FORGE_ETH_CVD_CHANDELIER",
        "desc": "Forge #6 — ETH 4H CVD cross + vol filter, chandelier+TP exit. 203% ROI,. Sharpe +1.83, ROI +162.4%, MDD 13.5%, 37 trades (MEDIOCRE). PF=3.50.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "cvd_cross",
            "filters":     ["vol_expansion"],
            "exit_method": "chandelier_tp",
            "cvd_window":     22,
            "vol_ma_period":  45,
            "vol_multiplier": 2.5039,
            "atr_period":     18,
            "atr_multiplier": 2.1794,
            "tp_atr_mult":    2.4923,
        },
    },

    "118": {
        "id":   "FORGE_ETH_ELDER_RAY_CHANDELIER",
        "desc": "Forge #7 — ETH 4H Elder Ray (new) + vol+squeeze filter, chandelier+TP exit. 123% ROI,. Sharpe +0.30, ROI +22.4%, MDD 39.2%, 83 trades (MEDIOCRE). PF=1.10.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "elder_ray",
            "filters":     ["vol_expansion", "no_squeeze"],
            "exit_method": "chandelier_tp",
            "period":        29,
            "adx_period":    16,
            "adx_threshold": 24,
            "vol_ma_period": 32,
            "vol_multiplier":1.2585,
            "bb_period":     28,
            "bb_std":        3.1888,
            "kc_window":     22,
            "kc_multiplier": 3.1986,
            "atr_period":    30,
            "atr_multiplier":4.3241,
            "tp_atr_mult":   5.5329,
        },
    },

    # ── strategy_forge v2 — new indicators (HMA, Vortex, Elder Ray, Williams %R filter) ──

    "119": {
        "id":   "FORGE_ETH_HMA_TIGHT_ATR",
        "desc": "Forge #8 — ETH 4H HMA cross (new) + ATR expansion. Sharpe +0.84, ROI +223.8%, MDD 50.4%, 127 trades (MEDIOCRE). PF=1.22.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "hma_cross",
            "filters":     ["atr_expansion"],
            "exit_method": "tight_atr",
            "ema_fast":       28,
            "ema_slow":       90,
            "atr_period":     15,
            "vol_ma_period":  31,
            "sl_atr_mult":    2.6821,
            "tp_atr_mult":    6.8668,
        },
    },

    "120": {
        "id":   "FORGE_ETH_FVG_TAKER_WR_ATR",
        "desc": "Forge #9 — ETH 4H FVG + Taker + Williams R filter (new). Sharpe +0.98, ROI +301.8%, MDD 54.3%, 290 trades (MEDIOCRE). PF=1.23.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "fvg",
            "filters":     ["taker_confirm", "wr_not_extreme"],
            "exit_method": "atr_tp_sl_hold",
            "atr_period":      24,
            "intensity_period":13,
            "period":          43,
            "tp_atr_mult":     4.6029,
            "sl_atr_mult":     1.9697,
            "max_hold_bars":  140,
        },
    },

    "121": {
        "id":   "FORGE_BTC_ELDER_RAY_ATR_HOLD",
        "desc": "Forge #10 — BTC 4H Elder Ray indicator (new) + ATR expansion, max-hold exit. Sharpe +0.39, ROI +38.3%, MDD 55.6%, 72 trades (MEDIOCRE). PF=1.14.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "elder_ray",
            "filters":     ["atr_expansion"],
            "exit_method": "max_hold",
            "period":         49,
            "adx_period":     14,
            "adx_threshold":  22,
            "atr_period":     17,
            "vol_ma_period":  25,
            "max_hold_bars": 119,
        },
    },

    "122": {
        "id":   "FORGE_ETH_EMA_WR_SHORT_TIGHT",
        "desc": "Forge #11 — ETH 4H EMA cross + Williams R filter (new) + EMA short filter, tight ATR. Sharpe +0.90, ROI +155.6%, MDD 26.4%, 79 trades (MEDIOCRE). PF=1.40.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "ema_price_cross",
            "filters":     ["wr_not_extreme", "ema_trend_short"],
            "exit_method": "tight_atr",
            "ema_period":    142,
            "ema_trend":     170,
            "period":         42,
            "atr_period":     16,
            "sl_atr_mult":    2.2999,
            "tp_atr_mult":    6.5362,
        },
    },

    "123": {
        "id":   "FORGE_ETH_AROON_VORTEX_EMA_TIGHT",
        "desc": "Forge #12 — ETH 4H Aroon cross + Vortex filter (new) + EMA trend, tight ATR exit. Sharpe +0.11, ROI -10.6%, MDD 47.2%, 345 trades (BAD). PF=1.01.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2022-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.10, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":       "aroon_cross",
            "filters":     ["vortex_trend", "ema_trend_long"],
            "exit_method": "tight_atr",
            "aroon_period":   37,
            "aroon_threshold":75,
            "vortex_period":  19,
            "ema_trend":     294,
            "atr_period":     18,
            "sl_atr_mult":    1.0038,
            "tp_atr_mult":    6.6457,
        },
    },

    "124": {
        "id":   "FORGE_ETH_MTF_EMA_CROSS",
        "desc": "Forge MTF #1 — ETH 1H EMA(8/21) cross + 4H HTF EMA trend filter (genuine MTF) + Taker confirm. Sharpe +0.74, ROI +79.0%, MDD 22.2%, 262 trades (MEDIOCRE). PF=1.25.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2022-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.06, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "ema_cross",
            "filters":        ["htf_ema_trend", "taker_confirm"],
            "exit_method":    "atr_tp_sl_hold",
            "ema_fast":        8,
            "ema_slow":        21,
            "htf_bars":        4,
            "htf_ema_period":  50,
            "intensity_period":13,
            "atr_period":      14,
            "tp_atr_mult":     10.0,
            "sl_atr_mult":     3.0,
            "max_hold_bars":   96,
        },
    },

    "125": {
        "id":   "FORGE_ETH_IMB_SNIPER",
        "desc": "Forge IMB Sniper #1 — ETH 4H Imbalance Zone (new indicator, thr=0.002) + Taker confirm + WR filter. Ultra-selective 0.2/wk, every signal is high-conviction. Sharpe +0.92, ROI +146.8%, MDD 19.4%, 54 trades (MEDIOCRE). PF=1.77.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.14, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":           "imbalance_zone",
            "filters":         ["taker_confirm", "wr_not_extreme"],
            "exit_method":     "atr_tp_sl_hold",
            "imb_threshold":   0.002,
            "intensity_period": 13,
            "period":          43,
            "atr_period":      24,
            "tp_atr_mult":     4.6,
            "sl_atr_mult":     1.97,
            "max_hold_bars":   140,
        },
    },

    # ── Sniper-Swing strategies (IDs 131–138) ────────────────────────────────
    # LTF entry (5m/15m) + HTF bias filter + forced max_hold exit (1h–4h)
    # Architecture: precision entry on LTF → hold 1-4 hours → forced sell
    # htf_bars: number of base-TF bars to resample for HTF filter
    #   5m  → 4h = 48 bars | 5m  → 1h = 12 bars
    #   15m → 4h = 16 bars | 15m → 1h = 4 bars
    # max_hold_bars enforces the forced sell (12=1h, 24=2h, 48=4h on 5m)
    # ─────────────────────────────────────────────────────────────────────────

    "126": {
        "id":   "SS_BTC_5M_HMA_HTF4H_HOLD2H",
        "desc": "Sniper-Swing A — BTC 5m HMA cross entry, 4H HTF EMA bias + ADX trending filter, forced 2h exit. Precision momentum entry with HTF trend alignment. Sharpe -7.07, ROI -22.9%, MDD 22.9%, 35 trades (BAD). PF=0.00.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2025-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "hma_cross",
            "filters":        ["htf_ema_trend", "adx_trend"],
            "exit_method":    "atr_tp_sl_hold",
            "ema_fast":        17,
            "ema_slow":        196,
            "htf_bars":        48,
            "htf_ema_period":  50,
            "adx_period":      16,
            "adx_threshold":   39.9137,
            "atr_period":      26,
            "tp_atr_mult":     5.7626,
            "sl_atr_mult":     2.8858,
            "max_hold_bars":   19,
        },
    },

    "127": {
        "id":   "SS_BTC_5M_EMA_HTF4H_WR_HOLD4H",
        "desc": "Sniper-Swing B — BTC 5m EMA cross entry, 4H HTF Supertrend bias + WR not-extreme filter, forced 4h exit. Trend-following sniper with mean-reversion guard. Sharpe -21.34, ROI -90.4%, MDD 90.4%, 361 trades (BAD). PF=0.00.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2025-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "ema_cross",
            "filters":        ["htf_supertrend", "wr_not_extreme"],
            "exit_method":    "atr_tp_sl_hold",
            "ema_fast":        11,
            "ema_slow":        173,
            "htf_bars":        48,
            "htf_st_period":   10,
            "htf_st_mult":     3.0,
            "period":          25,
            "atr_period":      5,
            "tp_atr_mult":     6.9625,
            "sl_atr_mult":     2.6478,
            "max_hold_bars":   113,
        },
    },

    "128": {
        "id":   "IMB_BTC_4H_SNIPER",
        "desc": "IMB Sniper #2 — BTC 4H Imbalance Zone (thr=0.002) + Taker confirm + WR filter. Mirror of #130 ETH formula applied to BTC 4H. Ultra-selective ~0.2/wk. Sharpe -0.39, ROI -36.1%, MDD 52.3%, 54 trades (BAD). PF=0.81.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.14, "leverage": 10,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":           "imbalance_zone",
            "filters":         ["taker_confirm", "wr_not_extreme"],
            "exit_method":     "atr_tp_sl_hold",
            "imb_threshold":   0.002,
            "intensity_period": 13,
            "period":          43,
            "atr_period":      24,
            "tp_atr_mult":     4.6,
            "sl_atr_mult":     1.97,
            "max_hold_bars":   140,
        },
    },

    "129": {
        "id":   "SS_ETH_5M_SUPERTREND_LONG_TRAIL_V6",
        "desc": "Sniper-Swing D v6 — ETH 5m ST flip long-only, exit on ST reversal (trail). 6H HTF EMA + ATR expand + OBV volume + ADX>31 quad-filter. ST(27, 2.5x). GOOD grade. Sharpe -0.80, ROI -3.2%, MDD 5.8%, 298 trades (BAD). PF=0.80.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.03, "leverage": 3,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "supertrend",
            "filters":        ["htf_ema_trend", "atr_expansion", "obv_trend", "adx_trend"],
            "exit_method":    "supertrend_trail",
            "direction":      "long_only",
            "st_period":      7,
            "st_multiplier":  4.6433,
            "htf_bars":       72,
            "htf_ema_period": 50,
            "atr_period":     15,
            "vol_ma_period":  45,
            "obv_period":     20,
            "adx_period":     14,
            "adx_threshold":  30,
            "sl_atr_mult":    2.5696,
            "tp_atr_mult":    5.9547,
        },
    },

    "130": {
        "id":   "SS_BTC_15M_STOCHRSI_HTF4H_ADX",
        "desc": "Sniper-Swing E — BTC 15m StochRSI reversal entry, 4H HTF Supertrend bias + ADX trending filter, tight ATR exit capped at 4h. Mean-reversion sniper within trending HTF. Sharpe -11.86, ROI -65.2%, MDD 65.2%, 284 trades (BAD). PF=0.09.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2024-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "stoch_rsi_reversion",
            "filters":        ["htf_supertrend", "adx_trend"],
            "exit_method":    "tight_atr",
            "rsi_period":     15,
            "stoch_period":   3,
            "htf_bars":       16,
            "htf_st_period":  10,
            "htf_st_mult":    3.0,
            "adx_period":     18,
            "adx_threshold":  36.6116,
            "atr_period":     27,
            "sl_atr_mult":    2.5737,
            "tp_atr_mult":    7.0544,
            "max_hold_bars":  151,
        },
    },

    "131": {
        "id":   "SS_ETH_15M_BB_REV_HTF1H_HOLD2H",
        "desc": "Sniper-Swing F — ETH 15m BB lower-band reversion entry, 1H HTF EMA trend + volume expansion filter, forced 2h exit. Volatility expansion sniper. Sharpe +0.04, ROI +0.2%, MDD 7.0%, 74 trades (BAD). PF=1.02.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "15m", "date_from": "2024-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "bb_reversion",
            "filters":        ["htf_ema_trend", "vol_expansion"],
            "exit_method":    "atr_tp_sl_hold",
            "bb_period":      17,
            "bb_std":         3.4612,
            "htf_bars":       4,
            "htf_ema_period": 21,
            "vol_ma_period":  9,
            "atr_period":     27,
            "tp_atr_mult":    9.5636,
            "sl_atr_mult":    2.9293,
            "max_hold_bars":  99,
        },
    },

    "132": {
        "id":   "SS_BTC_15M_WR_REV_HTF4H_HOLD3H",
        "desc": "Sniper-Swing G — BTC 15m Williams %R reversal entry, 4H HTF Supertrend bias, forced 3h exit. Classic momentum-exhaustion sniper. Sharpe -20.54, ROI -96.2%, MDD 96.2%, 1638 trades (BAD). PF=0.17.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2024-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "williams_r_reversion",
            "filters":        ["htf_supertrend"],
            "exit_method":    "atr_tp_sl_hold",
            "period":         50,
            "htf_bars":       16,
            "htf_st_period":  10,
            "htf_st_mult":    3.0,
            "atr_period":     29,
            "tp_atr_mult":    7.8608,
            "sl_atr_mult":    2.6927,
            "max_hold_bars":  152,
        },
    },

    "133": {
        "id":   "SS_BTC_5M_TAKER_HTF4H_HOLD2H",
        "desc": "Sniper-Swing H — BTC 5m Taker buy intensity momentum entry, 4H HTF EMA trend + ATR expansion filter, chandelier exit capped at 2h. Order-flow-driven sniper. Sharpe -23.72, ROI -89.6%, MDD 89.6%, 364 trades (BAD). PF=0.00.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2025-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "slippage_pct": 0.0005, "maintenance_margin_rate": 0.004},
        "params": {
            "entry":          "taker_momentum",
            "filters":        ["htf_ema_trend", "atr_expansion"],
            "exit_method":    "chandelier_tp",
            "intensity_period": 40,
            "htf_bars":       48,
            "htf_ema_period": 50,
            "vol_ma_period":  50,
            "atr_period":     14,
            "tp_atr_mult":    7.5559,
            "sl_atr_mult":    2.941,
            "max_hold_bars":  101,
        },
    },

    "134": {
        "id":   "KFM_BTC_4H",
        "desc": "Kalman Filtered Momentum (KFM) Baseline. Sharpe -0.37, ROI -52.0%, MDD 69.4%, 238 trades (BAD). PF=0.90.",

        "class": "KalmanFilteredMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "noise": 0.0186, "slope_lookback": 5, "slope_threshold": 33.7717, 
            "ema_trend_period": 293, "atr_period": 6, "chandelier_mult": 3.0
        },
    },
    "135": {
        "id":   "CGS_BTC_4H",
        "desc": "Choppiness-Gated Supertrend (CGS) Baseline. Sharpe +0.84, ROI +52.9%, MDD 33.3%, 28 trades (BAD). PF=1.78.",

        "class": "ChoppinessGatedSupertrendStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period": 15, "st_multiplier": 3.842, "chop_period": 14,
            "chop_threshold": 41.8809, "adx_period": 14, "adx_threshold": 21.5031,
            "atr_period": 27, "sl_atr_mult": 2.3014
        },
    },

    "136": {
        "id":   "AVS_BTC_4H",
        "desc": "Adaptive Volatility Squeeze (4H). Sharpe -1.54, ROI -49.6%, MDD 52.0%, 104 trades (BAD). PF=0.52.",

        "class": "AVSStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        43,
            "bb_std":           1.8819,
            "intensity_period": 10,
            "intensity_std":    2.1424,
            "taker_threshold":  0.5156,
            "sl_atr_mult":      2.6885,
            "tp_atr_mult":      4.6749,
            "max_hold_bars":    89,
        },
    },
    "137": {
        "id":   "FORGE_BTC_WR_REVERSION_15M",
        "desc": "Forge — BTC 15M williams_r_reversion + htf_supertrend, atr_tp_sl_hold exit. Sharpe -14.04, ROI -100.0%, MDD 100.0%, 1974 trades (BAD). PF=0.04.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2024-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            "entry":          "williams_r_reversion",
            "filters":        ["htf_supertrend"],
            "exit_method":    "atr_tp_sl_hold",
            "period":         22,
            "htf_bars":       16,
            "htf_st_period":  10,
            "htf_st_mult":    3.0,
            "atr_period":     29,
            "tp_atr_mult":    6.124,
            "sl_atr_mult":    1.9966,
            "max_hold_bars":  41,
        },
    },
    "138": {
        "id":   "FORGE_BTC_TAKER_MOMENTUM_5M",
        "desc": "Forge — BTC 5M taker_momentum + htf_ema_trend + atr_expansion, chandelier_tp exit. Sharpe -16.73, ROI -99.6%, MDD 99.6%, 294 trades (BAD). PF=0.00.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2025-05-31", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            "entry":             "taker_momentum",
            "filters":           ["htf_ema_trend", "atr_expansion"],
            "exit_method":       "chandelier_tp",
            "intensity_period":  41,
            "htf_bars":          48,
            "htf_ema_period":    50,
            "vol_ma_period":     36,
            "atr_period":        19,
            "tp_atr_mult":       6.5313,
            "sl_atr_mult":       3.8596,
            "max_hold_bars":     21,
        },
    },

    "139": {
        "id":   "DUMPREVERSALPEAKTRAIL_BTC_4H",
        "desc": "AUTO-REGISTERED — update description. Sharpe +0.66, ROI +214.4%, MDD 62.4%, 36 trades (MEDIOCRE). PF=3.11.",

        "class": "DumpReversalPeakTrailStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "low_lookback": 28,
            "vol_ma_period": 10,
            "vol_multiplier": 1.775,
            "rsi_period": 23,
            "rsi_threshold": 50.3995,
            "stop_loss_pct": 0.0239,
            "peak_retrace_pct": 0.3688,
        },
    },
    "140": {
        "id":   "RSIMEANREVERSION_BTC_4H",
        "desc": "AUTO-REGISTERED — update description. Sharpe +0.21, ROI +12.0%, MDD 28.7%, 39 trades (BAD). PF=1.13.",

        "class": "RsiMeanReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period": 30,
            "atr_period": 9,
            "rsi_oversold": 26.9188,
            "rsi_overbought": 79.7836,
            "tp_multiplier": 5.9902,
            "sl_multiplier": 0.8799,
        },
    },
    "141": {
        "id":   "TRENDINTENSITYINDEX_BTC_4H",
        "desc": "AUTO-REGISTERED — update description. Sharpe +0.00, ROI -15.0%, MDD 54.1%, 117 trades (BAD). PF=0.98.",

        "class": "TrendIntensityIndexStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {},
    },
    "142": {
        "id":   "FORGE_ETH_EMA_CROSS_1H",
        "desc": "Forge — ETH 1H ema_cross + htf_ema_trend + adx_trend, chandelier_tp exit. Sharpe -0.02, ROI -5.0%, MDD 26.5%, 221 trades (BAD). PF=0.98.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2022-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            "entry":            "ema_cross",
            "filters":          ["htf_ema_trend", "adx_trend"],
            "exit_method":      "chandelier_tp",
            "ema_fast":         16,
            "ema_slow":         116,
            "htf_bars":         7,
            "ema_trend_period": 49,
            "adx_period":       7,
            "adx_threshold":    21,
            "atr_period":       5,
            "atr_multiplier":   5.457,
            "tp_atr_mult":      1.869,
            "sl_atr_mult":      0.586,
            "max_hold_bars":    42,
        },
    },




    "144": {
        "id":    "FORGE_DOT_BB_BREAKOUT_WR_RSI_4H",
        "desc":  "Phase-12 Forge DOT 4H — bb_breakout + wr_not_extreme + rsi_not_extreme + psar_trail | Sharpe=2.10 MDD=8.3% Mo=2.32% 104 trades (2024-2026). Sharpe +2.08, ROI +93.1%, MDD 8.3%, 104 trades (GOOD). PF=2.65.",

        "class": "ForgeStrategy",
        "data":  {"coins": "DOT", "timeframes": "4h", "date_from": "2024-01-01", "date_to": "2026-05-31"},
        "risk":  {"initial_balance": 10000, "risk_per_trade": 0.05, "leverage": 5, "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            'entry': 'bb_breakout',
            'filters': ['wr_not_extreme', 'rsi_not_extreme'],
            'exit_method': 'psar_trail',
            'period': 5,
            'psar_acceleration': 0.0198,
            'psar_maximum': 0.3941,
            'ema_trend': 113,
            'adx_period': 26,
            'adx_threshold': 21,
            'zscore_period': 26,
            'zscore_threshold': 0.5885,
            'htf_bars': 6,
            'htf1_bars': 6,
            'htf2_bars': 42,
            'htf_ema_period': 142,
            'st_period': 25,
            'st_multiplier': 4.1114,
            'aroon_period': 44,
            'aroon_threshold': 56,
            'macro_bars': 168
        },
    },

    "148": {
        "id":    "FORGE_ADA_EMA_CROSS_EMA_TREND_PSAR_1H",
        "desc":  "Phase-12 Forge ADA 1H — ema_cross(15/21) + ema_trend_long(100) + psar_trail | Sharpe=3.62 MDD=3.1% Mo=2.81% 10.7tr/mo 0-loss-months (2024-2026) | OOS: Sharpe=3.63 Mo=2.26%. Sharpe +3.78, ROI +131.8%, MDD 3.0%, 300 trades (GOOD). PF=2.92.",

        "class": "ForgeStrategy",
        "data":  {"coins": "ADA", "timeframes": "1h", "date_from": "2024-01-01", "date_to": "2026-05-31"},
        "risk":  {"initial_balance": 10000, "risk_per_trade": 0.05, "leverage": 5, "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            'entry': 'ema_cross',
            'filters': ['ema_trend_long'],
            'exit_method': 'psar_trail',
            'ema_fast': 15,
            'ema_slow': 21,
            'ema_trend': 100,
            'psar_acceleration': 0.025,
            'psar_maximum': 0.15
        },
    },
    "149": {
        "id":   "TIP_BREAKOUT_ETH_1H_149",
        "desc": "Standalone Taker-Intensity Participation (TIP) Breakout. 1h ETH volume strategy. Sharpe -0.63, ROI -8.7%, MDD 13.1%, 246 trades (BAD). PF=0.85.",

        "class": "TIPBreakoutStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 10000, "risk_per_trade": 0.05, "leverage": 5,
                 "trading_fee": 0.0004, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        15,
            "bb_std":           3.4193,
            "intensity_period": 28,
            "intensity_std":    2.8301,
            "taker_threshold":  0.5572,
            "sl_atr_mult":      1.2012,
            "tp_atr_mult":      7.7773,
            "max_hold_bars":    52,
        },
    },
    "150": {
        "id": "EFR_MR_BTC_4H",
        "desc": "Extreme Funding Rate Mean Reversion (EFR-MR). Sharpe +0.64, ROI +4.5%, MDD 1.8%, 1 trades (BAD). PF=99.00.",

        "class": "EFRMRStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fr_zscore_period": 95, "fr_zscore_thresh": 2.3294, "spot_obi_thresh": 0.1553,
            "use_obi_filter": False, "tp_multiplier": 3.353, "sl_multiplier": 1.5247
        },
    },
    "151": {
        "id": "LER_BTC_4H",
        "desc": "Liquidity Exhaustion Reversal (LER). Sharpe +0.77, ROI +39.6%, MDD 16.1%, 36 trades (MEDIOCRE). PF=1.60.",

        "class": "LERStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period": 27, "bb_std": 2.3042, "depth_lookback": 135,
            "depth_perc_long": 0.1, "depth_perc_short": 0.9,
            "use_depth_filter": True, "tp_multiplier": 3.9506, "sl_multiplier": 2.3876
        },
    },
    "152": {
        "id": "FRDS_BTC_4H",
        "desc": "Funding Rate Divergence Squeeze (FRDS). Sharpe -0.97, ROI -65.6%, MDD 74.0%, 259 trades (BAD). PF=0.78.",

        "class": "FRDSStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "trend_period": 22, "use_spot_obi": True, "use_regime_filter": True,
            "tp_multiplier": 4.6339, "sl_multiplier": 1.1365
        },
    },
    "153": {
        "id": "FRDS_BTC_1H",
        "desc": "Funding Rate Divergence Squeeze (FRDS) on 1H Timeframe. Sharpe -2.50, ROI -97.2%, MDD 98.2%, 680 trades (BAD). PF=0.63.",

        "class": "FRDSStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "trend_period": 23, "use_spot_obi": False, "use_regime_filter": True,
            "tp_multiplier": 7.057, "sl_multiplier": 2.1989
        },
    },
    "154": {
        "id": "MICROSTRUCTURE_ENSEMBLE_BTC_1H",
        "desc": "Ensemble of FRDS, LER, and EFR-MR (Requires 2 of 3) on 1H. Sharpe -1.83, ROI -47.4%, MDD 48.6%, 61 trades (BAD). PF=0.34.",

        "class": "MicrostructureEnsembleStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fr_trend_period": 15, "obi_threshold": 0.2727, "depth_perc": 0.8328,
            "zscore_thresh": 2.7932, "tp_multiplier": 4.1907, "sl_multiplier": 2.9545
        },
    },
    "155": {
        "id": "TD_VSB_BTC_1H",
        "desc": "Taker-Driven VWAP Squeeze Breakout. Sharpe -3.49, ROI -91.2%, MDD 92.1%, 376 trades (BAD). PF=0.48.",

        "class": "TDVSBStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vwap_z_thresh": 1.9801, "taker_thresh": 1.6166,
            "tp_multiplier": 5.9518, "sl_multiplier": 1.031
        },
    },
    "156": {
        "id": "ZVE_BTC_1H",
        "desc": "Zero-Lag Volatility Expansion. Sharpe -3.51, ROI -89.7%, MDD 92.0%, 375 trades (BAD). PF=0.53.",

        "class": "ZVEStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "kc_mult": 2.2159, "chop_thresh": 57.0941,
            "tp_multiplier": 3.1322, "sl_multiplier": 1.2735
        },
    },
    "157": {
        "id": "DVAS_SOL_1H",
        "desc": "Dynamic VWAP ATR Scalper (SOL). Sharpe +0.65, ROI +16.1%, MDD 4.7%, 44 trades (MEDIOCRE). PF=1.55.",

        "class": "DVASStrategy",
        "data": {"coins": "SOL", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_dev_thresh": 2.4884, "rsi_extreme": 29.2792,
            "vol_spike_mult": 4.4884, "tp_multiplier": 1.1557, "sl_multiplier": 0.5393
        },
    },
    "158": {
        "id": "DVAS_BNB_1H",
        "desc": "Dynamic VWAP ATR Scalper (BNB). Sharpe +1.06, ROI +28.7%, MDD 6.0%, 30 trades (MEDIOCRE). PF=2.75.",

        "class": "DVASStrategy",
        "data": {"coins": "BNB", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "atr_dev_thresh": 0.9274, "rsi_extreme": 18.7729,
            "vol_spike_mult": 4.2345, "tp_multiplier": 1.6531, "sl_multiplier": 1.9795
        },
    },
    "159": {
        "id": "FORGE_EMA_MACD_BTC_5M",
        "desc": "EMA MACD Cross (BTC, 5m). Sharpe -32.71, ROI -100.0%, MDD 100.0%, 14429 trades (BAD). PF=0.01.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "invert_signals": True,
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "160": {
        "id": "FORGE_EMA_MACD_BTC_15M",
        "desc": "EMA MACD Cross (BTC, 15m). Sharpe -17.75, ROI -100.0%, MDD 100.0%, 4575 trades (BAD). PF=0.05.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "15m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "161": {
        "id": "FORGE_EMA_MACD_BTC_1H",
        "desc": "EMA MACD Cross (BTC, 1h). Sharpe -2.94, ROI -97.9%, MDD 98.6%, 846 trades (BAD). PF=0.62.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 25,
            "ema_slow": 159,
            "macd_fast": 14,
            "macd_slow": 45,
            "macd_signal": 4,
            "tp_atr_mult": 7.1303,
            "sl_atr_mult": 1.7169,
            "atr_period": 27
        },
    },
    "162": {
        "id": "FORGE_EMA_MACD_BTC_4H",
        "desc": "EMA MACD Cross (BTC, 4h). Sharpe +0.19, ROI +6.5%, MDD 34.8%, 121 trades (BAD). PF=1.06.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 30,
            "ema_slow": 200,
            "macd_fast": 30,
            "macd_slow": 88,
            "macd_signal": 17,
            "tp_atr_mult": 3.4754,
            "sl_atr_mult": 1.8967,
            "atr_period": 14
        },
    },
    "163": {
        "id": "FORGE_EMA_MACD_BTC_1D",
        "desc": "EMA MACD Cross (BTC, 1d). Sharpe +0.08, ROI -4.8%, MDD 44.7%, 77 trades (BAD). PF=1.01.",

        "class": "ForgeStrategy",
        "data": {"coins": "BTC", "timeframes": "1d", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 5,
            "ema_slow": 20,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "tp_atr_mult": 2.0,
            "sl_atr_mult": 1.0,
            "atr_period": 14
        },
    },
    "164": {
        "id": "FORGE_EMA_MACD_ETH_5M",
        "desc": "EMA MACD Cross (ETH, 5m). Sharpe -24.09, ROI -100.0%, MDD 100.0%, 14213 trades (BAD). PF=0.01.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "invert_signals": True,
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "165": {
        "id": "FORGE_EMA_MACD_ETH_15M",
        "desc": "EMA MACD Cross (ETH, 15m). Sharpe -11.97, ROI -100.0%, MDD 100.0%, 4582 trades (BAD). PF=0.09.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "15m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "166": {
        "id": "FORGE_EMA_MACD_ETH_1H",
        "desc": "EMA MACD Cross (ETH, 1h). Sharpe -1.11, ROI -74.8%, MDD 77.8%, 626 trades (BAD). PF=0.75.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 21,
            "ema_slow": 155,
            "macd_fast": 29,
            "macd_slow": 96,
            "macd_signal": 16,
            "tp_atr_mult": 5.3066,
            "sl_atr_mult": 1.0176,
            "atr_period": 5
        },
    },
    "167": {
        "id": "FORGE_EMA_MACD_ETH_4H",
        "desc": "EMA MACD Cross (ETH, 4h). Sharpe +1.27, ROI +302.2%, MDD 41.2%, 164 trades (MEDIOCRE). PF=1.37.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 8,
            "ema_slow": 81,
            "macd_fast": 30,
            "macd_slow": 96,
            "macd_signal": 20,
            "tp_atr_mult": 6.9206,
            "sl_atr_mult": 1.1505,
            "atr_period": 26
        },
    },
    "168": {
        "id": "FORGE_EMA_MACD_ETH_1D",
        "desc": "EMA MACD Cross (ETH, 1d). Sharpe +1.17, ROI +299.9%, MDD 26.7%, 33 trades (MEDIOCRE). PF=2.27.",

        "class": "ForgeStrategy",
        "data": {"coins": "ETH", "timeframes": "1d", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 8,
            "ema_slow": 71,
            "macd_fast": 28,
            "macd_slow": 31,
            "macd_signal": 9,
            "tp_atr_mult": 5.0515,
            "sl_atr_mult": 1.2183,
            "atr_period": 9
        },
    },
    "169": {
        "id": "FORGE_EMA_MACD_SOL_5M",
        "desc": "EMA MACD Cross (SOL, 5m). Sharpe -14.13, ROI -100.0%, MDD 100.0%, 14204 trades (BAD). PF=0.28.",

        "class": "ForgeStrategy",
        "data": {"coins": "SOL", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "170": {
        "id": "FORGE_EMA_MACD_SOL_15M",
        "desc": "EMA MACD Cross (SOL, 15m). Sharpe -6.08, ROI -99.9%, MDD 99.9%, 4604 trades (BAD). PF=0.53.",

        "class": "ForgeStrategy",
        "data": {"coins": "SOL", "timeframes": "15m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "171": {
        "id": "FORGE_EMA_MACD_SOL_1H",
        "desc": "EMA MACD Cross (SOL, 1h). Sharpe +0.56, ROI +68.8%, MDD 48.5%, 723 trades (MEDIOCRE). PF=1.06.",

        "class": "ForgeStrategy",
        "data": {"coins": "SOL", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 29,
            "ema_slow": 176,
            "macd_fast": 11,
            "macd_slow": 91,
            "macd_signal": 19,
            "tp_atr_mult": 6.3878,
            "sl_atr_mult": 0.7601,
            "atr_period": 16
        },
    },
    "172": {
        "id": "FORGE_EMA_MACD_SOL_4H",
        "desc": "EMA MACD Cross (SOL, 4h). Sharpe +1.80, ROI +1205.3%, MDD 30.0%, 177 trades (GOOD). PF=1.55.",

        "class": "ForgeStrategy",
        "data": {"coins": "SOL", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 21,
            "ema_slow": 35,
            "macd_fast": 29,
            "macd_slow": 87,
            "macd_signal": 18,
            "tp_atr_mult": 4.8936,
            "sl_atr_mult": 1.1034,
            "atr_period": 15
        },
    },
    "173": {
        "id": "FORGE_EMA_MACD_SOL_1D",
        "desc": "EMA MACD Cross (SOL, 1d). Sharpe +0.62, ROI +82.9%, MDD 39.5%, 72 trades (MEDIOCRE). PF=1.23.",

        "class": "ForgeStrategy",
        "data": {"coins": "SOL", "timeframes": "1d", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 5,
            "ema_slow": 20,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "tp_atr_mult": 2.0,
            "sl_atr_mult": 1.0,
            "atr_period": 14
        },
    },
    "174": {
        "id": "FORGE_EMA_MACD_XRP_5M",
        "desc": "EMA MACD Cross (XRP, 5m). Sharpe -15.64, ROI -100.0%, MDD 100.0%, 14582 trades (BAD). PF=0.40.",

        "class": "ForgeStrategy",
        "data": {"coins": "XRP", "timeframes": "5m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "175": {
        "id": "FORGE_EMA_MACD_XRP_15M",
        "desc": "EMA MACD Cross (XRP, 15m). Sharpe -5.70, ROI -99.8%, MDD 99.8%, 4797 trades (BAD). PF=0.51.",

        "class": "ForgeStrategy",
        "data": {"coins": "XRP", "timeframes": "15m", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 14,
            "ema_slow": 192,
            "macd_fast": 23,
            "macd_slow": 66,
            "macd_signal": 5,
            "tp_atr_mult": 2.092,
            "sl_atr_mult": 0.6452,
            "atr_period": 27
        },
    },
    "176": {
        "id": "FORGE_EMA_MACD_XRP_1H",
        "desc": "EMA MACD Cross (XRP, 1h). Sharpe +0.77, ROI +151.9%, MDD 58.8%, 616 trades (MEDIOCRE). PF=1.11.",

        "class": "ForgeStrategy",
        "data": {"coins": "XRP", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 10,
            "ema_slow": 138,
            "macd_fast": 21,
            "macd_slow": 95,
            "macd_signal": 17,
            "tp_atr_mult": 4.6212,
            "sl_atr_mult": 2.0363,
            "atr_period": 8
        },
    },
    "177": {
        "id": "FORGE_EMA_MACD_XRP_4H",
        "desc": "EMA MACD Cross (XRP, 4h). Sharpe +1.28, ROI +467.8%, MDD 36.9%, 288 trades (MEDIOCRE). PF=1.54.",

        "class": "ForgeStrategy",
        "data": {"coins": "XRP", "timeframes": "4h", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 7,
            "ema_slow": 148,
            "macd_fast": 29,
            "macd_slow": 100,
            "macd_signal": 3,
            "tp_atr_mult": 4.3814,
            "sl_atr_mult": 0.5276,
            "atr_period": 8
        },
    },
    "178": {
        "id": "FORGE_EMA_MACD_XRP_1D",
        "desc": "EMA MACD Cross (XRP, 1d). Sharpe +1.05, ROI +280.1%, MDD 41.5%, 37 trades (MEDIOCRE). PF=2.45.",

        "class": "ForgeStrategy",
        "data": {"coins": "XRP", "timeframes": "1d", "date_from": "2023-01-01", "date_to": "2026-06-01"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 13,
            "ema_slow": 37,
            "macd_fast": 18,
            "macd_slow": 53,
            "macd_signal": 20,
            "tp_atr_mult": 7.8803,
            "sl_atr_mult": 0.5446,
            "atr_period": 7
        },
    },
    "179": {
        "id":   "EMASTREAK_BTC_4H",
        "desc": "EMA Streak 1H - Abacussa streaming EMA crossover with safety features. Sharpe -0.06, ROI -14.9%, MDD 38.3%, 42 trades (BAD). PF=0.89.",

        "class": "EMAStreakStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast": 15, "slow": 83, "streakWin": 60, "momentumPct": 0.14, "useStreak": True,
            "stopLossPct": 0.02, "leverage_param": 20, "riskPerTrade": 0.06, "useTP": False,
            "takeProfitPct": 0.0, "safetyPinPct": 0.08, "safetyPinLockPct": 0.04
        },
    },

    "182": {
        "id":   "SUPERTREND_EMA_FILTER_BTC_4H",
        "desc": "Supertrend Pro — Supertrend flip+EMA-177 filter, st_mult=4.87. Sharpe +0.84, ROI +112.7%, MDD 28.9%, 78 trades (MEDIOCRE). PF=1.42.",

        "class": "SupertrendEmaFilterStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":      16,
            "st_multiplier":  4.8708,
            "ema_period":     177,
            "atr_period":     13,
            "sl_atr_mult":    1.8594,
            "tp_rr":          1.8277,
            "use_ema_filter": True,
        },
    },

    "183": {
        "id":   "SUPERTREND_PRO_VOL_BTC_4H",
        "desc": "Supertrend Pro Volatility Breakout — ST flip + RV>1.57 + RSI zone. Sharpe +0.42, ROI +61.3%, MDD 61.2%, 123 trades (MEDIOCRE). PF=1.15.",

        "class": "SupertrendProVolatilityStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "st_period":      15,
            "st_multiplier":  3.0438,
            "rv_period":      37,
            "rv_threshold":   1.5717,
            "rsi_period":     14,
            "atr_period":     13,
            "atr_trail_mult": 4.6781,
        },
    },

    "184": {
        "id":   "DIAMOND_TRIANGLE_BTC_4H",
        "desc": "Diamond Triangle Breakout — BB squeeze + vol spike + ADX trail. Sharpe +0.28, ROI +21.0%, MDD 62.8%, 216 trades (BAD). PF=1.07.",

        "class": "DiamondTriangleBreakoutStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":      12,
            "bb_std":         2.7295,
            "squeeze_pct":    0.0913,
            "squeeze_bars":   3,
            "vol_period":     18,
            "vol_spike_mult": 1.4394,
            "adx_period":     8,
            "adx_threshold":  24.81,
            "atr_period":     7,
            "sl_atr_mult":    2.6704,
            "atr_trail_mult": 4.7993,
        },
    },

    "185": {
        "id":   "RSI_DIVERGENCE_MR_BTC_4H",
        "desc": "RSI Divergence Mean Reversion — RSI div + ADX filter, BB midline TP (BTC 4H). Sharpe -1.15, ROI -20.6%, MDD 23.7%, 34 trades (BAD). PF=0.22.",

        "class": "RsiDivergenceMeanReversionStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "rsi_period":    13,
            "div_lookback":  47,
            "adx_period":    9,
            "adx_threshold": 32.0026,
            "bb_period":     11,
            "bb_std":        1.6958,
            "atr_period":    10,
            "sl_atr_mult":   2.6718,
        },
    },

    "186": {
        "id":   "FISHER_EXTREME_REVERSAL_BTC_1H",
        "desc": "Fisher Extreme Reversal — Fisher spike>1.84 + signal cross, TP at zero-cross (BTC 1H). Sharpe -1.43, ROI -30.1%, MDD 32.6%, 34 trades (BAD). PF=0.21.",

        "class": "FisherExtremeReversalStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fisher_period":  13,
            "signal_period":  12,
            "extreme_thresh": 1.8414,
            "atr_period":     14,
            "sl_atr_mult":    0.5034,
        },
    },

    "187": {
        "id":   "TIGHT_BB_SCALPER_BTC_1H",
        "desc": "Tight BB Scalper — 1.95std close-back-inside + flat EMA-247 filter (BTC 1H). Sharpe -6.21, ROI -100.0%, MDD 100.0%, 3123 trades (BAD). PF=0.38.",

        "class": "TightBollingerScalperStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bb_period":        17,
            "bb_std":           1.9507,
            "ema_period":       247,
            "ema_slope_thresh": 0.0064,
            "atr_period":       9,
            "sl_atr_mult":      1.312,
        },
    },

    "188": {
        "id":   "HMM_REGIME_CLASSIFIER_BTC_4H",
        "desc": "HMM Regime Classifier — 3-state Gaussian HMM on log_return+norm_ATR, EMA-89 trend gate (BTC 4H). Sharpe -0.19, ROI -54.0%, MDD 66.5%, 219 trades (BAD). PF=0.87.",

        "class": "HMMRegimeClassifierStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "n_states":       3,
            "ema_period":     89,
            "atr_period":     7,
            "sl_atr_mult":    1.5617,
            "atr_trail_mult": 3.8031,
        },
    },

    "189": {
        "id":   "PRICE_MOMENTUM_ACCEL_ETH_1H",
        "desc": "Price Momentum Acceleration — Alpha#46 2nd-order price diff z-score ±2.79σ (ETH 1H). Sharpe +0.39, ROI +51.1%, MDD 49.6%, 215 trades (MEDIOCRE). PF=1.11.",

        "class": "PriceMomentumAccelerationStrategy",
        "data": {"coins": "ETH", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast_period":     5,
            "slow_period":     39,
            "zscore_period":   150,
            "entry_threshold": 2.7866,
            "atr_period":      8,
            "sl_atr_mult":     2.506,
            "atr_trail_mult":  5.0669,
        },
    },

    "190": {
        "id":   "BAR_STRENGTH_MOMENTUM_BTC_4H",
        "desc": "Bar Strength Momentum — Alpha#53 bar-strength delta + ADX(32) gate (BTC 4H). Sharpe -0.46, ROI -70.2%, MDD 82.9%, 343 trades (BAD). PF=0.95.",

        "class": "BarStrengthMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "bs_period":       11,
            "entry_threshold": 0.2657,
            "adx_period":      13,
            "adx_threshold":   32.3649,
            "atr_period":      7,
            "sl_atr_mult":     2.2915,
            "atr_trail_mult":  4.9986,
        },
    },

    "191": {
        "id":   "VOL_CAPITULATION_REVERSAL_ETH_4H",
        "desc": "Volume Capitulation Reversal — Alpha#43 vol_rank×decline_rank product (ETH 4H). Sharpe -1.16, ROI -93.7%, MDD 95.6%, 950 trades (BAD). PF=0.92.",

        "class": "VolumeCapitulationReversalStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "adv_period":       21,
            "rank_v_period":    39,
            "momentum_period":  12,
            "rank_m_period":    14,
            "signal_threshold": 0.2124,
            "atr_period":       9,
            "sl_atr_mult":      1.1162,
            "atr_trail_mult":   4.5985,
        },
    },

    "192": {
        "id":   "INTRABAR_EFF_MOMENTUM_BTC_1H",
        "desc": "Intrabar Efficiency Momentum — Alpha#101 (close-open)/(high-low) EMA-179 smoothed gate (BTC 1H). Sharpe -0.74, ROI -42.5%, MDD 45.0%, 65 trades (BAD). PF=0.50.",

        "class": "IntrabarEfficiencyMomentumStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "smooth_period":   13,
            "entry_threshold": 0.3529,
            "ema_period":      179,
            "atr_period":      9,
            "sl_atr_mult":     1.9388,
            "atr_trail_mult":  3.5561,
        },
    },

    "193": {
        "id":   "HURST_REGIME_ADAPTIVE_ETH_4H",
        "desc": "Hurst Regime Adaptive — VR-167 regime switch: momentum (VR>1.38) vs MR (VR<0.62) on ETH 4H. Sharpe +0.75, ROI +147.0%, MDD 39.9%, 68 trades (MEDIOCRE). PF=1.61.",

        "class": "HurstRegimeAdaptiveStrategy",
        "data": {"coins": "ETH", "timeframes": "4h", "date_from": "2021-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "vr_window":         167,
            "vr_k":              11,
            "vr_band":           0.3781,
            "mom_period":        26,
            "rev_zscore_period": 19,
            "rev_threshold":     2.5796,
            "atr_period":        7,
            "sl_atr_mult":       1.3872,
            "atr_trail_mult":    4.0786,
        },
    },
    "194": {
        "id":   "AMIHUD_ILLIQ_MR_BTC_1H",
        "desc": "Amihud Illiquidity Mean-Reversion Strategy (1H). Sharpe -8.73, ROI -98.5%, MDD 98.5%, 656 trades (BAD). PF=0.23.",

        "class": "AmihudIlliqMrStrategy194",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "illiq_period": 25, "zscore_period": 288, "atr_period": 24, "tp_mult": 3.9933, "sl_mult": 0.89
        },
    },
    "195": {
        "id":   "OU_MR_SPEED_BTC_1H",
        "desc": "Ornstein-Uhlenbeck Mean-Reversion Speed Strategy (1H). Sharpe -2.13, ROI -44.5%, MDD 48.0%, 31 trades (BAD). PF=0.20.",

        "class": "OuMrSpeedStrategy195",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "period": 49, "atr_period": 11, "tp_mult": 5.8046, "sl_mult": 2.8753, "kappa_thresh": 219.3001
        },
    },
    "196": {
        "id":   "MULTI_REL_MOM_4H",
        "desc": "Cross-Sectional Relative Momentum Rank (Multi-Coin). Sharpe +0.37, ROI -56.2%, MDD 91.8%, 634 trades (BAD). PF=1.10.",

        "class": "RelativeMomentumRank",
        "data": {"coins": ["BTC", "ETH", "BNB", "SOL", "XRP"], "timeframes": "4h", "date_from": "2023-05-31", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "roc_period": 28,
            "sl_pct": 0.05,
            "tp_pct": 0.10
        },
    },
}



# --- Current Active Strategy (for optimizer) ---
ACTIVE_STRATEGY = "141" # Strategy 141 rejected by WFO (Sharpe Ratios: +0.210, -1.660, +0.120, -1.310)

STRATEGY_SETTINGS = {
    "name": "AVSStrategy", # Strategy 141 rejected by WFO
    "params": {
        "bb_period": 25, "bb_std": 3.37678576602479, "kc_period": 20, "kc_mult": 1.5,
        "adx_period": 24, "adx_threshold": 28.979877262955547, "fisher_period": 9,
        "use_vrsi_filter": True, "vrsi_period": 27, "vrsi_threshold": 72.02230023486418,
        "chandelier_atr_period": 22, "chandelier_mult": 3.416145155592091,
        "use_regime_filter": True, "use_squeeze_filter": True
    }, # Strategy 141 rejected by WFO
}


RISK_SETTINGS = {
    "initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
    "trading_fee": 0.0005, "maintenance_margin_rate": 0.005
} # Strategy 141 rejected by WFO
