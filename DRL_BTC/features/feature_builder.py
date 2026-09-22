"""
Feature builder — computes all Strategy Forge indicators per timeframe,
aligns 4h and 1d features to the 1h base grid via forward-fill, and saves
aligned matrices to DRL_BTC/data/features/.

Output columns are named  {indicator}_{tf}  so all 3 TFs live in one file.
All values are normalised to roughly [-1, 1] with no forward-looking data.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.config import DATA_ROOT, FEATURE_CACHE, TIMEFRAMES, BASE_TF
from DRL_BTC.features.combo_signal_builder import compute_combo_features


# ── loader ─────────────────────────────────────────────────────────────────────

def _load_ohlcv(tf: str) -> pd.DataFrame:
    path = DATA_ROOT / tf / "spot_ohlcv.parquet"
    df = pd.read_parquet(path)
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
    })
    df["taker_buy_base_vol"] = pd.to_numeric(df["taker_buy_base_vol"], errors="coerce")
    df["taker_buy_base_vol"] = df["taker_buy_base_vol"].fillna(df["Volume"] * 0.5)
    df = df.set_index("open_time").sort_index()
    df = df[["Open", "High", "Low", "Close", "Volume", "taker_buy_base_vol"]]
    return df


# ── single-TF feature computation ──────────────────────────────────────────────

def _safe(series: pd.Series, lo: float = -3.0, hi: float = 3.0) -> pd.Series:
    """Clip and return; NaN stays NaN."""
    return series.clip(lo, hi)


def compute_tf_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ~60 normalised features for one OHLCV DataFrame.
    Returned DataFrame has the same DatetimeIndex as df.
    """
    from strategy_forge.indicators import momentum, trend, volatility, volume, structure  # noqa: PLC0415
    feats: dict[str, pd.Series] = {}
    close  = df["Close"]
    atr14  = volatility.atr(df, 14).replace(0, np.nan)

    # ── TREND ──────────────────────────────────────────────────────────────────
    emas: dict[int, pd.Series] = {}
    for p in [9, 21, 50, 200]:
        e = trend.ema(df, p)
        emas[p] = e
        feats[f"ema{p}_ret"]   = _safe((close / e - 1).clip(-0.3, 0.3) / 0.3)
        feats[f"ema{p}_slope"] = _safe((e / e.shift(3) - 1).clip(-0.05, 0.05) / 0.05)

    feats["ema9_21_cross"]  = (emas[9] > emas[21]).astype(float) * 2 - 1
    feats["ema21_50_cross"] = (emas[21] > emas[50]).astype(float) * 2 - 1

    st_line, st_dir = trend.supertrend(df, 10, 3.0)
    feats["st_dir"]  = st_dir.astype(float)
    feats["st_dist"] = _safe(((close - st_line) / (close + 1e-8)).clip(-0.1, 0.1) / 0.1)

    adx_val, di_plus, di_minus = trend.adx_dmi(df, 14)
    feats["adx"]     = (adx_val / 100).clip(0, 1)
    feats["di_diff"] = ((di_plus - di_minus) / 100).clip(-1, 1)

    feats["psar_dir"]    = trend.parabolic_sar(df).astype(float)
    vi_p, vi_m           = trend.vortex(df, 14)
    feats["vortex_diff"] = (vi_p - vi_m).clip(-1, 1)

    hma_val = trend.hma(df, 20)
    feats["hma_slope"] = _safe((hma_val / hma_val.shift(3) - 1).clip(-0.05, 0.05) / 0.05)

    ich = trend.ichimoku(df, 9, 26, 52, 26)
    cloud_top = ich[["senkou_a", "senkou_b"]].max(axis=1)
    cloud_bot = ich[["senkou_a", "senkou_b"]].min(axis=1)
    ich_dir = pd.Series(0.0, index=df.index)
    ich_dir[close > cloud_top] = 1.0
    ich_dir[close < cloud_bot] = -1.0
    feats["ichimoku_dir"] = ich_dir

    # ── MOMENTUM ───────────────────────────────────────────────────────────────
    rsi14 = momentum.rsi(df, 14) / 100
    rsi7  = momentum.rsi(df, 7) / 100
    feats["rsi14"]       = rsi14.clip(0, 1)
    feats["rsi7"]        = rsi7.clip(0, 1)
    feats["rsi14_slope"] = (rsi14 - rsi14.shift(3)).clip(-0.3, 0.3)

    macd_line, macd_sig, macd_hist = momentum.macd(df, 12, 26, 9)
    feats["macd_hist"]  = _safe((macd_hist / (atr14 + 1e-8)).clip(-3, 3) / 3)
    feats["macd_above"] = (macd_line > macd_sig).astype(float) * 2 - 1

    k_kdj, d_kdj, j_kdj = momentum.kdj(df, 9)
    feats["kdj_j"] = (j_kdj / 100).clip(0, 1)

    wt1, wt2 = momentum.wavetrend(df, 10, 21)
    feats["wt1"]      = (wt1 / 100).clip(-1, 1)
    feats["wt2"]      = (wt2 / 100).clip(-1, 1)
    feats["wt_cross"] = (wt1 > wt2).astype(float) * 2 - 1

    feats["mfi"]       = (momentum.mfi(df, 14) / 100).clip(0, 1)
    feats["cci"]       = (momentum.cci(df, 14) / 200).clip(-1, 1)
    feats["williams_r"] = ((momentum.williams_r(df, 14) + 50) / 50).clip(0, 1)

    sk, sd = momentum.stoch(df, 5, 3, 3)
    feats["stoch_k"]       = (sk / 100).clip(0, 1)
    feats["stoch_d"]       = (sd / 100).clip(0, 1)
    feats["stoch_kd_cross"] = (sk > sd).astype(float) * 2 - 1

    srsi_k, srsi_d = momentum.stoch_rsi(df, 14, 14, 3, 3)
    feats["srsi_k"] = (srsi_k / 100).clip(0, 1)

    fisher_line, _ = momentum.fisher(df, 10)
    feats["fisher"] = (fisher_line / 3).clip(-1, 1)

    feats["tsi"] = (momentum.tsi(df, 13, 25) / 100).clip(-1, 1)

    aroon_up, aroon_dn = momentum.aroon(df, 14)
    feats["aroon_diff"] = ((aroon_up - aroon_dn) / 100).clip(-1, 1)

    # ── VOLATILITY ─────────────────────────────────────────────────────────────
    feats["atr_pct"] = (atr14 / (close + 1e-8)).clip(0, 0.1) / 0.1

    bb_upper, bb_mid, bb_lower = volatility.bollinger(df, 20, 2.0)
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    feats["bb_width"] = (volatility.bbw(df, 20, 2.0) / 0.3).clip(0, 1)
    feats["bb_pct"]   = ((close - bb_lower) / (bb_range + 1e-8)).clip(0, 1)

    feats["squeeze"]  = volatility.squeeze(df, 20, 2.0, 20, 1.5).astype(float)
    feats["hist_vol"] = (volatility.historical_volatility(df, 20) / 2.0).clip(0, 1)
    feats["choppiness"] = ((volatility.choppiness(df, 14) - 38.2) / (61.8 - 38.2)).clip(0, 1)

    atr_ma50 = atr14.rolling(50).mean()
    feats["atr_regime"] = ((atr14 / (atr_ma50 + 1e-8)) - 1).clip(-1, 2) / 2

    # ── VOLUME / FLOW ──────────────────────────────────────────────────────────
    vol_z = volume.volume_zscore(df, 20)
    feats["vol_z"] = _safe(vol_z.clip(-3, 3) / 3)

    tr = volume.taker_ratio(df, 20)
    feats["taker_ratio"]   = (tr - 0.5) * 2                                   # -1..+1
    tr_mu = tr.rolling(50).mean()
    tr_sd = tr.rolling(50).std().replace(0, np.nan)
    feats["taker_ratio_z"] = _safe(((tr - tr_mu) / (tr_sd + 1e-8)).clip(-3, 3) / 3)

    vwap_z_ser, _ = volume.vwap_zscore(df, 20)
    feats["vwap_z"] = _safe(vwap_z_ser.clip(-3, 3) / 3)

    cvd_ser = volume.cvd(df, 20)
    cvd_mu = cvd_ser.rolling(50).mean()
    cvd_sd = cvd_ser.rolling(50).std().replace(0, np.nan)
    feats["cvd_z"] = _safe(((cvd_ser - cvd_mu) / (cvd_sd + 1e-8)).clip(-3, 3) / 3)

    obv_ser = volume.obv(df)
    feats["obv_slope"] = (obv_ser / obv_ser.shift(10) - 1).clip(-0.5, 0.5) / 0.5

    vol_ma5  = df["Volume"].rolling(5).mean()
    vol_ma50 = df["Volume"].rolling(50).mean()
    feats["vol_regime"] = ((vol_ma5 / (vol_ma50 + 1e-8)) - 1).clip(-2, 2) / 2

    # ── STRUCTURE ──────────────────────────────────────────────────────────────
    price_z = structure.zscore(df, 20)
    feats["price_z20"] = _safe(price_z.clip(-3, 3) / 3)

    feats["vs_ema200"] = structure.price_vs_ema_pct(df, 200).clip(-0.3, 0.3) / 0.3

    bull_fvg, bear_fvg = structure.fvg(df)
    feats["fvg_bull"] = bull_fvg.astype(float)
    feats["fvg_bear"] = bear_fvg.astype(float)

    bull_imb, bear_imb = structure.imbalance_zone(df, 0.005)
    feats["imb_bull"] = bull_imb.astype(float)
    feats["imb_bear"] = bear_imb.astype(float)

    sh, sl = structure.swing_pivots(df, 20)
    feats["swing_hi"] = sh.astype(float)
    feats["swing_lo"] = sl.astype(float)

    bull_eng = structure.candle_bullish_engulfing(df).astype(float)
    bear_eng = structure.candle_bearish_engulfing(df).astype(float)
    hammer   = structure.candle_hammer(df).astype(float)
    star     = structure.candle_shooting_star(df).astype(float)
    feats["candle"] = (bull_eng * 0.5 + hammer * 0.25 - bear_eng * 0.5 - star * 0.25).clip(-1, 1)

    feats["order_block"] = structure.order_blocks(df, 14, 2.0, 3).astype(float)

    result = pd.DataFrame(feats, index=df.index)
    # Fill indicator warm-up NaNs within this TF before the caller aligns to 1h.
    # ffill first (carries last known value forward), then bfill (backfills the
    # very first bars where no forward value exists yet).
    result = result.ffill().bfill()
    return result


