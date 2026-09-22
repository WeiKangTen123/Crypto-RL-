import pandas as pd
import numpy as np
import talib
from typing import Tuple, List, Dict, Union, Optional

"""
library.py — Centralized repository for proven mathematical factors.
This file contains isolated functions that return numerical series or signals.
All strategy files MUST import from here — never re-implement these inline.
"""

# ── 1. VOLATILITY & SQUEEZE FACTORS ──────────────────────────────────────────

def calc_bb_kc_squeeze(df, bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5):
    """
    Identifies 'Squeeze' periods where Bollinger Bands are inside Keltner Channels.
    Returns: Boolean Series (True = Squeeze)
    """
    # Bollinger Bands
    upper_bb, mid_bb, lower_bb = talib.BBANDS(df['Close'], timeperiod=bb_period, nbdevup=bb_std, nbdevdn=bb_std)
    
    # Keltner Channels
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=kc_period)
    mid_kc = talib.EMA(df['Close'], timeperiod=kc_period)
    upper_kc = mid_kc + (atr * kc_mult)
    lower_kc = mid_kc - (atr * kc_mult)
    
    squeeze = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    return squeeze



def calc_adx(df, period=14):
    """
    Calculates ADX (Average Directional Index).
    Returns: adx Series.
    """
    return talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=period)

def calc_bb_kc_squeeze_filtered(df, bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5, adx_period=14, adx_threshold=25):
    """
    Identifies 'Squeeze' periods where Bollinger Bands are inside Keltner Channels,
    but only when ADX indicates trending conditions are NOT present.
    Returns: Boolean Series (True = Squeeze, False = No Squeeze or Trending).
    """
    squeeze = calc_bb_kc_squeeze(df, bb_period, bb_std, kc_period, kc_mult)
    adx     = calc_adx(df, adx_period)
    
    # Squeeze is active if BB are inside KC AND ADX is below threshold (i.e., not trending)
    return squeeze & (adx < adx_threshold)

def calc_chandelier_exit(df, atr_period=22, multiplier=3.0, long_only=True):
    """
    Calculates Chandelier Exit (trailing stop-loss).
    Returns: long_exit, short_exit Series.
    """
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=atr_period)

    long_cand  = (df['High'].rolling(window=atr_period).max() - atr * multiplier).to_numpy()
    short_cand = (df['Low'].rolling(window=atr_period).min()  + atr * multiplier).to_numpy()
    close      = df['Close'].to_numpy()
    n          = len(df)

    long_arr  = np.full(n, np.nan)
    short_arr = np.full(n, np.nan)

    for i in range(1, n):
        prev_le = long_arr[i - 1]
        if np.isnan(prev_le) or close[i - 1] > prev_le:
            long_arr[i] = max(long_cand[i], prev_le if not np.isnan(prev_le) else -np.inf)
        else:
            long_arr[i] = long_cand[i]

        if not long_only:
            prev_se = short_arr[i - 1]
            if np.isnan(prev_se) or close[i - 1] < prev_se:
                short_arr[i] = min(short_cand[i], prev_se if not np.isnan(prev_se) else np.inf)
            else:
                short_arr[i] = short_cand[i]

    return pd.Series(long_arr, index=df.index), pd.Series(short_arr, index=df.index)

# ── 2. ORDER FLOW & INTENSITY FACTORS ────────────────────────────────────────

def calc_taker_intensity(df, period=24, std_mult=2.0):
    """
    Measures aggressive market participation using num_trades and taker volume.
    Returns: Normalized score (z-score style)
    """
    num_trades = df['num_trades']
    ma = num_trades.rolling(window=period).mean()
    std = num_trades.rolling(window=period).std()
    
    intensity = (num_trades - ma) / (std + 1e-10)
    
    # Volume component (Taker Ratio)
    taker_ratio = df['taker_buy_base_vol'] / (df['Volume'] + 1e-10)
    
    return intensity, taker_ratio


# ── 3. ICHIMOKU CLOUD FACTORS ───────────────────────────────────────────────

def calc_ichimoku(df, tenkan=9, kijun=26, senkou_b=52, displacement=26):
    """
    Calculates Ichimoku Cloud components.
    """
    res = {}
    res['tenkan'] = (df['High'].rolling(window=tenkan).max() + df['Low'].rolling(window=tenkan).min()) / 2
    res['kijun'] = (df['High'].rolling(window=kijun).max() + df['Low'].rolling(window=kijun).min()) / 2
    
    res['senkou_a'] = ((res['tenkan'] + res['kijun']) / 2).shift(displacement)
    res['senkou_b'] = ((df['High'].rolling(window=senkou_b).max() + df['Low'].rolling(window=senkou_b).min()) / 2).shift(displacement)
    
    res['cloud_top'] = np.maximum(res['senkou_a'], res['senkou_b'])
    res['cloud_bottom'] = np.minimum(res['senkou_a'], res['senkou_b'])
    
    return pd.DataFrame(res, index=df.index)


# ── 4. MOMENTUM & DIVERGENCE FACTORS ────────────────────────────────────────

def detect_divergence(price_series, indicator_series, lookback=60):
    """
    Identifies Regular Bullish/Bearish divergences between price and an oscillator.
    Bullish: price makes lower low, indicator makes higher low.
    Bearish: price makes higher high, indicator makes lower high.
    Returns: Signal series (1 for Bullish, -1 for Bearish, 0 for None).

    Signals are placed at bar i+window (confirmation time) so no future data
    is required at signal generation — fully causal.
    """
    signals = pd.Series(0, index=price_series.index)
    window  = lookback // 2

    price     = price_series.values
    indicator = indicator_series.values
    n         = len(price)

    last_low_p,  last_low_r  = np.nan, np.nan
    last_high_p, last_high_r = np.nan, np.nan

    for i in range(window, n - window):
        confirm = i + window   # bar at which this pivot is confirmable from past data only

        # Pivot low: bar i is minimum in symmetric [i-window, i+window] window.
        # At bar `confirm` all bars in that window are in the past — causal.
        if price[i] == np.min(price[max(0, i - window): i + window + 1]):
            if not np.isnan(last_low_p):
                if price[i] < last_low_p and indicator[i] > last_low_r:
                    signals.iloc[confirm] = 1
            last_low_p, last_low_r = price[i], indicator[i]

        # Pivot high
        if price[i] == np.max(price[max(0, i - window): i + window + 1]):
            if not np.isnan(last_high_p):
                if price[i] > last_high_p and indicator[i] < last_high_r:
                    signals.iloc[confirm] = -1
            last_high_p, last_high_r = price[i], indicator[i]

    return signals


# ── 5. MEAN REVERSION FACTORS ───────────────────────────────────────────────

def calc_vwap_zscore(df, period=20):
    """
    Calculates distance from Rolling VWAP normalized by standard deviation.
    """
    typical = (df['High'] + df['Low'] + df['Close']) / 3.0
    rolling_tp_vol = (typical * df['Volume']).rolling(window=period).sum()
    rolling_vol    = df['Volume'].rolling(window=period).sum()
    vwap           = rolling_tp_vol / (rolling_vol + 1e-10)
    
    std = (typical - vwap).rolling(window=period).std()
    zscore = (df['Close'] - vwap) / (std + 1e-10)
    
    return zscore, vwap


# ── 6. TREND FILTERS & VOLATILITY BREAKOUTS ──────────────────────────────────

def calc_choppiness_index(df, period=14):
    """
    Calculates the Choppiness Index (CHOP).
    Values > 61.8 indicate consolidation, < 38.2 indicate strong trend.
    """
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=1)
    atr_sum = atr.rolling(window=period).sum()
    max_high = df['High'].rolling(window=period).max()
    min_low = df['Low'].rolling(window=period).min()
    
    # Add epsilon to prevent division by zero or log of zero
    chop = 100 * np.log10(atr_sum / (max_high - min_low + 1e-10) + 1e-10) / np.log10(period)
    return chop

def calc_keltner_channels(df, period=20, mult=2.0):
    """
    Calculates Keltner Channels.
    """
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=period)
    mid_kc = talib.EMA(df['Close'], timeperiod=period)
    upper_kc = mid_kc + (atr * mult)
    lower_kc = mid_kc - (atr * mult)
    
    return upper_kc, mid_kc, lower_kc

def calc_supertrend(df, period=10, multiplier=3.0):
    """
    Calculates Supertrend indicator.
    Returns (supertrend_line, direction) where direction: 1=up (bullish), -1=down (bearish).

    Uses prev_direction to track state rather than comparing supertrend value to band value
    (the old approach was broken by a 0.0 initialization that made the first bar always
    match the upper band, producing a false initial flip).
    """
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=period)
    hl2 = (df['High'] + df['Low']) / 2

    basic_upperband = hl2 + (multiplier * atr)
    basic_lowerband = hl2 - (multiplier * atr)

    final_upperband = basic_upperband.copy()
    final_lowerband = basic_lowerband.copy()
    supertrend           = pd.Series(float('nan'), index=df.index)
    supertrend_direction = pd.Series(1, index=df.index)  # default bullish

    # Find first bar where ATR is valid
    start = int(atr.first_valid_index() is not None and df.index.get_loc(atr.first_valid_index()))
    if not isinstance(start, int):
        start = period

    # Seed direction at first valid bar based on where close sits relative to bands
    if df['Close'].iloc[start] > basic_upperband.iloc[start]:
        supertrend_direction.iloc[start] = 1
        supertrend.iloc[start]           = final_lowerband.iloc[start]
    else:
        supertrend_direction.iloc[start] = -1
        supertrend.iloc[start]           = final_upperband.iloc[start]

    for i in range(start + 1, len(df)):
        # Sticky upper band — only tighten downward or reset when price breaks above it
        if basic_upperband.iloc[i] < final_upperband.iloc[i - 1] or df['Close'].iloc[i - 1] > final_upperband.iloc[i - 1]:
            final_upperband.iloc[i] = basic_upperband.iloc[i]
        else:
            final_upperband.iloc[i] = final_upperband.iloc[i - 1]

        # Sticky lower band — only tighten upward or reset when price breaks below it
        if basic_lowerband.iloc[i] > final_lowerband.iloc[i - 1] or df['Close'].iloc[i - 1] < final_lowerband.iloc[i - 1]:
            final_lowerband.iloc[i] = basic_lowerband.iloc[i]
        else:
            final_lowerband.iloc[i] = final_lowerband.iloc[i - 1]

        prev_dir = int(supertrend_direction.iloc[i - 1])

        if prev_dir == -1:
            # Bearish: flip to bullish if close breaks above upper band
            if df['Close'].iloc[i] > final_upperband.iloc[i]:
                supertrend_direction.iloc[i] = 1
                supertrend.iloc[i]           = final_lowerband.iloc[i]
            else:
                supertrend_direction.iloc[i] = -1
                supertrend.iloc[i]           = final_upperband.iloc[i]
        else:
            # Bullish: flip to bearish if close breaks below lower band
            if df['Close'].iloc[i] < final_lowerband.iloc[i]:
                supertrend_direction.iloc[i] = -1
                supertrend.iloc[i]           = final_upperband.iloc[i]
            else:
                supertrend_direction.iloc[i] = 1
                supertrend.iloc[i]           = final_lowerband.iloc[i]

    return supertrend, supertrend_direction


# ── 7. ICT / SMART MONEY FACTORS ─────────────────────────────────────────────

def detect_fvg(df):
    """
    Detects Fair Value Gaps (FVG).
    Bullish: Low[i] > High[i-2]
    Bearish: High[i] < Low[i-2]
    """
    bullish_fvg = (df['Low'] > df['High'].shift(2))
    bearish_fvg = (df['High'] < df['Low'].shift(2))
    return bullish_fvg, bearish_fvg

