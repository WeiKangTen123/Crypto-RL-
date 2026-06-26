import pandas as pd
import numpy as np
import os


def _load_window(coin, timeframe, start_date, end_date):
    data_path = os.path.join("dataset", coin, timeframe, "spot_ohlcv.parquet")
    if not os.path.exists(data_path):
        return None

    df = pd.read_parquet(data_path)

    for col in ('open_time', 'timestamp'):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            df = df.set_index(col).sort_index()
            break

    # Normalise column names to Title-case
    df.columns = [c.title() if c.lower() in ('close', 'high', 'low', 'open', 'volume') else c
                  for c in df.columns]

    return df.loc[start_date:end_date]


def classify_regime(start_date, end_date, coin="BTC", timeframe="4h"):
    """
    Returns (regime, score) for the given window.
    regime: BULL_TREND | BEAR_TREND | HIGH_VOL_CHOP | LOW_VOL_RANGE
    """
    window_df = _load_window(coin, timeframe, start_date, end_date)

    if window_df is None:
        return "DATA_MISSING", 0.0
    if len(window_df) < 10:
        return "INSUFFICIENT_DATA", 0.0

    close = window_df['Close']
    candles_per_day = {"1h": 24, "4h": 6, "15m": 96, "1d": 1}.get(timeframe, 6)

    total_return = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
    log_returns  = np.log(close / close.shift(1)).dropna()
    volatility   = log_returns.std() * np.sqrt(candles_per_day * 365.25)
    ema          = close.ewm(span=50).mean()
    above_ema    = (close > ema).mean()

    if total_return > 0.05 and above_ema > 0.6:
        return "BULL_TREND",    round(float(total_return), 4)
    elif total_return < -0.05 and above_ema < 0.4:
        return "BEAR_TREND",    round(float(abs(total_return)), 4)
    elif volatility > 0.6:
        return "HIGH_VOL_CHOP", round(float(volatility), 4)
    else:
        return "LOW_VOL_RANGE", round(float(1 - volatility), 4)


def extract_market_features(start_date, end_date, coin="BTC", timeframe="4h"):
    """
    Returns a dict of key market descriptors for the window.
    Used by the pattern-matching agent to find similar historical periods.
    """
    window_df = _load_window(coin, timeframe, start_date, end_date)

    if window_df is None or len(window_df) < 14:
        return {}

    close  = window_df['Close']
    high   = window_df['High']
    low    = window_df['Low']
    candles_per_day = {"1h": 24, "4h": 6, "15m": 96, "1d": 1}.get(timeframe, 6)

    # ATR (14-period, normalised by price)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr_raw  = tr.rolling(14).mean().iloc[-1]
    atr_pct  = round(float(atr_raw / close.iloc[-1] * 100), 4)

    # RSI (14-period) at end of window
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-10)
    rsi   = round(float((100 - 100 / (1 + rs)).iloc[-1]), 2)

    # Annualised volatility
    log_ret    = np.log(close / close.shift(1)).dropna()
    annual_vol = round(float(log_ret.std() * np.sqrt(candles_per_day * 365.25) * 100), 2)

    # Total price return over the window
    price_return = round(float((close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100), 2)

    # Taker buy ratio (if column available)
    taker_ratio = None
    taker_col   = next((c for c in window_df.columns if 'taker' in c.lower() and 'base' in c.lower()), None)
    vol_col     = 'Volume'
    if taker_col and vol_col in window_df.columns:
        try:
            tc = pd.to_numeric(window_df[taker_col], errors='coerce')
            vc = pd.to_numeric(window_df[vol_col],   errors='coerce')
            ratio       = tc / (vc + 1e-10)
            taker_ratio = round(float(ratio.mean()), 4)
        except Exception:
            taker_ratio = None

    features = {
        "atr_pct":      atr_pct,
        "rsi_end":      rsi,
        "annual_vol":   annual_vol,
        "price_return": price_return,
    }
    if taker_ratio is not None:
        features["taker_ratio"] = taker_ratio

    return features


if __name__ == "__main__":
    r, s = classify_regime("2024-01-01", "2024-01-31", coin="BTC", timeframe="4h")
    f = extract_market_features("2024-01-01", "2024-01-31", coin="BTC", timeframe="4h")
    print(f"Regime: {r}, Score: {s}")
    print(f"Features: {f}")