# ── auxiliary data features ────────────────────────────────────────────────────

def _compute_funding_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    6 funding-rate features from dataset/BTC/1h/funding_rate.parquet.
    Funding settles every 8h; the parquet already forward-fills intra-period values.
    All features normalised to ~[-1, 1].
    """
    fr_raw = pd.read_parquet(DATA_ROOT / "1h" / "funding_rate.parquet")
    fr_raw = fr_raw.set_index("open_time").sort_index()
    fr = fr_raw["funding_rate"].reindex(base_index, method="ffill").ffill().bfill()

    feats = {}

    # Raw rate normalised: typical range ±0.002
    feats["funding_raw"] = fr.clip(-0.002, 0.002) / 0.002

    # Z-score vs 20h rolling window — how extreme is current rate
    mu20 = fr.rolling(20).mean()
    sd20 = fr.rolling(20).std().replace(0, np.nan)
    feats["funding_z20"] = ((fr - mu20) / (sd20 + 1e-8)).clip(-3, 3) / 3

    # 8h momentum — is crowding increasing or decreasing
    feats["funding_mom8h"] = (fr - fr.shift(8)).clip(-0.002, 0.002) / 0.002

    # 24h smoothed level — regime-scale positioning signal
    feats["funding_ma24"] = fr.rolling(24).mean().clip(-0.002, 0.002) / 0.002

    # 8h cumulative cost — actual carry burden if long for next settlement
    feats["funding_cumsum8h"] = fr.rolling(8).sum().clip(-0.005, 0.005) / 0.005

    # 20h rolling volatility of funding — uncertainty in crowding
    feats["funding_vol20"] = (sd20 / 0.0003).clip(0, 1)

    result = pd.DataFrame(feats, index=base_index)
    return result.ffill().bfill()


def _compute_orderbook_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    8 order-book features from dataset/BTC/1h/order_book_depth.parquet.
    Data starts 2023-01-01; pre-2023 bars are filled with 0 (neutral).
    ±0.2% columns are 88% NaN and are dropped.
    Uses notional (USD value) at each price level for cross-time comparability.
    """
    ob = pd.read_parquet(DATA_ROOT / "1h" / "order_book_depth.parquet")
    ob = ob.set_index("timestamp").sort_index()

    # Drop near-touch columns (88% NaN — data was not collected at that granularity)
    ob = ob.drop(columns=[c for c in ob.columns if "0.2" in c], errors="ignore")

    # Reindex to 1h base grid; ffill fills small intra-hour gaps
    ob = ob.reindex(base_index, method="ffill")

    bid_notional = [f"notional_{-p}.0" for p in [1, 2, 3, 4, 5]]
    ask_notional = [f"notional_{p}.0"  for p in [1, 2, 3, 4, 5]]

    total_bid = ob[bid_notional].sum(axis=1)
    total_ask = ob[ask_notional].sum(axis=1)

    feats = {}

    # Bid/ask imbalance at 3 depth slices — positive = more bids than asks
    for pct in [1, 3, 5]:
        b = ob[f"notional_{-pct}.0"]
        a = ob[f"notional_{pct}.0"]
        feats[f"ob_imb_{pct}pct"] = ((b - a) / (b + a + 1e-8)).clip(-1, 1)

    # Whole-book directional bias
    feats["ob_ba_ratio"] = ((total_bid - total_ask) / (total_bid + total_ask + 1e-8)).clip(-1, 1)

    # Rolling Z-scores — is this unusually deep/thin book vs recent history?
    for side, tot in [("bid", total_bid), ("ask", total_ask)]:
        mu = tot.rolling(20).mean()
        sd = tot.rolling(20).std().replace(0, np.nan)
        feats[f"ob_{side}_z"] = ((tot - mu) / (sd + 1e-8)).clip(-3, 3) / 3

    # Book shape: is depth front-heavy (near mid) or back-heavy (far from mid)?
    bid_near = ob["notional_-1.0"] + ob["notional_-2.0"]
    bid_far  = ob["notional_-4.0"] + ob["notional_-5.0"]
    feats["ob_bid_slope"] = ((bid_near - bid_far) / (bid_near + bid_far + 1e-8)).clip(-1, 1)

    ask_near = ob["notional_1.0"] + ob["notional_2.0"]
    ask_far  = ob["notional_4.0"] + ob["notional_5.0"]
    feats["ob_ask_slope"] = ((ask_near - ask_far) / (ask_near + ask_far + 1e-8)).clip(-1, 1)

    result = pd.DataFrame(feats, index=base_index)
    # Pre-2023 rows have no order book data → fill with 0 (neutral / no signal)
    result = result.ffill().fillna(0.0)
    return result