def detect_swing_high_low(df, lookback=20):
    """
    Detects swing highs and lows without look-ahead.
    is_swing_high[i] / is_swing_low[i] is True when the bar lookback periods ago
    is confirmed as a swing pivot at bar i (i.e. it was the extreme in the full
    2*lookback+1 window that ends at bar i).
    Callers should extract pivot VALUES as df['High'].shift(lookback).where(is_swing_high)
    so the value recorded is the pivot bar's price, not the confirmation bar's price.
    """
    rolling_max   = df['High'].rolling(window=2 * lookback + 1).max()
    rolling_min   = df['Low'].rolling(window=2 * lookback + 1).min()
    is_swing_high = df['High'].shift(lookback) == rolling_max
    is_swing_low  = df['Low'].shift(lookback)  == rolling_min
    return is_swing_high, is_swing_low


# ── 8. CORE TECHNICAL INDICATORS ───────────────────────────────────────────

def calc_ema(df, period=20):
    """EMA of Close."""
    return talib.EMA(df['Close'], timeperiod=period)

def calc_sma(series, period=20):
    """SMA of a given series."""
    if isinstance(series, pd.DataFrame):
        series = series['Close']
    return talib.SMA(series, timeperiod=period)

def calc_rsi(series, period=14):
    """RSI of a given series."""
    return talib.RSI(series, timeperiod=period)

def calc_cci(df, period=14):
    """Commodity Channel Index (CCI)."""
    return talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=period)

def calc_atr(df, period=14):
    """Average True Range."""
    return talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=period)

def calc_bollinger_bands(df, period=20, std=2.0):
    """
    Bollinger Bands.
    Returns: upper, mid, lower Series.
    """
    upper, mid, lower = talib.BBANDS(df['Close'], timeperiod=period, nbdevup=std, nbdevdn=std)
    return upper, mid, lower

def calc_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    """MACD line, signal, histogram."""
    macd, macdsignal, macdhist = talib.MACD(
        df['Close'], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod
    )
    return macd, macdsignal, macdhist

def calc_adx_dmi(df, period=14):
    """
    ADX + Directional Movement Index.
    Returns: adx, di_plus, di_minus Series.
    """
    adx      = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=period)
    di_plus  = talib.PLUS_DI(df['High'], df['Low'], df['Close'], timeperiod=period)
    di_minus = talib.MINUS_DI(df['High'], df['Low'], df['Close'], timeperiod=period)
    return adx, di_plus, di_minus

def calc_ema_ribbon(df, periods=(9, 21, 55, 200)):
    """
    Multi-period EMA ribbon.
    Returns: dict of {period: Series}.
    """
    return {p: talib.EMA(df['Close'], timeperiod=p) for p in periods}

def calc_aroon(df, period=14):
    """
    Aroon Up / Down.
    Returns: aroon_up, aroon_down Series (both 0–100).
    """
    aroon_down, aroon_up = talib.AROON(df['High'], df['Low'], timeperiod=period)
    return aroon_up, aroon_down


# ── 9. SMART MONEY CONCEPTS (SMC) ───────────────────────────────────────────

def detect_order_blocks(df, atr_period=14, atr_multiplier=2.0, ob_lookback=3):
    """
    Identifies institutional Order Blocks (OB) based on impulse moves and tracks their mitigation.
    Returns: signals (1 for Bullish OB touch, -1 for Bearish OB touch)
    """
    signals = pd.Series(0, index=df.index)
    unmitigated_obs = {'bullish': [], 'bearish': []} # Stores {'high': ..., 'low': ..., 'idx': ...}

    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=atr_period)

    for i in range(len(df)):
        current_candle = df.iloc[i]

        # Initialize prev_candle outside the loop to handle i=0 case gracefully
        prev_candle = df.iloc[i-1] if i > 0 else None

        # 1. Detect Strong Move (Impulse)
        if i >= ob_lookback:
            # Check for strong bullish move: current close significantly higher than 'ob_lookback' bars ago
            if current_candle['Close'] - df['Close'].iloc[i-ob_lookback] > atr_multiplier * atr.iloc[i]:
                # Strong Bullish Move detected, look for Bullish OB
                # Bullish OB: last Bearish candle before the strong up move
                if prev_candle is not None and prev_candle['Close'] < prev_candle['Open']:
                    unmitigated_obs['bullish'].append({
                        'high': prev_candle['High'],
                        'low': prev_candle['Low'],
                        'idx': i-1
                    })
            # Check for strong bearish move: current close significantly lower than 'ob_lookback' bars ago
            elif df['Close'].iloc[i-ob_lookback] - current_candle['Close'] > atr_multiplier * atr.iloc[i]:
                # Strong Bearish Move detected, look for Bearish OB
                # Bearish OB: last Bullish candle before the strong down move
                if prev_candle is not None and prev_candle['Close'] > prev_candle['Open']:
                    unmitigated_obs['bearish'].append({
                        'high': prev_candle['High'],
                        'low': prev_candle['Low'],
                        'idx': i-1
                    })

        # 2. Check for Mitigation and Generate Signals
        # Check Bullish OBs
        # Iterate over a copy to allow modification during iteration
        for ob in list(unmitigated_obs['bullish']):
            # Mitigation for Bullish OB: Price falls back and touches the OB zone (specifically the High of the OB candle)
            # Ensure the current candle is not the OB candle itself, and price is within or below the OB high
            if i > ob['idx'] and current_candle['Low'] <= ob['high'] and signals.iloc[i] == 0: 
                signals.iloc[i] = 1 # Long signal
                unmitigated_obs['bullish'].remove(ob) # Mark as mitigated

        # Check Bearish OBs
        # Iterate over a copy to allow modification during iteration
        for ob in list(unmitigated_obs['bearish']):
            # Mitigation for Bearish OB: Price rises back and touches the OB zone (specifically the Low of the OB candle)
            # Ensure the current candle is not the OB candle itself, and price is within or above the OB low
            if i > ob['idx'] and current_candle['High'] >= ob['low'] and signals.iloc[i] == 0:
                signals.iloc[i] = -1 # Short signal
                unmitigated_obs['bearish'].remove(ob) # Mark as mitigated
                
    return signals


# ── 10. ARBITRAGE & SPREADS ───────────────────────────────────────────────

def calc_basis_z_score(spot_df, perp_df, period=20):
    """
    Calculates the Z-Score of the Spot-Perp Basis.
    Assumes spot_df and perp_df are aligned on the same index.
    """
    basis = perp_df['Close'] - spot_df['Close']
    rolling_mean = basis.rolling(window=period).mean()
    rolling_std = basis.rolling(window=period).std()
    
    basis_z = (basis - rolling_mean) / (rolling_std + 1e-10)
    return basis_z


# ── 11. MOMENTUM OSCILLATORS ─────────────────────────────────────────────────

def calc_stoch_kdj(df, period=9):
    """
    KDJ Oscillator (Stochastic-based).
    K = smoothed %K, D = smoothed K, J = 3K - 2D.
    Returns: K, D, J Series (all 0–100 scale).
    """
    low_min  = df['Low'].rolling(window=period, min_periods=1).min()
    high_max = df['High'].rolling(window=period, min_periods=1).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
    K = rsv.ewm(com=2, adjust=False).mean()
    D = K.ewm(com=2, adjust=False).mean()
    J = 3.0 * K - 2.0 * D
    return K, D, J

def calc_wavetrend(df, n1=10, n2=21):
    """
    WaveTrend Oscillator (LazyBear).
    wt1 crosses above wt2 = bullish signal; below = bearish.
    Returns: wt1, wt2 Series.
    """
    ap  = (df['High'] + df['Low'] + df['Close']) / 3.0
    esa = ap.ewm(span=n1, adjust=False).mean()
    d   = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    ci  = (ap - esa) / (0.015 * d.replace(0, np.nan))
    wt1 = ci.ewm(span=n2, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    return wt1, wt2

def calc_mfi(df, period=14):
    """
    Money Flow Index (volume-weighted RSI).
    Returns: MFI Series (0–100).
    """
    typical = (df['High'] + df['Low'] + df['Close']) / 3.0
    raw_mf  = typical * df['Volume']
    pos_mf  = raw_mf.where(typical > typical.shift(1), 0.0).rolling(window=period).sum()
    neg_mf  = raw_mf.where(typical <= typical.shift(1), 0.0).rolling(window=period).sum()
    mfr     = pos_mf / (neg_mf + 1e-10)
    return 100 - (100 / (1 + mfr))


# ── 12. MEAN REVERSION ────────────────────────────────────────────────────────

def calc_vwap(df):
    """
    Daily-reset VWAP.
    Resets at each calendar day boundary (UTC).
    Returns: vwap Series aligned to df.index.
    """
    tp   = (df['High'] + df['Low'] + df['Close']) / 3.0
    tp_v = tp * df['Volume']
    dates = df.index.normalize()
    cumtpv = tp_v.groupby(dates).cumsum()
    cumvol = df['Volume'].groupby(dates).cumsum()
    return cumtpv / cumvol.replace(0, np.nan)

def calc_zscore(series, period=20):
    """
    Rolling Z-score of any series.
    Returns: z-score Series (mean=0, std=1 window).
    """
    mean = series.rolling(window=period).mean()
    std  = series.rolling(window=period).std()
    return (series - mean) / (std + 1e-10)


# ── 13. CHANNEL INDICATORS ────────────────────────────────────────────────────

def calc_donchian_channels(df, period=20):
    """
    Donchian Channels (Turtle Trader breakout levels).
    Returns: upper, mid, lower Series.
      upper = highest High over period
      lower = lowest Low over period
      mid   = (upper + lower) / 2
    """
    upper = df['High'].rolling(window=period).max()
    lower = df['Low'].rolling(window=period).min()
    mid   = (upper + lower) / 2.0
    return upper, mid, lower

def calc_vwma(df, period=20):
    """
    Volume-Weighted Moving Average (VWMA / FVMA proxy).
    Returns: vwma Series.
    """
    tp_v = df['Close'] * df['Volume']
    return tp_v.rolling(window=period).sum() / df['Volume'].rolling(window=period).sum()


# ── 14. ADVANCED MOVING AVERAGES ─────────────────────────────────────────────

def calc_mcginley_dynamic(df, period=14):
    """
    McGinley Dynamic Indicator.
    Tracks market prices without the whipsaws of simple or exponential moving averages.
    Formula: MD_i = MD_{i-1} + (Close_i - MD_{i-1}) / (0.6 * period * (Close_i / MD_{i-1})**4)
    Returns: mcginley Series.
    """
    md = np.zeros(len(df))
    close = df['Close'].values
    
    md[0] = close[0]
    for i in range(1, len(df)):
        if md[i-1] == 0:
            md[i] = close[i]
            continue
        ratio = close[i] / md[i-1]
        md[i] = md[i-1] + (close[i] - md[i-1]) / (0.6 * period * (ratio ** 4))
        
    return pd.Series(md, index=df.index)

def calc_zlema(series, period=20):
    """
    Zero-Lag EMA (DEMA variant).
    Reduces lag by correcting for the EMA's own lag: 2×EMA1 − EMA2.
    Returns: zlema Series.
    """
    ema1 = talib.EMA(series, timeperiod=period)
    ema2 = talib.EMA(ema1, timeperiod=period)
    return ema1 + (ema1 - ema2)

def calc_t3(series, length=5, vf=0.7):
    """
    T3 Adaptive Moving Average (Tillson).
    Smoother than EMA with minimal lag. vf (volume factor) controls smoothness:
    vf=0 → SMA, vf=1 → maximum responsiveness.
    Returns: t3 Series.
    """
    a  = vf
    e1 = series.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    e3 = e2.ewm(span=length, adjust=False).mean()
    e4 = e3.ewm(span=length, adjust=False).mean()
    e5 = e4.ewm(span=length, adjust=False).mean()
    e6 = e5.ewm(span=length, adjust=False).mean()
    c1 = -(a ** 3)
    c2 = 3 * a**2 + 3 * a**3
    c3 = -6 * a**2 - 3 * a - 3 * a**3
    c4 = 1 + 3 * a + a**3 + 3 * a**2
    return c1*e6 + c2*e5 + c3*e4 + c4*e3

def calc_zero_lag_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    """
    Zero-Lag MACD — built on DEMA instead of EMA to reduce signal lag.
    Returns: zmacd, signal Series.
    """
    dema_fast = calc_zlema(df['Close'], fastperiod)
    dema_slow = calc_zlema(df['Close'], slowperiod)
    zmacd  = dema_fast - dema_slow
    signal = talib.EMA(zmacd, timeperiod=signalperiod)
    return zmacd, signal


# ── 15. MOMENTUM — ADVANCED ───────────────────────────────────────────────────

def calc_tsi(series, fast=13, slow=25):
    """
    True Strength Index (TSI).
    Double-smoothed momentum normalised by double-smoothed absolute momentum.
    Returns: TSI Series (range roughly −100 to +100, centre 0).
    """
    diff     = series.diff()
    abs_diff = diff.abs()
    num = diff.ewm(span=fast, adjust=False).mean().ewm(span=slow, adjust=False).mean()
    den = abs_diff.ewm(span=fast, adjust=False).mean().ewm(span=slow, adjust=False).mean()
    return (num / (den + 1e-10)) * 100


# ── 16. CANDLE PATTERN DETECTORS ─────────────────────────────────────────────

def detect_candle_engulfing(df):
    """
    Bullish Engulfing candle pattern.
    Current candle is bullish, opens at/below prev close, closes at/above prev open.
    Returns: Boolean Series (True = bullish engulfing).
    """
    po = df['Open'].shift(1)
    pc = df['Close'].shift(1)
    co = df['Open']
    cc = df['Close']
    return (cc > co) & (co <= pc) & (cc >= po)

def detect_candle_hammer(df):
    """
    Hammer / Pin Bar pattern.
    Lower shadow ≥ 2× body, upper shadow ≤ body — signals potential reversal.
    Returns: Boolean Series (True = hammer).
    """
    body         = (df['Close'] - df['Open']).abs().clip(lower=1e-10)
    lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
    upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
    return (lower_shadow >= 2.0 * body) & (upper_shadow <= body)

def detect_candle_bearish_engulfing(df):
    """
    Bearish Engulfing candle pattern.
    Current candle is bearish, opens at/above prev close, closes at/below prev open.
    Returns: Boolean Series (True = bearish engulfing).
    """
    po = df['Open'].shift(1)
    pc = df['Close'].shift(1)
    co = df['Open']
    cc = df['Close']
    return (cc < co) & (co >= pc) & (cc <= po)

def detect_candle_shooting_star(df):
    """
    Shooting Star pattern (Bearish Pin Bar).
    Upper shadow ≥ 2× body, lower shadow ≤ body — signals potential reversal.
    Returns: Boolean Series (True = shooting star).
    """
    body         = (df['Close'] - df['Open']).abs().clip(lower=1e-10)
    lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
    upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
    return (upper_shadow >= 2.0 * body) & (lower_shadow <= body)


# ── 17. STOCHASTIC KDJ ───────────────────────────────────────────────────────

def calc_kdj(df, period=9):
    """
    Stochastic KDJ oscillator.
    K = smoothed RSV (raw stochastic), D = smoothed K, J = 3K − 2D.
    Returns: K, D, J Series (0–100 scale; J can exceed range).
    """
    low_min  = df['Low'].rolling(window=period, min_periods=1).min()
    high_max = df['High'].rolling(window=period, min_periods=1).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
    K = rsv.ewm(com=2, adjust=False).mean()
    D = K.ewm(com=2, adjust=False).mean()
    J = 3.0 * K - 2.0 * D
    return K, D, J


# ── 18. UTILITY ──────────────────────────────────────────────────────────────

def window_any_true(series, window):
    """
    Rolling 'was this condition true within the last N bars?'
    Converts a boolean series to 1/0 then takes a rolling max.
    Returns: Boolean Series.
    """
    return series.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool)


