---
name: Kalman Filtered Momentum (KFM)
category: Momentum
coins: [BTC, ETH, BNB, SOL, XRP]
timeframes: [4h]
status: IMPLEMENTED
---

## Alpha Premise
Traditional moving averages (EMA/SMA) suffer from fixed lag. A Kalman Filter estimates the true underlying price state by continuously updating based on the variance of the asset. By calculating the first derivative (slope) of the Kalman state, we isolate structural medium-frequency momentum without getting whipsawed by short-term noise.

## Strategy Play Style
Medium Frequency Trend-Following (MFT). It thrives in protracted directional markets where standard moving averages would get whipsawed by intermediate volatility.

## Strategic Disadvantages
High-frequency ranging environments. Even with adaptive noise matrices, the Kalman filter can lag slightly during sudden V-shaped recoveries or flash crashes.

## Enhancement Recommendations
1. The Developer must implement a `calc_kalman_filter` factor in `library.py`.
2. Pair the Kalman slope with an ATR-based Chandelier Exit for dynamic take-profit.

## Agent Reasoning (Chain of Thought)
Standard EMA momentum strategies lack dynamic adaptability to volatility. Quantitative research highlights Kalman Filters for algorithmic trading because they model price as a hidden state, dynamically scaling the measurement noise covariance (R). By taking the first derivative (slope) of this state on a 4H timeframe, we capture clean, multi-day MFT trends (executing roughly every 2-3 days).