# ── open interest features ─────────────────────────────────────────────────────

def _compute_futures_metrics_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    14 features from dataset/BTC/1h/futures_metrics.parquet (built by fetch_futures_metrics.py).
    Covers open interest, long/short ratio, top-trader positioning, and taker L/S volume.
    All normalised to ~[-1, 1]. Pre-data rows filled with 0 (neutral).

    OI signals (7):
      oi_chg_1h    — 1h OI pct change (new positions opening/closing)
      oi_chg_4h    — 4h OI pct change (medium-term position building)
      oi_z20       — OI z-score vs 20h rolling (unusual crowding)
      oi_vol_ratio — OI / volume (high = real trend, low = speculative noise)
      oi_confirm   — OI and price same direction (+1 confirm, -1 diverge)
      oi_extreme   — rolling 200h percentile rank (-1=low, +1=high)
      oi_mom       — 3h OI momentum (acceleration of position building)

    Sentiment signals (5):
      ls_ratio_z20     — long/short account ratio z-score (>0 = crowded longs)
      ls_extreme       — is market unusually long or short vs history
      top_ls_z20       — top-trader long/short ratio z-score (smart money signal)
      top_retail_div   — smart money vs retail divergence (contrarian signal)
      taker_ls_z20     — taker buy/sell volume ratio z-score

    Basis signals (3, from spot/futures price spread):
      basis_raw    — spot-futures spread normalised
      basis_z20    — basis z-score vs 20h rolling
      basis_trend  — is basis expanding or contracting
    """
    METRICS_PATH = Path(__file__).parent.parent.parent / "dataset" / "BTC" / "1h" / "futures_metrics.parquet"
    _ZERO_COLS = ["oi_chg_1h","oi_chg_4h","oi_z20","oi_vol_ratio","oi_confirm","oi_extreme","oi_mom",
                  "ls_ratio_z20","ls_extreme","top_ls_z20","top_retail_div","taker_ls_z20",
                  "basis_raw","basis_z20","basis_trend"]

    if not METRICS_PATH.exists():
        print("  [WARN] futures_metrics.parquet not found — run fetch_futures_metrics.py first")
        return pd.DataFrame(0.0, index=base_index, columns=_ZERO_COLS)

    m = pd.read_parquet(METRICS_PATH)
    m.index = pd.to_datetime(m.index)

    oi  = m["oi_usd"].reindex(base_index, method="ffill").ffill().bfill()
    ls  = m["ls_ratio"].reindex(base_index, method="ffill").ffill().bfill()
    tls = m["top_ls_ratio"].reindex(base_index, method="ffill").ffill().bfill()
    tlv = m["taker_ls_vol"].reindex(base_index, method="ffill").ffill().bfill()

    # Load 1h close and volume for OI confirmation / basis
    # Raw parquet has RangeIndex — must set open_time as index before reindexing
    ohlcv = pd.read_parquet(Path(__file__).parent.parent.parent / "dataset" / "BTC" / "1h" / "spot_ohlcv.parquet")
    ohlcv["open_time"] = pd.to_datetime(ohlcv["open_time"])
    ohlcv = ohlcv.set_index("open_time").sort_index()
    close  = pd.to_numeric(ohlcv["close"],  errors="coerce").reindex(base_index, method="ffill")
    volume = pd.to_numeric(ohlcv["volume"], errors="coerce").reindex(base_index, method="ffill")

    feats = {}

    # ── OI features ──────────────────────────────────────────────────────────
    oi_chg1 = (oi - oi.shift(1)) / (oi.shift(1) + 1e-8)
    oi_chg4 = (oi - oi.shift(4)) / (oi.shift(4) + 1e-8)
    feats["oi_chg_1h"]  = oi_chg1.clip(-0.05, 0.05) / 0.05
    feats["oi_chg_4h"]  = oi_chg4.clip(-0.10, 0.10) / 0.10

    mu20 = oi.rolling(20).mean(); sd20 = oi.rolling(20).std().replace(0, np.nan)
    feats["oi_z20"] = ((oi - mu20) / (sd20 + 1e-8)).clip(-3, 3) / 3

    oi_vol  = oi / (volume * close + 1e-8)
    ov_mu   = oi_vol.rolling(20).mean(); ov_sd = oi_vol.rolling(20).std().replace(0, np.nan)
    feats["oi_vol_ratio"] = ((oi_vol - ov_mu) / (ov_sd + 1e-8)).clip(-3, 3) / 3

    feats["oi_confirm"] = (np.sign(close.diff(1).fillna(0)) * np.sign(oi_chg1.fillna(0))).clip(-1, 1)
    feats["oi_extreme"] = oi.rolling(200, min_periods=20).rank(pct=True) * 2.0 - 1.0
    feats["oi_mom"]     = (oi_chg1 - oi_chg1.shift(3)).clip(-0.03, 0.03) / 0.03

    # ── Long/Short ratio features ─────────────────────────────────────────────
    # ls_ratio > 1 = more accounts long than short; < 1 = more short
    ls_mu20 = ls.rolling(20).mean(); ls_sd20 = ls.rolling(20).std().replace(0, np.nan)
    feats["ls_ratio_z20"] = ((ls - ls_mu20) / (ls_sd20 + 1e-8)).clip(-3, 3) / 3
    feats["ls_extreme"]   = ls.rolling(200, min_periods=20).rank(pct=True) * 2.0 - 1.0

    # ── Top trader (smart money) features ────────────────────────────────────
    tls_mu = tls.rolling(20).mean(); tls_sd = tls.rolling(20).std().replace(0, np.nan)
    feats["top_ls_z20"] = ((tls - tls_mu) / (tls_sd + 1e-8)).clip(-3, 3) / 3
    # Divergence: smart money (top traders) vs retail (all accounts)
    # Positive = smart money more bullish than retail (follow smart money)
    feats["top_retail_div"] = ((tls - ls) / (ls + 1e-8)).clip(-0.5, 0.5) / 0.5

    # ── Taker L/S volume ratio ────────────────────────────────────────────────
    tlv_mu = tlv.rolling(20).mean(); tlv_sd = tlv.rolling(20).std().replace(0, np.nan)
    feats["taker_ls_z20"] = ((tlv - tlv_mu) / (tlv_sd + 1e-8)).clip(-3, 3) / 3

    # ── Spot-futures basis ────────────────────────────────────────────────────
    spot_df   = pd.read_parquet(Path(__file__).parent.parent.parent / "dataset" / "BTC" / "spot_ohlcv.parquet")
    spot_1h   = spot_df[spot_df["interval"] == "1h"].copy()
    spot_1h["open_time"] = pd.to_datetime(spot_1h["open_time"])
    spot_1h   = spot_1h.sort_values("open_time").set_index("open_time")
    spot_close = pd.to_numeric(spot_1h["close"], errors="coerce").reindex(base_index, method="ffill").ffill().bfill()

    basis = (close - spot_close) / (spot_close + 1e-8)
    b_mu20 = basis.rolling(20).mean(); b_sd20 = basis.rolling(20).std().replace(0, np.nan)
    feats["basis_raw"]   = basis.clip(-0.005, 0.005) / 0.005
    feats["basis_z20"]   = ((basis - b_mu20) / (b_sd20 + 1e-8)).clip(-3, 3) / 3
    feats["basis_trend"] = (basis - basis.shift(8)).clip(-0.003, 0.003) / 0.003

    result = pd.DataFrame(feats, index=base_index)
    return result.ffill().fillna(0.0)


# ── on-chain features ──────────────────────────────────────────────────────────

def _compute_onchain_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    7 on-chain / cycle features.

    F&G (3 cols) — from dataset/BTC/1h/onchain_metrics.parquet (fetch_onchain_metrics.py):
      fng_raw   — Fear & Greed 0→1 (extreme fear=0, extreme greed=1)
      fng_z60   — 60-day rolling z-score of F&G
      fng_mom7  — 7-day F&G momentum

    Cycle proxy (4 cols) — computed from existing 1h OHLCV (no download needed):
      mvrv_proxy  — price / 2yr EMA  (> 2.4 historically = cycle top zone)
      mvrv_z      — 365-day rolling z-score of mvrv_proxy
      yr1_mom     — 52-week log return (bull/bear cycle position)
      ath_draw    — drawdown from rolling 4-year ATH (0=at ATH, 1=–75% down)
    """
    _ZERO_COLS = ["fng_raw", "fng_z60", "fng_mom7", "mvrv_proxy", "mvrv_z", "yr1_mom", "ath_draw"]
    ONCHAIN_PATH = Path(__file__).parent.parent.parent / "dataset" / "BTC" / "1h" / "onchain_metrics.parquet"

    feats: dict = {}

    # ── F&G from parquet ────────────────────────────────────────────────────────
    if ONCHAIN_PATH.exists():
        oc = pd.read_parquet(ONCHAIN_PATH)
        oc.index = pd.to_datetime(oc.index)   # ensure DatetimeIndex (tz-naive)
        oc = oc.reindex(base_index, method="ffill").bfill()
        feats["fng_raw"]  = oc["fng"].clip(0, 1)
        feats["fng_z60"]  = oc["fng_z60"].clip(-3, 3) / 3.0
        feats["fng_mom7"] = oc["fng_mom7"].clip(-0.5, 0.5) / 0.5
    else:
        print("  [WARN] onchain_metrics.parquet not found — run fetch_onchain_metrics.py first")
        feats["fng_raw"]  = pd.Series(0.5, index=base_index)
        feats["fng_z60"]  = pd.Series(0.0, index=base_index)
        feats["fng_mom7"] = pd.Series(0.0, index=base_index)

    # ── OHLCV-derived cycle features ────────────────────────────────────────────
    ohlcv_path = Path(__file__).parent.parent.parent / "dataset" / "BTC" / "1h" / "spot_ohlcv.parquet"
    ohlcv_raw  = pd.read_parquet(ohlcv_path, columns=["open_time", "close"])
    ohlcv_raw["open_time"] = pd.to_datetime(ohlcv_raw["open_time"])
    ohlcv_raw  = ohlcv_raw.set_index("open_time").sort_index()
    close_raw  = pd.to_numeric(ohlcv_raw["close"], errors="coerce")
    close_full = close_raw.reindex(base_index, method="ffill").ffill().bfill()

    # MVRV proxy: price / 2-year EMA (17520 hours)
    ema_2yr = close_full.ewm(span=17520, adjust=False).mean()
    mvrv_p  = (close_full / (ema_2yr + 1e-8)).clip(0.3, 5.0)
    feats["mvrv_proxy"] = ((mvrv_p - 1.0) / 4.0).clip(0, 1)   # normalise to [0,1]
    mu_m = mvrv_p.rolling(8760, min_periods=1000).mean()
    sd_m = mvrv_p.rolling(8760, min_periods=1000).std().replace(0, np.nan)
    feats["mvrv_z"] = ((mvrv_p - mu_m) / (sd_m + 1e-8)).clip(-3, 3) / 3.0

    # 1-year log momentum: positive in bull, negative in bear
    yr1 = np.log((close_full / close_full.shift(8760)).clip(0.01, 100))
    feats["yr1_mom"] = yr1.clip(-2, 2) / 2.0

    # Drawdown from rolling 4-year ATH (35040h)
    ath_4yr = close_full.rolling(35040, min_periods=500).max()
    feats["ath_draw"] = ((ath_4yr - close_full) / (ath_4yr + 1e-8)).clip(0, 1)

    result = pd.DataFrame(feats, index=base_index)
    return result.ffill().fillna(0.0)