# ── 19. FISHER TRANSFORM ─────────────────────────────────────────────────────

def calc_fisher_transform(df, period=10):
    """
    Fisher Transform oscillator (Ehlers).
    Normalises price to [-0.999, 0.999] then applies the log transform.
    Returns: fisher, trigger Series (trigger = fisher.shift(1)).
    """
    high_n = df['High'].rolling(window=period).max()
    low_n  = df['Low'].rolling(window=period).min()
    price_range = (high_n - low_n).replace(0, 1e-4)
    raw_value   = 2 * ((df['Close'] - low_n) / price_range - 0.5)

    value  = np.zeros(len(df))
    fisher = np.zeros(len(df))
    rv     = raw_value.values
    for i in range(1, len(df)):
        if np.isnan(rv[i]):
            continue
        value[i] = 0.33 * rv[i] + 0.67 * value[i - 1]
        v = max(min(value[i], 0.999), -0.999)
        fisher[i] = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * fisher[i - 1]

    fisher_s  = pd.Series(fisher, index=df.index)
    trigger_s = fisher_s.shift(1)
    return fisher_s, trigger_s


# ── 20. VOLUME-WEIGHTED RSI (VRSI) ───────────────────────────────────────────

def calc_vrsi(df, period=14):
    """
    Volume-Weighted RSI — RSI where up/down moves are scaled by volume.
    Useful for detecting volume-exhaustion reversals.
    Returns: vrsi Series (0–100).
    """
    price_chg = df['Close'].diff()
    U = df['Volume'] * price_chg.clip(lower=0)
    D = df['Volume'] * (-price_chg).clip(lower=0)
    sma_u = U.rolling(window=period, min_periods=period).mean()
    sma_d = D.rolling(window=period, min_periods=period).mean()
    rs = sma_u / (sma_d + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


# ── 22. CLASSIFICATION FACTORS ───────────────────────────────────────────────

def calc_lorentzian_classification(df, k_neighbors=5, history_window=2000, rsi_period=14, cci_period=14, adx_period=14):
    """
    Calculates a classification score based on Lorentzian K-Nearest Neighbors (KNN).
    Classifies market state (bullish/bearish) based on historical patterns using RSI, CCI, ADX.
    Returns: pd.Series of prediction scores (+/- based on majority vote).
    """
    
    # Ensure DataFrame is sorted by index
    df = df.sort_index()

    # 1. Compute features
    rsi = talib.RSI(df['Close'], timeperiod=rsi_period)
    cci = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=cci_period)
    adx_full = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=adx_period)
    # The ADX from talib.ADX is already the ADX value
    
    # Create feature DataFrame
    features_df = pd.DataFrame({'rsi': rsi, 'cci': cci, 'adx': adx_full}, index=df.index)
    features_df = features_df.dropna() # Drop rows with NaN values from indicator calculation

    if features_df.empty:
        return pd.Series(0, index=df.index)

    # 2. Define Lorentzian Distance Function
    def lorentzian_distance(vec1, vec2):
        # Ensure vectors are numpy arrays for element-wise operations
        vec1 = np.asarray(vec1)
        vec2 = np.asarray(vec2)
        # Add a small epsilon to prevent log(0)
        return np.sum(np.log(1 + np.abs(vec1 - vec2) + 1e-10))

    # 3. Prepare historical labels (simple heuristic for demonstration)
    # Placeholder: +1 for bullish candle (close > open), -1 for bearish (close < open), 0 otherwise
    historical_labels = pd.Series(0, index=df.index, dtype=int)
    historical_labels[df['Close'] > df['Open']] = 1
    historical_labels[df['Close'] < df['Open']] = -1
    
    # Ensure labels align with features_df index
    historical_labels = historical_labels.loc[features_df.index]

    prediction_scores = pd.Series(0.0, index=features_df.index)

    # Iterate through the DataFrame to perform KNN for each bar
    # Start iteration after enough data for history_window and k_neighbors
    min_history_needed = max(history_window, rsi_period, cci_period, adx_period) + 1
    if len(features_df) <= min_history_needed:
        return prediction_scores # Not enough data to compute

    for i in range(min_history_needed, len(features_df)):
        current_vector = features_df.iloc[i].values
        
        # Define rolling history window
        # The history should be from before the current bar
        rolling_history_features = features_df.iloc[max(0, i - history_window):i].values
        rolling_history_labels = historical_labels.iloc[max(0, i - history_window):i].values
        
        if len(rolling_history_features) == 0:
            continue

        distances = []
        for j in range(len(rolling_history_features)):
            dist = lorentzian_distance(current_vector, rolling_history_features[j])
            distances.append((dist, rolling_history_labels[j])) # Store distance with its label

        # Sort by distance and get k_neighbors
        distances.sort(key=lambda x: x[0])
        k_nearest = distances[:k_neighbors]

        # Calculate prediction score (sum of labels of k_nearest neighbors)
        # Note: The card pseudocode implies labels are directly summed for score
        prediction_score = sum([label for _, label in k_nearest])
        prediction_scores.iloc[i] = prediction_score

    return prediction_scores


# ── 21. CUMULATIVE VOLUME DELTA (CVD) ────────────────────────────────────────

def calc_cvd(df, window=20):
    """
    Cumulative Volume Delta — rolling sum of (taker_buy − taker_sell) volume.
    Requires 'taker_buy_base_vol' column; falls back to 0.5 × Volume when absent.
    Returns: cvd Series.
    """
    if 'taker_buy_base_vol' in df.columns:
        taker_buy = pd.to_numeric(df['taker_buy_base_vol'], errors='coerce').fillna(0)
    else:
        taker_buy = df['Volume'] * 0.5
    delta = 2 * taker_buy - df['Volume']
    return delta.rolling(window=window).sum()

# ── 22. ALPHA PRIMITIVES (TS & MATH) ─────────────────────────────────────────

def ts_corr(series_x, series_y, window):
    """
    Time-series rolling correlation between two series.
    Returns: Series
    """
    return series_x.rolling(window=window).corr(series_y)

def ts_min(series, window):
    """
    Time-series rolling minimum.
    Returns: Series
    """
    return series.rolling(window=window).min()

def S_log1p(series):
    """
    Signed log1p transformation to normalize heavy-tailed distributions.
    S_log1p(x) = sign(x) * log(1 + abs(x))
    Returns: Series
    """
    return np.sign(series) * np.log1p(np.abs(series))


# ── 23. ORDER BOOK (LEVEL 2 DEPTH) ───────────────────────────────────────────

def calc_orderbook_imbalance(df, level=1.0):
    """
    Calculates Order Book Imbalance (Bid Notional vs Ask Notional) at a specific % depth.
    Formula: Bid_Depth / (Bid_Depth + Ask_Depth).
    > 0.5 means bid-heavy (buyers stacking), < 0.5 means ask-heavy (sellers stacking).
    Falls back to 0.5 if orderbook data is missing.
    """
    bid_col = f'notional_{-float(level)}'
    ask_col = f'notional_{float(level)}'
    
    if bid_col in df.columns and ask_col in df.columns:
        bid = df[bid_col].fillna(0)
        ask = df[ask_col].fillna(0)
        imbalance = bid / (bid + ask + 1e-10)
        return imbalance.fillna(0.5)
    else:
        return pd.Series(0.5, index=df.index)

# ── KALMAN FILTER ───────────────────────────────────────────────

def calc_kalman_filter(series, noise=0.01):
    """
    1D Kalman Filter for price smoothing.
    Returns: kalman_state Series
    """
    import numpy as np
    import pandas as pd
    kalman = np.zeros(len(series))
    values = series.values
    kalman[0] = values[0]
    error_cov = 1.0
    process_variance = 1e-5
    measurement_variance = noise
    
    for i in range(1, len(series)):
        pred_cov = error_cov + process_variance
        kalman_gain = pred_cov / (pred_cov + measurement_variance)
        kalman[i] = kalman[i-1] + kalman_gain * (values[i] - kalman[i-1])
        error_cov = (1 - kalman_gain) * pred_cov
        
    return pd.Series(kalman, index=series.index)

# ── 24. NEW FACTORS (EFR-MR, LER, FRDS) ──────────────────────────────────────

