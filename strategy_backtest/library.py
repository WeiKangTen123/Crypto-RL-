import pandas as pd
import numpy as np
import talib

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