# ── alpha library features ──────────────────────────────────────────────────────

_ALPHA_LIB_PATH = ROOT / "dataset" / "BTC" / "alpha_lib.parquet"

def _compute_alpha_lib_features(base_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    17 IC-selected features from the alpha-direction_features library.
    All pre-computed at 1h frequency, already clipped to [-1, 1].
    Covers: OI crowding, taker pressure, long liquidations, funding change,
    net-taker, MA300 alpha, coinbase premium, korea premium, market cap momentum,
    ETH cross, exchange reserve, whale outflows, on-chain contract activity,
    token transfer median, ETH2 depositors, gas limit, contract calls.
    """
    if not _ALPHA_LIB_PATH.exists():
        print(f"  [WARN] alpha_lib.parquet not found at {_ALPHA_LIB_PATH} — using zeros")
        cols = [
            "alpha_lib_oi_z24", "alpha_lib_taker_z168", "alpha_lib_liq_z168",
            "alpha_lib_fund_diff", "alpha_lib_net_taker", "alpha_lib_alpha300",
            "alpha_lib_cbx_z168", "alpha_lib_krx_z12", "alpha_lib_mcap_z12",
            "alpha_lib_eth_z12", "alpha_lib_xreserve", "alpha_lib_xout10",
            "alpha_lib_tx_ext_usd", "alpha_lib_tx_med", "alpha_lib_eth2dep",
            "alpha_lib_gas168", "alpha_lib_ccalls",
        ]
        return pd.DataFrame(0.0, index=base_index, columns=cols, dtype=np.float32)

    df = pd.read_parquet(_ALPHA_LIB_PATH)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    feats = df.reindex(base_index, method="ffill").ffill().bfill().fillna(0.0)
    return feats.astype(np.float32)


# ── composite signals ───────────────────────────────────────────────────────────

def _compute_composite_signals(wide: pd.DataFrame) -> pd.DataFrame:
    """
    4 pre-synthesised signals derived from the aligned multi-TF feature matrix.
    Appended as extra columns so the agent has explicit domain knowledge available
    alongside the raw indicator groups.  All outputs in [-1, 1].

      macro_score   — multi-TF trend alignment (EMA cross × 3 TFs, supertrend × 3 TFs,
                       funding direction); captures the big-picture directional bias
      swing_score   — 4h momentum quality (MACD histogram, RSI positioning, Aroon,
                       KDJ-J); captures medium-term setup strength
      entry_score   — 1h microstructure readiness (orderbook imbalance, taker buy
                       pressure, CVD, RSI speed); captures whether NOW is a good entry
      regime_score  — market tradeability (anti-choppiness × 2 TFs, ADX trend
                       strength, volatility normality); near −1 = chop, near +1 = trend
    """
    f = wide

    def _gc(col: str, default: float = 0.0) -> pd.Series:
        """Get column, falling back to a constant series if absent (handles pre-metrics builds)."""
        return f[col] if col in f.columns else pd.Series(default, index=f.index, dtype="float32")

    # macro_score ─────────────────────────────────────────────────────────────
    # ema9_21_cross: already +1 / −1; average across TFs in [−1, +1]
    ema_cross   = (f["ema9_21_cross_1h"] + f["ema9_21_cross_4h"] + f["ema9_21_cross_1d"]) / 3
    # st_dir: already +1 / −1
    st_align    = (f["st_dir_1h"] + f["st_dir_4h"] + f["st_dir_1d"]) / 3
    # funding_raw: normalised to [−1, 1]; deeply positive → longs pay → bearish signal
    fund_sig    = (-f["funding_raw"]).clip(-1.0, 1.0) * 0.5
    # OI confirmation: +1 = OI and price moving same direction (real trend); −1 = divergence
    oi_conf     = _gc("oi_confirm")
    # OI crowding: highly elevated OI is mean-reverting → bearish signal for position sizing
    oi_crowd    = -_gc("oi_extreme").clip(-1.0, 1.0) * 0.5   # invert: high OI → contra
    macro_score = (0.40 * ema_cross + 0.30 * st_align + 0.15 * fund_sig
                   + 0.10 * oi_conf + 0.05 * oi_crowd).clip(-1.0, 1.0)

    # swing_score ─────────────────────────────────────────────────────────────
    rsi_c       = (f["rsi14_4h"] - 0.5) * 2           # 0..1 → −1..+1 centred at 0.5
    macd        = f["macd_hist_4h"]                     # already ~[−1, 1]
    aroon       = f["aroon_diff_4h"]                    # −1..+1
    kdj_c       = (f["kdj_j_4h"] - 0.5) * 2            # 0..1 → −1..+1
    # Smart-money vs retail divergence: top traders more bullish than retail = follow
    smart_div   = _gc("top_retail_div")
    swing_score = (0.30 * macd + 0.25 * rsi_c + 0.20 * aroon
                   + 0.10 * kdj_c + 0.15 * smart_div).clip(-1.0, 1.0)

    # entry_score ─────────────────────────────────────────────────────────────
    ob_bias     = f["ob_ba_ratio"]                      # whole-book bid/ask imbalance
    taker       = f["taker_ratio_z_1h"]                 # z-scored taker buy ratio
    cvd         = f["cvd_z_1h"]                         # CVD z-score
    spd         = f["rsi14_slope_1h"].clip(-1.0, 1.0)   # RSI momentum / speed
    # Taker L/S vol z-score: aggressive buyers vs sellers (immediacy signal)
    taker_ls    = _gc("taker_ls_z20")
    entry_score = (0.25 * ob_bias + 0.25 * taker + 0.20 * cvd
                   + 0.15 * taker_ls + 0.15 * spd).clip(-1.0, 1.0)

    # regime_score ────────────────────────────────────────────────────────────
    # choppiness: 0 = pure trend, 1 = pure chop → invert
    anti_chop    = 1.0 - (f["choppiness_1h"] + f["choppiness_4h"]) / 2   # 0..1
    adx_str      = f["adx_4h"]                          # 0..1, trend strength
    vol_ok       = (1.0 - f["atr_regime_1h"].clip(0.0, 1.0))             # prefer normal vol
    # OI 4h change: sustained position building → trending regime signal
    oi_build     = _gc("oi_chg_4h").clip(-1.0, 1.0).abs()                 # high = positions building
    regime_raw   = 0.30 * anti_chop + 0.40 * adx_str + 0.15 * vol_ok + 0.15 * oi_build
    regime_score = (regime_raw * 2.0 - 1.0).clip(-1.0, 1.0)              # 0..1 → −1..+1

    sigs = pd.DataFrame({
        "macro_score":  macro_score,
        "swing_score":  swing_score,
        "entry_score":  entry_score,
        "regime_score": regime_score,
    }, index=wide.index)

    return pd.concat([wide, sigs], axis=1)


# ── multi-TF alignment ──────────────────────────────────────────────────────────

def build_aligned_features() -> pd.DataFrame:
    """
    Build a single wide DataFrame indexed on 1h timestamps.
    Columns: {feature}_{tf}  for tf in ['1h', '4h', '1d'].
    4h and 1d features are forward-filled to every 1h bar.
    Also includes funding-rate and order-book features (no tf suffix).
    """
    # Load each timeframe once; reuse the 1h DataFrame as the base index.
    tf_dfs: dict[str, pd.DataFrame] = {tf: _load_ohlcv(tf) for tf in TIMEFRAMES}
    base_df   = tf_dfs[BASE_TF]
    all_feats: list[pd.DataFrame] = []

    for tf, df_tf in tf_dfs.items():
        print(f"  Computing features for {tf}…")
        feats_tf = compute_tf_features(df_tf)

        if tf != BASE_TF:
            # Shift 1 bar forward so each 4h/1d bar is only visible AFTER it closes
            feats_tf = feats_tf.shift(1).reindex(base_df.index, method="ffill")
        else:
            feats_tf = feats_tf.reindex(base_df.index)

        feats_tf.columns = [f"{col}_{tf}" for col in feats_tf.columns]
        all_feats.append(feats_tf)

    # Auxiliary sources: funding rate, order book, futures metrics (OI+LS+basis)
    print("  Computing funding rate features…")
    all_feats.append(_compute_funding_features(base_df.index))
    print("  Computing order book features…")
    all_feats.append(_compute_orderbook_features(base_df.index))
    print("  Computing futures metrics features (OI / L/S ratio / basis)…")
    all_feats.append(_compute_futures_metrics_features(base_df.index))
    print("  Computing on-chain features (MVRV / F&G / AdrActive / NVT)…")
    all_feats.append(_compute_onchain_features(base_df.index))
    print("  Loading alpha library features (17 IC-selected signals)…")
    all_feats.append(_compute_alpha_lib_features(base_df.index))

    wide = pd.concat(all_feats, axis=1)
    # After TF alignment a small number of leading rows can still have NaN
    # (the shift(1) on 4h/1d leaves the very first 1h bar empty).
    # bfill() propagates the earliest valid value backward to cover them.
    wide = wide.bfill()

    print("  Computing composite signals (macro / swing / entry / regime)…")
    wide = _compute_composite_signals(wide)

    print("  Loading combo ensemble signals (rule-based teacher signal)…")
    combo_feats = compute_combo_features(base_df.index)
    wide = pd.concat([wide, combo_feats], axis=1)

    print("  Running BTC strategy signals (FreqAI-style position state features)…")
    from DRL_BTC.features.strategy_signal_builder import compute_strategy_features  # lazy — needs strategy_backtest
    strat_feats = compute_strategy_features(base_df.index)
    wide = pd.concat([wide, strat_feats], axis=1)

    return wide


# ── price column for env ────────────────────────────────────────────────────────

def build_full_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """
    Returns (features_df, close_series) both on the 1h index.
    features_df is the wide multi-TF feature matrix.
    close_series is the 1h close price (used by the env for PnL).
    """
    base_df = _load_ohlcv(BASE_TF)
    close   = base_df["Close"].rename("close")
    feats   = build_aligned_features()
    # Align index
    idx = feats.index.intersection(close.index)
    return feats.loc[idx], close.loc[idx]


# ── save / load cache ───────────────────────────────────────────────────────────

def save_features():
    """Precompute and cache feature matrix + close prices to parquet."""
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    print("Building multi-TF feature matrix…")
    feats, close = build_full_dataset()
    feats_path = FEATURE_CACHE / "features.parquet"
    close_path = FEATURE_CACHE / "close.parquet"
    feats.to_parquet(feats_path)
    close.to_frame().to_parquet(close_path)
    print(f"Saved {feats.shape[1]} features × {len(feats)} bars → {feats_path}")
    print(f"Saved close prices → {close_path}")
    print(f"NaN count per column:\n{feats.isnull().sum().describe()}")
    return feats, close


_COMPOSITE_COLS = {"macro_score", "swing_score", "entry_score", "regime_score"}


def load_features() -> tuple[pd.DataFrame, pd.Series]:
    """Load cached feature matrix.  Run 'python feature_builder.py' to regenerate."""
    feats_path = FEATURE_CACHE / "features.parquet"
    close_path = FEATURE_CACHE / "close.parquet"

    if not feats_path.exists():
        raise FileNotFoundError(
            f"Feature cache not found: {feats_path}\n"
            "Generate it with:  python DRL_BTC/features/feature_builder.py"
        )

    feats   = pd.read_parquet(feats_path)
    missing = _COMPOSITE_COLS - set(feats.columns)
    if missing:
        raise ValueError(
            f"Feature cache is stale — composite signal columns missing: {missing}\n"
            "Regenerate with:  python DRL_BTC/features/feature_builder.py"
        )

    close = pd.read_parquet(close_path)["close"]
    return feats, close


if __name__ == "__main__":
    print("Rebuilding feature cache (including composite signals)…")
    save_features()
    print("Done.  Restart training with: python DRL_BTC/training/train.py --seed 42")