def calc_spot_obi(df, level=1.0):
    """
    Spot Order Book Imbalance = (Bid_Depth - Ask_Depth) / (Bid_Depth + Ask_Depth).
    """
    bid_col = f'depth_{-float(level)}'
    ask_col = f'depth_{float(level)}'
    if bid_col in df.columns and ask_col in df.columns:
        bid = df[bid_col].fillna(0)
        ask = df[ask_col].fillna(0)
        obi = (bid - ask) / (bid + ask + 1e-10)
        return obi
    else:
        return pd.Series(0.0, index=df.index)

def calc_depth_imbalance(df, level=1.0):
    """
    Depth Imbalance = Ask_Depth - Bid_Depth.
    """
    bid_col = f'depth_{-float(level)}'
    ask_col = f'depth_{float(level)}'
    if bid_col in df.columns and ask_col in df.columns:
        bid = df[bid_col].fillna(0)
        ask = df[ask_col].fillna(0)
        return ask - bid
    else:
        return pd.Series(0.0, index=df.index)

def calc_linear_regression_slope(series, period=12):
    """
    Calculates rolling linear regression slope.
    """
    import numpy as np
    x = np.arange(period)
    x_mean = x.mean()
    x_diff = x - x_mean
    x_var = np.sum(x_diff ** 2)

    def slope(y):
        if len(y) < period or np.isnan(y).any():
            return 0.0
        return np.sum((y - np.mean(y)) * x_diff) / x_var

    return series.rolling(window=period).apply(slope, raw=True)

# ── PURE PYTHON INDICATORS (FOR BT.CORE) ──────────────────────────────────────
import collections
import math

class PureEMA:
    def __init__(self, period):
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.val = None
    def update(self, price):
        if self.val is None:
            self.val = price
        else:
            self.val = self.alpha * price + (1 - self.alpha) * self.val
        return self.val

class PureSMA:
    def __init__(self, period):
        self.period = period
        self.q = collections.deque(maxlen=period)
    def update(self, val):
        if val is None: return None
        self.q.append(val)
        if len(self.q) == self.period:
            return sum(self.q)/self.period
        return None

class PureMACD:
    def __init__(self, fast, slow, sig):
        self.fast_ema = PureEMA(fast)
        self.slow_ema = PureEMA(slow)
        self.sig_ema = PureEMA(sig)
    def update(self, price):
        f = self.fast_ema.update(price)
        s = self.slow_ema.update(price)
        if f is None or s is None:
            return None, None, None
        macd = f - s
        sig = self.sig_ema.update(macd)
        if sig is None:
            return macd, None, None
        return macd, sig, macd - sig

class PureRSI:
    def __init__(self, period):
        self.period = period
        self.gains = PureEMA(period)
        self.losses = PureEMA(period)
        self.prev = None
        self.gains.alpha = 1.0 / period
        self.losses.alpha = 1.0 / period
    def update(self, price):
        if self.prev is None:
            self.prev = price
            return None
        change = price - self.prev
        self.prev = price
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        
        avg_gain = self.gains.update(gain)
        avg_loss = self.losses.update(loss)
        if avg_loss == 0:
            return 100.0
        if avg_gain is None or avg_loss is None:
            return None
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

class PureATR:
    def __init__(self, period):
        self.period = period
        self.ema = PureEMA(period)
        self.ema.alpha = 1.0 / period
        self.prev_close = None
    def update(self, high, low, close):
        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.prev_close = close
        return self.ema.update(tr)

class PureKDJ:
    def __init__(self, period):
        self.period = period
        self.highs = collections.deque(maxlen=period)
        self.lows = collections.deque(maxlen=period)
        self.k_ema = PureEMA(3)
        self.k_ema.alpha = 1/3.0
        self.d_ema = PureEMA(3)
        self.d_ema.alpha = 1/3.0
    def update(self, high, low, close):
        self.highs.append(high)
        self.lows.append(low)
        hh = max(self.highs)
        ll = min(self.lows)
        if hh == ll:
            rsv = 0.0
        else:
            rsv = (close - ll) / (hh - ll) * 100.0
        k = self.k_ema.update(rsv)
        if k is None: k = 50.0
        d = self.d_ema.update(k)
        if d is None: d = 50.0
        j = 3.0 * k - 2.0 * d
        return k, d, j

class PureVWAP:
    def __init__(self, reset_bars=0):
        self.reset_bars = reset_bars
        self.bars = 0
        self.cum_pv = 0.0
        self.cum_v = 0.0
    def update(self, price, vol):
        self.bars += 1
        if self.reset_bars and self.bars > self.reset_bars:
            self.cum_pv = 0.0
            self.cum_v = 0.0
            self.bars = 1
        self.cum_pv += price * vol
        self.cum_v += vol
        if self.cum_v == 0: return price
        return self.cum_pv / self.cum_v
    def reset(self):
        self.cum_pv = 0.0
        self.cum_v = 0.0
        self.bars = 0

class PureVWMA:
    def __init__(self, period):
        self.period = period
        self.pvs = collections.deque(maxlen=period)
        self.vs = collections.deque(maxlen=period)
    def update(self, price, vol):
        self.pvs.append(price * vol)
        self.vs.append(vol)
        v_sum = sum(self.vs)
        if v_sum == 0: return price
        return sum(self.pvs) / v_sum

class PureSupertrend:
    def __init__(self, period, multiplier):
        self.period = period
        self.multiplier = multiplier
        self.atr = PureATR(period)
        self.final_ub = None
        self.final_lb = None
        self.direction = 1
        self.prev_close = None
    def update(self, high, low, close):
        atr_val = self.atr.update(high, low, close)
        if atr_val is None:
            self.prev_close = close
            return None, self.direction
        hl2 = (high + low) / 2.0
        basic_ub = hl2 + self.multiplier * atr_val
        basic_lb = hl2 - self.multiplier * atr_val
        
        if self.final_ub is None:
            self.final_ub = basic_ub
            self.final_lb = basic_lb
            
        if self.prev_close is not None:
            if basic_ub < self.final_ub or self.prev_close > self.final_ub:
                self.final_ub = basic_ub
            if basic_lb > self.final_lb or self.prev_close < self.final_lb:
                self.final_lb = basic_lb
                
        if self.direction == -1 and close > self.final_ub:
            self.direction = 1
            self.final_lb = basic_lb
        elif self.direction == 1 and close < self.final_lb:
            self.direction = -1
            self.final_ub = basic_ub
            
        self.prev_close = close
        st = self.final_lb if self.direction == 1 else self.final_ub
        return st, self.direction

class PureRollingStats:
    def __init__(self, period):
        self.period = period
        self.q = collections.deque(maxlen=period)
    def update(self, val):
        self.q.append(val)
        n = len(self.q)
        if n == self.period:
            mean = sum(self.q) / n
            var = sum((x - mean)**2 for x in self.q) / n
            std = math.sqrt(var)
            return mean, std
        return None, None

class RollingCondition:
    def __init__(self, window):
        self.window = window
        self.q = collections.deque(maxlen=window)
    def update(self, cond):
        self.q.append(cond)
        return any(self.q)

class PureCross:
    def __init__(self):
        self.prev_a = None
        self.prev_b = None
    def update(self, a, b):
        if self.prev_a is None or a is None or b is None:
            self.prev_a = a
            self.prev_b = b
            return False, False
        cross_up = (a > b) and (self.prev_a <= self.prev_b)
        cross_down = (a < b) and (self.prev_a >= self.prev_b)
        self.prev_a = a
        self.prev_b = b
        return cross_up, cross_down

class PureTurn:
    def __init__(self):
        self.prev = None
    def update(self, val):
        if self.prev is None or val is None:
            self.prev = val
            return False, False
        turn_pos = (val > 0) and (self.prev <= 0)
        turn_neg = (val < 0) and (self.prev >= 0)
        self.prev = val
        return turn_pos, turn_neg

class PureZLEMA:
    def __init__(self, period):
        self.ema1 = PureEMA(period)
        self.ema2 = PureEMA(period)
    def update(self, price):
        e1 = self.ema1.update(price)
        if e1 is None: return None
        e2 = self.ema2.update(e1)
        if e2 is None: return None
        return e1 + (e1 - e2)

class PureZeroLagMACD:
    def __init__(self, fast, slow, sig):
        self.z_fast = PureZLEMA(fast)
        self.z_slow = PureZLEMA(slow)
        self.z_sig = PureZLEMA(sig)
        self.prev_macd = None
    def update(self, price):
        f = self.z_fast.update(price)
        s = self.z_slow.update(price)
        if f is None or s is None: return None, None, None
        macd = f - s
        sig = self.z_sig.update(macd)
        self.prev_macd = macd
        if sig is None: return macd, None, None
        return macd, sig, macd - sig


# ── 16. TREND INTENSITY INDEX (TII) ─────────────────────────────────────────

def calc_trend_intensity_index(close: pd.Series, major_period: int = 60, minor_period: int = 30) -> pd.Series:
    """
    Trend Intensity Index (TII) — M.H. Pee.

    Measures the percentage of positive deviation relative to total absolute deviation
    from a long-term SMA. Values above 80 indicate a strong uptrend; below 20 a strong
    downtrend.

    Args:
        close: Close price series.
        major_period: Lookback for the long-term SMA (default 60).
        minor_period: Rolling sum window for deviation aggregation (default 30).

    Returns:
        pd.Series of TII values in [0, 100].
    """
    ma = close.rolling(window=major_period).mean()
    dev = close - ma

    sd_plus  = dev.clip(lower=0).rolling(window=minor_period).sum()
    sd_minus = dev.clip(upper=0).abs().rolling(window=minor_period).sum()

    total = sd_plus + sd_minus
    tii = 100.0 * sd_plus / total.replace(0, np.nan)
    return tii.fillna(50.0)


def calc_bbw(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.0) -> pd.Series:
    """
    Bollinger Band Width (BBW) — normalized.

    BBW = (Upper Band - Lower Band) / Middle Band.
    Low values indicate squeeze / consolidation; high values indicate expansion.

    Args:
        df: DataFrame with 'Close' column.
        bb_period: Bollinger Band window (default 20).
        bb_std: Standard deviation multiplier (default 2.0).

    Returns:
        pd.Series of BBW values.
    """
    upper, mid, lower = talib.BBANDS(df['Close'], timeperiod=bb_period, nbdevup=bb_std, nbdevdn=bb_std)
    bbw = (upper - lower) / mid.replace(0, np.nan)
    return bbw.fillna(0.0)


def calc_hmm_regime_classifier(df: pd.DataFrame, n_states: int = 3) -> pd.Series:
    """
    Hidden Markov Model regime classifier using Gaussian emissions.

    Fits a GaussianHMM on (log_return, norm_ATR) features and decodes states,
    then sorts them by mean log return:  0=bearish, 1=sideways, 2=bullish.

    Args:
        df:       DataFrame with Open/High/Low/Close columns.
        n_states: Number of HMM hidden states (default 3).

    Returns:
        pd.Series of int regime labels: 0=bearish, 1=sideways, 2=bullish.
    """
    from hmmlearn import hmm

    close    = df['Close'].astype(float)
    log_ret  = np.log(close / close.shift(1))
    atr      = calc_atr(df, 14)
    norm_vol = (atr / close.replace(0, np.nan))

    features = pd.concat([log_ret, norm_vol], axis=1)
    features.replace([np.inf, -np.inf], np.nan, inplace=True)
    valid    = features.notna().all(axis=1)
    X        = features[valid].values.astype(float)

    # Default to sideways when not enough data
    regime = pd.Series(1, index=df.index, dtype=int)

    if len(X) < n_states * 50:
        return regime

    try:
        model = hmm.GaussianHMM(
            n_components=n_states, covariance_type='full',
            n_iter=100, random_state=42, tol=1e-4,
        )
        model.fit(X)
        raw_states = model.predict(X)
    except Exception:
        return regime

    # Sort raw state IDs by mean log return (feature col 0) → ascending
    state_means   = [X[raw_states == s, 0].mean() if (raw_states == s).sum() > 0 else 0.0
                     for s in range(n_states)]
    sorted_order  = sorted(range(n_states), key=lambda s: state_means[s])
    raw_to_named  = {raw: named for named, raw in enumerate(sorted_order)}

    named_states        = pd.Series([raw_to_named[r] for r in raw_states], index=df.index[valid])
    regime.loc[valid]   = named_states
    return regime

def calc_amihud_illiq(df, period=20):
    """
    Calculates Amihud Illiquidity ratio: abs(returns) / volume.
    Returns: ILLIQ Series.
    """
    illiq = df['Close'].pct_change().abs() / (df['Volume'] + 1e-10)
    return illiq.rolling(window=period).mean()

def calc_ou_mr_speed(df, period=20):
    """
    Calculates Ornstein-Uhlenbeck mean-reversion speed (kappa).
    Uses price deviation from EMA(period).
    Returns: kappa Series.
    """
    dev = df['Close'] - df['Close'].ewm(span=period).mean()
    # AR(1) coefficient (phi)
    phi = dev.rolling(window=period).corr(dev.shift(1))
    # Kappa formula: -log(phi) * 252 (annualized)
    # Clip phi to (0, 1) to avoid log of non-positive
    kappa = -np.log(phi.clip(1e-10, 0.999)) * 252
    return kappa

# ── CROSS-SECTIONAL FACTORS ────────────────────────────────────────────────
def calc_roc(df, period=14):
    """
    Calculates the Rate of Change (Momentum) of the Close price.
    Returns: ROC Series (percentage).
    """
    return talib.ROC(df['Close'], timeperiod=period)

def calc_csi(df, period=20):
    """
    Candle Sentiment Index (CSI).
    Formula: (POS_bars - NEG_bars) / period
    POS_bar: Close > Open
    NEG_bar: Close < Open
    Returns: CSI Series ranging from -1 to 1.
    """
    pos_bars = (df['Close'] > df['Open']).astype(int)
    neg_bars = (df['Close'] < df['Open']).astype(int)
    
    rolling_pos = pos_bars.rolling(window=period).sum()
    rolling_neg = neg_bars.rolling(window=period).sum()
    
    csi = (rolling_pos - rolling_neg) / period
    return csi

def calc_volume_hurst(df: pd.DataFrame, period: int = 100) -> pd.Series:
    """
    Approximates the Hurst exponent of the Volume series using a rolling Variance Ratio.
    H ≈ 0.5 + 0.5 * log2( Var(x - x_lag2) / (2 * Var(x - x_lag1)) )
    
    If H > 0.5: Persistent (trending volume - surges tend to follow surges)
    If H < 0.5: Anti-persistent (mean-reverting volume - spikes die off quickly)
    If H = 0.5: Random walk
    """
    v = df['Volume']
    
    # 1-period diff variance
    diff1 = v.diff(1)
    var1 = diff1.rolling(period).var()
    
    # 2-period diff variance
    diff2 = v.diff(2)
    var2 = diff2.rolling(period).var()
    
    # Avoid division by zero
    var1 = var1.replace(0, np.nan)
    
    # Approximate Hurst
    h_approx = 0.5 + 0.5 * np.log2(var2 / (2 * var1))
    
    return h_approx.fillna(0.5)

def calc_ts_rank(series: pd.Series, period: int) -> pd.Series:
    """
    Time-Series Rank: Returns the percentile rank of the current value 
    within its trailing window of length `period`.
    Ranges from 0.0 to 1.0.
    """
    def _rank(x):
        # Number of elements less than or equal to the last element
        return (x <= x[-1]).sum() / len(x)
    
    return series.rolling(period).apply(_rank, raw=True)

def calc_vol_change_momentum(df: pd.DataFrame, delta_p: int = 2, corr_p: int = 6, ts_p: int = 10) -> pd.Series:
    """
    Volume-change momentum anti-corr (WorldQuant Alpha #2 adaptation).
    Formula: -corr(ts_rank(delta(log(vol), delta_p)), ts_rank((close-open)/open), corr_p)
    """
    # delta(log(vol), 2)
    log_vol = np.log(df['Volume'].replace(0, np.nan))
    d_log_vol = log_vol.diff(delta_p)
    
    # ts_rank of d_log_vol
    rank_vol = calc_ts_rank(d_log_vol, ts_p)
    
    # (close-open)/open
    ret_intra = (df['Close'] - df['Open']) / df['Open'].replace(0, np.nan)
    rank_ret = calc_ts_rank(ret_intra, ts_p)
    
    # Rolling correlation
    corr = rank_vol.rolling(corr_p).corr(rank_ret)
    
    # Return negative correlation
    return -corr

def calc_open_vol_anticorr(df: pd.DataFrame, ts_p: int = 10, corr_p: int = 10) -> pd.Series:
    """
    Open-volume anticorrelation (WorldQuant Alpha #3 adaptation).
    Formula: -corr(rank(open), rank(vol), 10)
    Using time-series rank for a single asset.
    """
    rank_open = calc_ts_rank(df['Open'], ts_p)
    rank_vol = calc_ts_rank(df['Volume'].replace(0, np.nan), ts_p)
    
    corr = rank_open.rolling(corr_p).corr(rank_vol)
    
    return -corr

def calc_vwap_dist_vol_delta(df: pd.DataFrame, ts_p: int = 10) -> pd.Series:
    """
    VWAP distance x volume delta (WorldQuant Alpha #5 adaptation).
    Formula: rank(open - SMA(vwap, ts_p)) * sign(close - vwap) * rank(abs(close - vwap)) * rank(delta(volume, ts_p))
    """
    vwap = (df['High'] + df['Low'] + df['Close']) / 3

    f1 = calc_ts_rank(df['Open'] - vwap.rolling(ts_p).mean(), ts_p)
    f2 = np.sign(df['Close'] - vwap)
    f3 = calc_ts_rank(np.abs(df['Close'] - vwap), ts_p)
    f4 = calc_ts_rank(df['Volume'].replace(0, np.nan).diff(ts_p), ts_p)

    alpha = f1 * f2 * f3 * f4

    return alpha

def calc_vol_regime_reversal(df: pd.DataFrame, std_p: int = 20, argmax_p: int = 5, ts_p: int = 10) -> pd.Series:
    """
    Volatility regime reversal signal (WorldQuant Alpha #1 adaptation).
    Formula: rank(argmax(sign(ret<0) ? std(ret,20) : close, 5)) - 0.5
    """
    ret = df['Close'].pct_change()
    
    # Rolling std of returns
    rolling_std = ret.rolling(std_p).std()
    
    # Condition array
    val_array = np.where(ret < 0, rolling_std, df['Close'])
    val_series = pd.Series(val_array, index=df.index)
    
    # argmax over `argmax_p` periods
    argmax_series = val_series.rolling(argmax_p).apply(np.argmax, raw=True)
    
    # ts_rank - 0.5
    alpha = calc_ts_rank(argmax_series, ts_p) - 0.5
    
    return alpha

def calc_open_vol_corr_fade(df: pd.DataFrame, corr_p: int = 10) -> pd.Series:
    """
    Open-volume correlation fade (WorldQuant Alpha #6 adaptation).
    Formula: -corr(open, vol, 10)
    Uses linear correlation (Pearson).
    """
    corr = df['Open'].rolling(corr_p).corr(df['Volume'].replace(0, np.nan))
    
    return -corr

def calc_vol_surge_momentum_fade(df: pd.DataFrame, sma_p: int = 20, delta_p: int = 7, ts_p: int = 60) -> pd.Series:
    """
    Volume surge momentum fade (WorldQuant Alpha #7).
    Formula: (adv20 < vol) ? -ts_rank(abs(delta(close, 7)), 60) * sign(delta(close, 7)) : -1
    """
    adv = df['Volume'].rolling(sma_p).mean()
    vol_cond = adv < df['Volume']
    
    d_close = df['Close'].diff(delta_p)
    abs_d_close = np.abs(d_close)
    
    # ts_rank ranges from 0 to 1
    rank_abs = calc_ts_rank(abs_d_close, ts_p)
    
    surge_val = -rank_abs * np.sign(d_close)

    # 0 = neutral when no volume surge (original formula uses -1 but that creates
    # an implicit short bias in single-asset context; 0 means no signal)
    alpha = np.where(vol_cond, surge_val, 0)

    return pd.Series(alpha, index=df.index)

def calc_momentum_cross_term_reversal(df: pd.DataFrame, ts_p: int = 10, corr_p: int = 10, delta_p: int = 10, rank_p: int = 10) -> pd.Series:
    """
    Momentum cross-term reversal (WorldQuant Alpha #8 adaptation).
    Formula: -1 * rank(2 * rank(correlation(ts_rank(close, 10), ts_rank(volume, 10), 10)) - rank(delta(close, 10)))
    (Adapted to use time-series ranks entirely for a single-asset continuous alpha).
    """
    rank_close = calc_ts_rank(df['Close'], ts_p)
    rank_vol = calc_ts_rank(df['Volume'].replace(0, np.nan), ts_p)
    
    corr = rank_close.rolling(corr_p).corr(rank_vol)
    rank_corr = calc_ts_rank(corr, rank_p)
    
    d_close = df['Close'].diff(delta_p)
    rank_delta = calc_ts_rank(d_close, rank_p)
    
    # inner term
    inner = 2 * rank_corr - rank_delta
    
    # final rank
    alpha = -calc_ts_rank(inner, rank_p)
    
    return alpha

def calc_close_delta_conditional_flip(df: pd.DataFrame, delta_p: int = 1, ts_p: int = 5) -> pd.Series:
    """
    Close delta conditional flip (WorldQuant Alpha #9).
    Formula: ((ts_min(delta(close, 1), 5) > 0) ? delta(close, 1) : 
             ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
    """
    d_close = df['Close'].diff(delta_p)
    ts_min = d_close.rolling(ts_p).min()
    ts_max = d_close.rolling(ts_p).max()
    
    cond1 = ts_min > 0
    cond2 = ts_max < 0
    
    # if cond1 is true -> d_close
    # else if cond2 is true -> d_close
    # else -> -d_close
    # Which simplifies to: if (cond1 OR cond2) then d_close else -d_close
    alpha = np.where(cond1 | cond2, d_close, -d_close)
    
    return pd.Series(alpha, index=df.index)

def calc_ranked_conditional_close_delta(df: pd.DataFrame, delta_p: int = 1, ts_p: int = 4, rank_p: int = 10) -> pd.Series:
    """
    Ranked conditional close delta (WorldQuant Alpha #10 adaptation).
    Formula: rank(((ts_min(delta(close, 1), 4) > 0) ? delta(close, 1) : 
             ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))
    """
    d_close = df['Close'].diff(delta_p)
    ts_min = d_close.rolling(ts_p).min()
    ts_max = d_close.rolling(ts_p).max()
    
    cond1 = ts_min > 0
    cond2 = ts_max < 0
    
    alpha_raw = np.where(cond1 | cond2, d_close, -d_close)
    alpha_raw_series = pd.Series(alpha_raw, index=df.index)
    
    alpha = calc_ts_rank(alpha_raw_series, rank_p)
    
    return alpha

def calc_vwap_deviation_vol_rank(df: pd.DataFrame, ts_p: int = 3, rank_p: int = 10) -> pd.Series:
    """
    VWAP deviation × volume rank (WorldQuant Alpha #11 adaptation).
    Formula: ((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3)))
    (Adapted to use time-series ranks).
    """
    # Data loader only keeps OHLCV — compute bar VWAP inline as typical price
    vwap = (df['High'] + df['Low'] + df['Close']) / 3
    vwap_diff = vwap - df['Close']
    
    ts_max_diff = vwap_diff.rolling(ts_p).max()
    ts_min_diff = vwap_diff.rolling(ts_p).min()
    
    rank_max = calc_ts_rank(ts_max_diff, rank_p)
    rank_min = calc_ts_rank(ts_min_diff, rank_p)
    
    vol_delta = df['Volume'].diff(ts_p)
    rank_vol = calc_ts_rank(vol_delta, rank_p)
    
    alpha = (rank_max + rank_min) * rank_vol
    
    return alpha

def calc_volume_covariance_fade(df: pd.DataFrame, cov_p: int = 5, rank_p: int = 10) -> pd.Series:
    """
    Volume covariance fade (WorldQuant Alpha #13 adaptation).
    Formula: -rank(covariance(rank(close), rank(volume), 5))
    """
    rank_close = calc_ts_rank(df['Close'], rank_p)
    rank_vol = calc_ts_rank(df['Volume'].replace(0, np.nan), rank_p)
    
    cov = rank_close.rolling(cov_p).cov(rank_vol)
    
    alpha = -calc_ts_rank(cov, rank_p)
    
    return alpha

def calc_vol_return_anticorr_fade(df: pd.DataFrame, delta_p: int = 3, corr_p: int = 10, rank_p: int = 10) -> pd.Series:
    """
    Volume-return anti-correlation fade (WorldQuant Alpha #14 adaptation).
    Formula: -rank(delta(returns, 3)) * correlation(open, volume, 10)
    """
    returns = df['Close'].pct_change()
    ret_delta = returns.diff(delta_p)
    rank_ret_delta = calc_ts_rank(ret_delta, rank_p)
    
    corr = df['Open'].rolling(corr_p).corr(df['Volume'].replace(0, np.nan))
    
    alpha = -rank_ret_delta * corr
    
    return alpha

def calc_high_vol_3corr_cascade(df: pd.DataFrame, corr_p: int = 3, sum_p: int = 3, rank_p: int = 10) -> pd.Series:
    """
    High-volume 3-corr cascade (WorldQuant Alpha #15 adaptation).
    Formula: -1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3)
    """
    rank_high = calc_ts_rank(df['High'], rank_p)
    rank_vol = calc_ts_rank(df['Volume'].replace(0, np.nan), rank_p)
    
    corr = rank_high.rolling(corr_p).corr(rank_vol)
    rank_corr = calc_ts_rank(corr, rank_p)
    
    alpha = -1 * rank_corr.rolling(sum_p).sum()
    
    return alpha

def calc_high_vol_covariance_fade(df: pd.DataFrame, cov_p: int = 5, rank_p: int = 10) -> pd.Series:
    """
    High-volume covariance fade (WorldQuant Alpha #16 adaptation).
    Formula: -rank(covariance(rank(high), rank(volume), 5))
    """
    rank_high = calc_ts_rank(df['High'], rank_p)
    rank_vol = calc_ts_rank(df['Volume'].replace(0, np.nan), rank_p)
    
    cov = rank_high.rolling(cov_p).cov(rank_vol)
    
    alpha = -calc_ts_rank(cov, rank_p)
    
    return alpha

def calc_triple_interaction_momentum(df: pd.DataFrame, ts_p1: int = 10, ts_p2: int = 5, sma_p: int = 20, rank_p: int = 10) -> pd.Series:
    """
    Triple-interaction momentum (WorldQuant Alpha #17 adaptation).
    Formula: (((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) * rank(ts_rank((volume / adv20), 5)))
    """
    # Term 1: -1 * rank(ts_rank(close, 10))
    t1_inner = calc_ts_rank(df['Close'], ts_p1)
    term1 = -1 * calc_ts_rank(t1_inner, rank_p)
    
    # Term 2: rank(delta(delta(close, 1), 1)) -> basically acceleration of close
    accel = df['Close'].diff(1).diff(1)
    term2 = calc_ts_rank(accel, rank_p)
    
    # Term 3: rank(ts_rank((volume / adv20), 5))
    adv20 = df['Volume'].rolling(sma_p).mean()
    vol_ratio = df['Volume'] / adv20.replace(0, np.nan)
    t3_inner = calc_ts_rank(vol_ratio, ts_p2)
    term3 = calc_ts_rank(t3_inner, rank_p)
    
    alpha = term1 * term2 * term3
    
    return alpha

def calc_stddev_gap_cross(df: pd.DataFrame, std_p: int = 5, ts_p: int = 5, rank_p: int = 10) -> pd.Series:
    """
    Standard deviation gap cross (WorldQuant Alpha #18 adaptation).
    Formula: -rank(ts_rank(stddev(abs(close - open), 5), 5) + ts_rank(stddev(close, 5), 5))
    """
    body_abs = np.abs(df['Close'] - df['Open'])
    std_body = body_abs.rolling(std_p).std()
    ts_rank_body = calc_ts_rank(std_body, ts_p)
    
    std_close = df['Close'].rolling(std_p).std()
    ts_rank_close = calc_ts_rank(std_close, ts_p)
    
    inner_sum = ts_rank_body + ts_rank_close
    alpha = -calc_ts_rank(inner_sum, rank_p)
    
    return alpha

def calc_close_return_cond_gap(df: pd.DataFrame, delta_p: int = 7, sum_p: int = 60, rank_p: int = 10) -> pd.Series:
    """
    Close-return conditional gap (WorldQuant Alpha #19 adaptation).
    Formula: ((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank(1 + sum(returns, 250))))
    Simplifies to: -sign(delta(close, 7)) * (1 + rank(sum(returns, 250)))
    """
    d_close = df['Close'].diff(delta_p)
    term1 = -np.sign(d_close)
    
    returns = df['Close'].pct_change()
    sum_ret = returns.rolling(sum_p).sum()
    term2 = 1 + calc_ts_rank(sum_ret, rank_p)
    
    alpha = term1 * term2
    
    return alpha

def calc_open_close_gap_cascade(df: pd.DataFrame, rank_p: int = 10) -> pd.Series:
    """
    Open-close gap cascade (WorldQuant Alpha #20 adaptation).
    Formula: (((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open - delay(low, 1))))
    """
    open_high_gap = df['Open'] - df['High'].shift(1)
    open_close_gap = df['Open'] - df['Close'].shift(1)
    open_low_gap = df['Open'] - df['Low'].shift(1)
    
    rank1 = -1 * calc_ts_rank(open_high_gap, rank_p)
    rank2 = calc_ts_rank(open_close_gap, rank_p)
    rank3 = calc_ts_rank(open_low_gap, rank_p)
    
    alpha = rank1 * rank2 * rank3
    
    return alpha

def calc_adv_low_mean_revert(df: pd.DataFrame, adv_p: int = 20, corr_p: int = 5) -> pd.Series:
    """
    Adv-low mean-revert + close (WorldQuant Alpha #28 adaptation).
    Formula: correlation(adv20, low, 5) + ((high + low) / 2) - close
    """
    adv = df['Volume'].rolling(adv_p).mean()
    corr = adv.rolling(corr_p).corr(df['Low'])
    
    # Fill NaN correlations with 0 to prevent dropping signal
    corr = corr.fillna(0)
    
    alpha = corr + ((df['High'] + df['Low']) / 2) - df['Close']
    return alpha

def calc_geom_mean_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Geometric mean - VWAP (WorldQuant Alpha #41 adaptation).
    Formula: sqrt(high * low) - vwap
    Requires VWAP in dataframe.
    """
    # Use typical price proxy if true VWAP is missing
    vwap = df.get('VWAP', (df['High'] + df['Low'] + df['Close']) / 3)
    
    geom_mean = np.sqrt(df['High'] * df['Low'])
    alpha = geom_mean - vwap
    return alpha

def calc_vol_close_anti_mom(df: pd.DataFrame, delta_p: int = 1) -> pd.Series:
    """
    Volume-close anti-momentum (WorldQuant Alpha #12 adaptation).
    Formula: sign(delta(volume, 1)) * (-1 * delta(close, 1))
    """
    vol_diff = df['Volume'].diff(delta_p)
    close_diff = df['Close'].diff(delta_p)
    
    alpha = np.sign(vol_diff) * (-1 * close_diff)
    return alpha

def calc_open_close_ratio_rank(df: pd.DataFrame, rank_p: int = 10) -> pd.Series:
    """
    Open-close ratio rank (WorldQuant Alpha #33 adaptation).
    Formula: rank(-1 * ((1 - (open / close))))
    """
    ratio = 1 - (df['Open'] / df['Close'])
    ratio = ratio.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    alpha = calc_ts_rank(-1 * ratio, rank_p)
    return alpha

def calc_close_open_ratio_mom(df: pd.DataFrame, rank_p: int = 10) -> pd.Series:
    """
    Close-open ratio momentum (WorldQuant Alpha #38 adaptation).
    Formula: ts_rank(close / open, 10)
    """
    ratio = df['Close'] / df['Open']
    ratio = ratio.replace([np.inf, -np.inf], np.nan).fillna(1.0)
    
    alpha = calc_ts_rank(ratio, rank_p)
    return alpha

def calc_ohlc_gap_ratio(df: pd.DataFrame) -> pd.Series:
    """
    OHLC gap ratio (WorldQuant Alpha #101 adaptation).
    Formula: (close - open) / (high - low + 0.001)
    """
    numerator = df['Close'] - df['Open']
    denominator = df['High'] - df['Low'] + 0.001
    
    alpha = numerator / denominator
    return alpha

def calc_return_vol_ratio(df: pd.DataFrame, short_vol_p: int = 2, long_vol_p: int = 5) -> pd.Series:
    """
    Return Vol Ratio + Close Delta (WorldQuant Alpha #34 adaptation).
    Formula: rank(stddev(returns, 2) / stddev(returns, 5)) - rank(delta(close, 1))
    """
    returns = df['Close'].pct_change()
    
    std_short = returns.rolling(short_vol_p).std()
    std_long = returns.rolling(long_vol_p).std()
    
    vol_ratio = std_short / (std_long + 1e-9)
    close_delta = df['Close'].diff(1)
    
    # We rank both across time (say 10 periods) to normalize them
    rank_vol = calc_ts_rank(vol_ratio, 10)
    rank_delta = calc_ts_rank(close_delta, 10)
    
    alpha = rank_vol - rank_delta
    return alpha

def calc_decay_linear(series: pd.Series, window: int) -> pd.Series:
    """
    WorldQuant's decay_linear function.
    Applies a linearly decaying weight to the last `window` periods.
    The most recent period gets the highest weight (window), the oldest gets weight 1.
    """
    weights = np.arange(1, window + 1)
    weights = weights / np.sum(weights)
    
    # Using np.dot with raw=True is the fastest way to apply a custom dot product filter in pandas
    return series.rolling(window).apply(lambda x: np.dot(x, weights), raw=True)


# ── 10 NEW ADVANCED ALPHA FACTORS ─────────────────────────────────────────────

def calc_fractal_variance_ratio(df: pd.DataFrame, p1: int = 5, p2: int = 20, p3: int = 60) -> pd.Series:
    """
    1. Fractal Variance Ratio Factor
    Computes multi-timeframe variance ratio as a proxy for the Hurst Exponent.
    VR > 1.0 indicates trending persistence; VR < 1.0 indicates mean reversion.
    """
    ret = df['Close'].pct_change()
    var1 = ret.rolling(p1).var()
    var2 = ret.rolling(p2).var()
    var3 = ret.rolling(p3).var()
    
    vr12 = (var2 / (p2 / p1)) / (var1 + 1e-8)
    vr23 = (var3 / (p3 / p2)) / (var2 + 1e-8)
    
    # Combined fractal persistence index normalized to [-1, 1]
    fractal_index = ((vr12 + vr23) / 2.0 - 1.0).clip(-1.0, 1.0)
    return fractal_index.fillna(0.0)


def calc_delta_decay_fade(df: pd.DataFrame, window: int = 24, decay_p: int = 12) -> pd.Series:
    """
    2. Delta Decay Fade Factor
    Applies linear decay to directional volume delta (taker volume proxy) to detect fading momentum.
    """
    bar_direction = np.sign(df['Close'] - df['Open'])
    volume_delta = bar_direction * df['Volume']
    
    decayed_delta = calc_decay_linear(volume_delta.fillna(0.0), decay_p)
    mu = decayed_delta.rolling(window).mean()
    sd = decayed_delta.rolling(window).std().replace(0, np.nan)
    
    z_score = ((decayed_delta - mu) / (sd + 1e-8)).clip(-3.0, 3.0) / 3.0
    # Fade signal: invert extreme z-score
    return (-z_score).fillna(0.0)


def calc_cusum_sharpe_breakout(df: pd.DataFrame, window: int = 48, threshold: float = 1.5) -> pd.Series:
    """
    3. CUSUM Sharpe Breakout Factor
    Calculates rolling Sharpe ratio and computes cumulative sum (CUSUM) deviations to trigger quality breakouts.
    """
    ret = df['Close'].pct_change()
    mu = ret.rolling(window).mean()
    sd = ret.rolling(window).std().replace(0, np.nan)
    sharpe = (mu / (sd + 1e-8)) * np.sqrt(365 * 24)
    
    # CUSUM filter
    sharpe_diff = sharpe.diff()
    cusum_pos = sharpe_diff.clip(lower=0).rolling(window).sum()
    cusum_neg = (-sharpe_diff.clip(upper=0)).rolling(window).sum()
    
    signal = pd.Series(0.0, index=df.index)
    signal[cusum_pos > threshold] = 1.0
    signal[cusum_neg > threshold] = -1.0
    return signal.fillna(0.0)


def calc_rank_decay_cascade(df: pd.DataFrame, short_p: int = 5, long_p: int = 20, rank_w: int = 10) -> pd.Series:
    """
    4. Rank Decay Cascade Factor
    Measures cross-timeframe rank decay of price velocity to detect structural trend exhaustion.
    """
    vel_short = df['Close'].diff(short_p)
    vel_long = df['Close'].diff(long_p)
    
    rank_s = calc_ts_rank(vel_short, rank_w)
    rank_l = calc_ts_rank(vel_long, rank_w)
    
    decay_diff = calc_decay_linear(rank_s - rank_l, rank_w)
    return decay_diff.clip(-1.0, 1.0).fillna(0.0)


def calc_funding_oi_divergence(df: pd.DataFrame, window: int = 24) -> pd.Series:
    """
    5. Sentiment Funding-OI Divergence Factor
    Combines funding rate Z-scores with Open Interest / Volume shifts to signal over-leveraged squeezes.
    Uses taker buy volume ratio & volatility when explicit OI parquet is omitted.
    """
    close_ret = df['Close'].pct_change()
    vol_z = (df['Volume'] - df['Volume'].rolling(window).mean()) / (df['Volume'].rolling(window).std() + 1e-8)
    ret_z = (close_ret - close_ret.rolling(window).mean()) / (close_ret.rolling(window).std() + 1e-8)
    
    # Divergence between return momentum and volume intensity
    divergence = (ret_z - vol_z).clip(-3.0, 3.0) / 3.0
    return divergence.fillna(0.0)


def calc_cvd_absorption_divergence(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    6. CVD Absorption & Divergence Factor
    Measures Cumulative Volume Delta vs price direction to spot passive limit order absorption.
    """
    if 'taker_buy_base_vol' in df.columns:
        taker_buy = pd.to_numeric(df['taker_buy_base_vol'], errors='coerce').fillna(df['Volume'] * 0.5)
    else:
        taker_buy = df['Volume'] * 0.5
    vol = pd.to_numeric(df['Volume'], errors='coerce').fillna(0.0)
    taker_sell = vol - taker_buy
    cvd = (taker_buy - taker_sell).cumsum()
    
    cvd_ret = cvd.pct_change(window)
    price_ret = df['Close'].pct_change(window)
    
    cvd_z = (cvd_ret - cvd_ret.rolling(window).mean()) / (cvd_ret.rolling(window).std() + 1e-8)
    price_z = (price_ret - price_ret.rolling(window).mean()) / (price_ret.rolling(window).std() + 1e-8)
    
    # Absorption: High volume delta but minimal price movement
    absorption = (cvd_z - price_z).clip(-3.0, 3.0) / 3.0
    return absorption.fillna(0.0)


def calc_fvg_mitigation_recovery(df: pd.DataFrame, gap_threshold: float = 0.005) -> pd.Series:
    """
    7. Fair Value Gap (FVG) Mitigation Recovery Factor
    Detects 3-bar Fair Value Gaps (SMC) and signals recovery / mean-reversion entries.
    """
    high_prev2 = df['High'].shift(2)
    low_curr = df['Low']
    
    low_prev2 = df['Low'].shift(2)
    high_curr = df['High']
    
    bullish_fvg = (low_curr - high_prev2) / df['Close']
    bearish_fvg = (low_prev2 - high_curr) / df['Close']
    
    signal = pd.Series(0.0, index=df.index)
    signal[bullish_fvg > gap_threshold] = 1.0
    signal[bearish_fvg > gap_threshold] = -1.0
    return signal.fillna(0.0)


def calc_hurst_regime_adaptive(df: pd.DataFrame, window: int = 100, threshold: float = 0.55) -> pd.Series:
    """
    8. Hurst Regime Adaptive Factor
    Estimates rolling Hurst exponent via log-range scaling to identify persistent trending vs mean-reverting regimes.
    """
    def _estimate_hurst(series):
        if len(series) < 20 or series.std() == 0:
            return 0.5
        rets = np.diff(series)
        z = np.cumsum(rets - np.mean(rets))
        r = np.max(z) - np.min(z)
        s = np.std(rets) + 1e-8
        rs = r / s
        n = len(rets)
        if rs <= 0 or n <= 1:
            return 0.5
        h = np.log(rs) / np.log(n)
        return float(np.clip(h, 0.0, 1.0))

    hurst_series = df['Close'].rolling(window).apply(_estimate_hurst, raw=True)
    regime = pd.Series(0.0, index=df.index)
    regime[hurst_series > threshold] = 1.0     # Persistent Trend
    regime[hurst_series < (1.0 - threshold)] = -1.0 # Mean Reverting
    return regime.fillna(0.0)


def calc_intrabar_efficiency_momentum(df: pd.DataFrame, smooth_p: int = 14, ema_p: int = 179) -> pd.Series:
    """
    9. Intrabar Efficiency Momentum Factor (Adapted from WorldQuant Alpha #101)
    Measures bar directional efficiency (Close-Open)/(High-Low) gated by long EMA trend direction.
    """
    bar_eff = (df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-8)
    smooth_eff = bar_eff.rolling(smooth_p).mean()
    ema_trend = talib.EMA(df['Close'], timeperiod=ema_p)
    
    signal = pd.Series(0.0, index=df.index)
    signal[(smooth_eff > 0.35) & (df['Close'] > ema_trend)] = 1.0
    signal[(smooth_eff < -0.35) & (df['Close'] < ema_trend)] = -1.0
    return signal.fillna(0.0)


def calc_triple_ts_rank_momentum(df: pd.DataFrame, p1: int = 5, p2: int = 15, p3: int = 30) -> pd.Series:
    """
    10. Triple TS-Rank Momentum Factor
    Combines multi-period time-series percentile ranks of price momentum to isolate strong continuation / reversal setups.
    """
    ret1 = df['Close'].pct_change(p1)
    ret2 = df['Close'].pct_change(p2)
    ret3 = df['Close'].pct_change(p3)
    
    r1 = calc_ts_rank(ret1, 20)
    r2 = calc_ts_rank(ret2, 20)
    r3 = calc_ts_rank(ret3, 20)
    
    composite_rank = (r1 + r2 + r3) / 3.0
    return composite_rank.clip(-1.0, 1.0).fillna(0.0)


# ── 2026 INSTITUTIONAL ALPHA FACTORS ──────────────────────────────────────────

def calc_wyckoff_spring_upthrust(df: pd.DataFrame, lookback: int = 72, atr_period: int = 14) -> Tuple[pd.Series, pd.Series]:
    """
    Calculates Wyckoff Spring and Upthrust factors (72-hour range break/reversal traps).
    - Spring: Price dips below rolling lookback Low and closes back above it (Bear Trap).
    - Upthrust: Price spikes above rolling lookback High and closes back below it (Bull Trap).
    Returns: (spring_score, upthrust_score) normalized by ATR.
    """
    atr = calc_atr(df, atr_period).replace(0, np.nan).ffill().fillna(1.0)
    low_roll = df['Low'].rolling(lookback, min_periods=max(12, lookback // 4)).min().shift(1).fillna(df['Low'])
    high_roll = df['High'].rolling(lookback, min_periods=max(12, lookback // 4)).max().shift(1).fillna(df['High'])
    
    spring_cond = (df['Low'] < low_roll) & (df['Close'] > low_roll)
    upthrust_cond = (df['High'] > high_roll) & (df['Close'] < high_roll)
    
    spring_val = np.where(spring_cond, (low_roll - df['Low']) / atr, 0.0)
    upthrust_val = np.where(upthrust_cond, (df['High'] - high_roll) / atr, 0.0)
    
    return pd.Series(np.clip(spring_val, 0.0, 5.0), index=df.index), pd.Series(np.clip(upthrust_val, 0.0, 5.0), index=df.index)


def calc_kaufman_efficiency_ratio(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Kaufman Efficiency Ratio (KER) measuring price path efficiency (0.0 = noise, 1.0 = direct trend).
    """
    change = (df['Close'] - df['Close'].shift(period)).abs()
    volatility = df['Close'].diff().abs().rolling(period).sum()
    ker = change / volatility.replace(0, np.nan)
    return ker.clip(0.0, 1.0).fillna(0.5)


def calc_dynamic_macro_regime_weight(df: pd.DataFrame, adx_period: int = 14, chop_period: int = 14, ema_period: int = 200) -> pd.Series:
    """
    Computes Continuous Dynamic Macro Regime Weight (G_t in [0.0, 1.0]).
    Blends ADX trend strength, Kaufman Efficiency, and Choppiness with EMA200 trend alignment.
    Returns: G_t Series in [0.0, 1.0] (1.0 = Strong Persistent Trend, 0.0 = Sideways Chop).
    """
    adx = calc_adx(df, adx_period).fillna(20.0)
    adx_score = (adx / 50.0).clip(0.0, 1.0)
    
    chop = calc_choppiness_index(df, chop_period).fillna(50.0)
    chop_score = (1.0 - (chop / 100.0)).clip(0.0, 1.0)
    
    ker = calc_kaufman_efficiency_ratio(df, chop_period).fillna(0.5)
    ker_score = ker.clip(0.0, 1.0)
    
    ema = talib.EMA(df['Close'], timeperiod=ema_period)
    trend_aligned = (df['Close'] > ema).astype(float)
    
    regime_weight = (adx_score * 0.35 + chop_score * 0.35 + ker_score * 0.30) * trend_aligned
    return pd.Series(np.clip(regime_weight.fillna(0.5), 0.0, 1.0), index=df.index)


def calc_cvd_absorption_divergence(df: pd.DataFrame, period: int = 24) -> Tuple[pd.Series, pd.Series]:
    """
    Calculates 24-hour Cumulative Volume Delta (CVD) pressure and absorption divergence.
    Returns: (cvd_buying_pressure in [-1.0, 1.0], cvd_divergence in [-1.0, 1.0]).
    """
    vol = df['Volume'].astype(float).replace(0, np.nan).fillna(1.0)
    tb_vol = df.get('taker_buy_base_volume', df.get('taker_buy_base_vol', vol * 0.5)).astype(float)
    signed_vol = 2.0 * tb_vol - vol
    
    cvd = signed_vol.rolling(period, min_periods=1).sum()
    vol_sum = vol.rolling(period, min_periods=1).sum().replace(0, 1.0)
    cvd_pressure = (cvd / vol_sum).clip(-1.0, 1.0).fillna(0.0)
    
    price_ret = df['Close'].pct_change(period).fillna(0.0)
    norm_ret = (price_ret - price_ret.rolling(period * 4, min_periods=period).mean()) / (price_ret.rolling(period * 4, min_periods=period).std() + 1e-6)
    norm_cvd = (cvd_pressure - cvd_pressure.rolling(period * 4, min_periods=period).mean()) / (cvd_pressure.rolling(period * 4, min_periods=period).std() + 1e-6)
    
    absorption_div = (norm_cvd - norm_ret).clip(-3.0, 3.0).fillna(0.0) / 3.0
    return pd.Series(cvd_pressure, index=df.index), pd.Series(absorption_div, index=df.index)


# ── 2026 VEGAS THEORY & STATISTICAL Z-SCORE FACTORS ─────────────────────────

def calc_vegas_tunnel(df: pd.DataFrame, fast_period: int = 144, slow_period: int = 169) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes classic Vegas Tunnel moving averages (Fibonacci squares: 12^2=144, 13^2=169).
    Returns: (ema_144, ema_169, vegas_midline).
    """
    ema_fast = talib.EMA(df['Close'], timeperiod=fast_period)
    ema_slow = talib.EMA(df['Close'], timeperiod=slow_period)
    vegas_mid = (ema_fast + ema_slow) / 2.0
    return ema_fast, ema_slow, vegas_mid


def calc_vegas_macro_tunnel(df: pd.DataFrame, macro_fast: int = 576, macro_slow: int = 676) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes macro Vegas Tunnel moving averages (24^2=576, 26^2=676).
    Returns: (ema_576, ema_676, macro_midline).
    """
    ema_macro_f = talib.EMA(df['Close'], timeperiod=macro_fast)
    ema_macro_s = talib.EMA(df['Close'], timeperiod=macro_slow)
    macro_mid = (ema_macro_f + ema_macro_s) / 2.0
    return ema_macro_f, ema_macro_s, macro_mid


def calc_vegas_distance_zscore(df: pd.DataFrame, fast_period: int = 144, slow_period: int = 169, z_period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    Calculates the statistical deviation (Z-score) of Price from the Vegas Tunnel midline.
    Returns: (z_distance, raw_distance).
    """
    _, _, vegas_mid = calc_vegas_tunnel(df, fast_period, slow_period)
    dist = df['Close'] - vegas_mid
    mean_dist = dist.rolling(z_period).mean()
    std_dist = dist.rolling(z_period).std()
    z_dist = (dist - mean_dist) / (std_dist + 1e-8)
    return z_dist, dist


def calc_vegas_mean_score(df: pd.DataFrame, fast_period: int = 144, slow_period: int = 169, atr_period: int = 14) -> pd.Series:
    """
    Calculates the normalized Vegas Mean Score (distance from Vegas midline divided by ATR).
    Returns: mean_score Series.
    """
    _, _, vegas_mid = calc_vegas_tunnel(df, fast_period, slow_period)
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=atr_period)
    mean_score = (df['Close'] - vegas_mid) / (atr + 1e-8)
    return mean_score


def calc_vegas_composite_signal(df: pd.DataFrame, 
                               fast_period: int = 144, 
                               slow_period: int = 169, 
                               macro_period: int = 576, 
                               filter_period: int = 12, 
                               z_period: int = 20, 
                               adx_period: int = 14, 
                               vol_ma_period: int = 20) -> Dict[str, pd.Series]:
    """
    Vectorized computation of all Vegas Theory, statistical Z-Score, and trend filters.
    Returns: Dict containing ema_12, ema_144, ema_169, ema_576, z_score, mean_score, adx, vol_ratio, atr.
    """
    ema_fast = talib.EMA(df['Close'], timeperiod=fast_period)
    ema_slow = talib.EMA(df['Close'], timeperiod=slow_period)
    vegas_mid = (ema_fast + ema_slow) / 2.0
    ema_macro = talib.EMA(df['Close'], timeperiod=macro_period)
    ema_filter = talib.EMA(df['Close'], timeperiod=filter_period)
    
    # Statistical Z-Score of distance from Vegas midline
    dist = df['Close'] - vegas_mid
    mean_dist = dist.rolling(z_period).mean()
    std_dist = dist.rolling(z_period).std()
    z_score = (dist - mean_dist) / (std_dist + 1e-8)
    
    # Normalized Mean Score (distance / ATR)
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    mean_score = dist / (atr + 1e-8)
    
    # Trend & Volume filters
    adx = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=adx_period)
    vol_sma = talib.SMA(df['Volume'], timeperiod=vol_ma_period)
    vol_ratio = df['Volume'] / (vol_sma + 1e-8)
    
    return {
        'ema_12': ema_filter,
        'ema_144': ema_fast,
        'ema_169': ema_slow,
        'vegas_mid': vegas_mid,
        'ema_576': ema_macro,
        'z_score': z_score,
        'mean_score': mean_score,
        'adx': adx,
        'vol_ratio': vol_ratio,
        'atr': atr
    }


def calc_inverse_volatility_weights(volatilities: pd.DataFrame, max_weight: float = 0.35, min_weight: float = 0.05) -> pd.DataFrame:
    """
    Calculates normalized inverse-volatility weights across assets for dynamic risk parity.
    Weight_i = (1 / vol_i) / sum(1 / vol_j), clipped to [min_weight, max_weight].
    """
    inv_vol = 1.0 / (volatilities + 1e-8)
    sum_inv = inv_vol.sum(axis=1).replace(0, np.nan)
    raw_weights = inv_vol.div(sum_inv, axis=0)
    clipped = raw_weights.clip(lower=min_weight, upper=max_weight)
    weights = clipped.div(clipped.sum(axis=1), axis=0)
    return weights.fillna(0.0)


def calc_market_breadth_score(closes: pd.DataFrame, ema_144s: pd.DataFrame) -> pd.Series:
    """
    Calculates the proportion of universe assets trading above their Vegas Tunnel 144 EMA.
    Breadth = Count(Close > EMA_144) / Total_Assets.
    Returns: Series of breadth scores in [0.0, 1.0].
    """
    above = (closes > ema_144s).astype(int)
    breadth = above.sum(axis=1) / closes.shape[1]
    return breadth


# ── 2026 CROSS-ASSET MACRO & SPOT ETF FLOW FACTORS ───────────────────────────

def calc_macro_regime_index(
    spy_df: pd.DataFrame,
    dxy_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    jpy_df: pd.DataFrame,
    spy_ma_period: int = 50,
    dxy_z_period: int = 30,
    vix_panic_threshold: float = 26.0,
    vix_spike_pct: float = 0.20,
    jpy_rapid_drop_pct: float = -0.025
) -> Tuple[pd.Series, pd.Series]:
    """
    Cross-Asset Macro Lead-Lag Regime Filter and Panic Circuit Breaker.
    Intermarket synthesis across equities, currency, volatility, and forex carry.

    1. Equity Trend (SPY > EMA 50): Global risk-on tailwind (+0.35 weight).
    2. Currency Pressure (DXY Z-Score): Weakening dollar expands global M2 liquidity (+0.25 weight).
    3. Equity Volatility (VIX): Normal volatility (<20) encourages leverage (+0.25 weight).
    4. FX Carry Stability (USD/JPY): Stable yen prevents systemic carry trade unwinds (+0.15 weight).

    Returns:
    - macro_score: pd.Series in [0.0, 1.0] (1.0 = Maximum Risk-On, 0.0 = High Risk-Off).
    - macro_veto: pd.Series of booleans (True = Acute Panic / Global Shock Veto).
    """
    spy_c = spy_df['Close'] if 'Close' in spy_df.columns else spy_df['close']
    spy_ema = talib.EMA(spy_c, timeperiod=spy_ma_period)
    spy_score = (spy_c > spy_ema).astype(float)

    dxy_c = dxy_df['Close'] if 'Close' in dxy_df.columns else dxy_df['close']
    dxy_z = (dxy_c - dxy_c.rolling(dxy_z_period).mean()) / (dxy_c.rolling(dxy_z_period).std() + 1e-8)
    dxy_score = (1.0 - (dxy_z / 2.0).clip(-1.0, 1.0)) / 2.0

    vix_c = vix_df['Close'] if 'Close' in vix_df.columns else vix_df['close']
    vix_score = (1.0 - (vix_c - 12.0) / (vix_panic_threshold - 12.0)).clip(0.0, 1.0)
    vix_3d_pct = vix_c.pct_change(18)

    jpy_c = jpy_df['Close'] if 'Close' in jpy_df.columns else jpy_df['close']
    jpy_3d_pct = jpy_c.pct_change(18)
    jpy_score = pd.Series(np.where(jpy_3d_pct < jpy_rapid_drop_pct, 0.0, 1.0), index=spy_df.index)

    macro_score = (spy_score * 0.35) + (dxy_score * 0.25) + (vix_score * 0.25) + (jpy_score * 0.15)
    macro_score = macro_score.clip(0.0, 1.0).fillna(0.50)

    # Acute Macro Shock / Panic Veto Condition
    macro_veto = (
        (vix_c >= vix_panic_threshold) |
        ((vix_3d_pct >= vix_spike_pct) & (spy_c < spy_ema)) |
        (dxy_z >= 2.2) |
        (jpy_3d_pct <= jpy_rapid_drop_pct)
    )

    return macro_score, macro_veto


def calc_etf_flow_proxy(
    ibit_df: pd.DataFrame,
    fbtc_df: pd.DataFrame,
    flow_ma_periods: int = 30,
    decel_bars: int = 18
) -> Tuple[pd.Series, pd.Series]:
    """
    Spot Bitcoin ETF Institutional Flow Momentum & Outflow Alert.
    Models institutional dollar volume and directional flow proxy across IBIT & FBTC.

    Returns:
    - etf_flow_score: pd.Series in [0.0, 1.0] (1.0 = Institutional Accumulation, 0.5 = Neutral/Pre-ETF, 0.0 = Severe Outflow).
    - etf_outflow_alert: pd.Series of booleans (True = Institutional De-risking / Outflow Wave).
    """
    ibit_c = ibit_df['Close'] if 'Close' in ibit_df.columns else ibit_df['close']
    ibit_v = ibit_df['Volume'] if 'Volume' in ibit_df.columns else ibit_df['volume']
    ibit_o = ibit_df['Open'] if 'Open' in ibit_df.columns else ibit_df['open']

    fbtc_c = fbtc_df['Close'] if 'Close' in fbtc_df.columns else fbtc_df['close']
    fbtc_v = fbtc_df['Volume'] if 'Volume' in fbtc_df.columns else fbtc_df['volume']
    fbtc_o = fbtc_df['Open'] if 'Open' in fbtc_df.columns else fbtc_df['open']

    ibit_dollar = ibit_c * ibit_v
    fbtc_dollar = fbtc_c * fbtc_v
    total_dollar = ibit_dollar + fbtc_dollar

    ibit_sign = np.sign(ibit_c - ibit_o)
    fbtc_sign = np.sign(fbtc_c - fbtc_o)
    flow_proxy = (ibit_sign * ibit_dollar) + (fbtc_sign * fbtc_dollar)

    rolling_flow = flow_proxy.rolling(flow_ma_periods).sum()
    rolling_vol = total_dollar.rolling(flow_ma_periods).sum().replace(0, np.nan)
    flow_intensity = (rolling_flow / rolling_vol).fillna(0.0).clip(-1.0, 1.0)

    # Pre-2024 ETF era flag
    is_active = total_dollar.rolling(flow_ma_periods).max() > 0

    etf_flow_score = pd.Series(0.50, index=ibit_df.index)
    etf_flow_score[is_active] = (flow_intensity[is_active] + 1.0) / 2.0

    neg_flow = (rolling_flow < 0) & is_active
    outflow_alert = ((neg_flow.rolling(decel_bars).sum() >= decel_bars) | (flow_intensity < -0.40)) & is_active

    return etf_flow_score, outflow_alert









