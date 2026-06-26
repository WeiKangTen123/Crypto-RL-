"""
Offline dataset processor — reads pre-downloaded OHLCV parquet files instead of
calling the Binance API. Produces the same output as BinanceProcessor.run() so
all downstream code (optimize_cpcv, validate, backtest, pbo) works unchanged.

Expected file layout:
    dataset/{COIN}/{TIMEFRAME}/spot_ohlcv.parquet
    e.g. dataset/BTC/4h/spot_ohlcv.parquet

Parquet columns used:
    open_time  (datetime64)  → renamed to 'timestamp', used as DataFrame index
    symbol     (str)         → renamed to 'tic'
    open, high, low, close, volume  (float)

All other parquet columns (interval, close_time, quote_asset_volume, …) are dropped.
TA-Lib indicators are computed identically to BinanceProcessor.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from talib import RSI, MACD, CCI, DX, ROC, ULTOSC, WILLR, OBV, HT_DCPHASE, ATR, BBANDS, EMA

try:
    from fracdiff.sklearn import FracdiffStat
except ImportError:
    FracdiffStat = None


class DatasetProcessor:
    def __init__(self, dataset_dir=None):
        if dataset_dir is None:
            # dataset/ lives one level above core/
            dataset_dir = Path(__file__).resolve().parent.parent / 'dataset'
        self.dataset_dir = Path(dataset_dir)
        self.correlation_threshold = 0.9
        self.tech_indicator_list = None
        self.ticker_list = None

    # ------------------------------------------------------------------
    # Public API — identical signature to BinanceProcessor.run()
    # ------------------------------------------------------------------

    def run(self, ticker_list, start_date, end_date, time_interval,
            technical_indicator_list, if_vix, feature_tickers=None):
        self.ticker_list  = ticker_list                          # coins to trade
        self.all_tickers  = ticker_list + (feature_tickers or [])  # all coins for features

        print('Reading data from local parquet files...')
        data = self._load_data(self.all_tickers, start_date, end_date, time_interval)
        print(f'Loaded {len(data)} rows. Computing TA-Lib indicators...')

        data = self._add_technical_indicator(data, technical_indicator_list)
        data = self._add_cross_asset_features(data)
        data = self._drop_correlated_features(data)

        price_array, tech_array, time_array = self._df_to_array(data, if_vix)

        # Replace NaN with 0 (warm-up period for indicators)
        tech_array = tech_array.astype(np.float64)
        tech_array[np.isnan(tech_array)] = 0

        config = {
            'price_array': price_array,
            'tech_array': tech_array,
            'ticker_list': ticker_list,
        }

        return data, price_array, tech_array, time_array, config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_data(self, ticker_list, start_date, end_date, time_interval):
        frames = []
        for ticker in ticker_list:
            # 'BTCUSDT' → 'BTC', 'ETHUSDT' → 'ETH'
            coin = ticker.upper().replace('USDT', '')
            path = self.dataset_dir / coin / time_interval / 'spot_ohlcv.parquet'

            if not path.exists():
                raise FileNotFoundError(
                    f"Parquet not found: {path}\n"
                    f"Expected layout: dataset/{coin}/{time_interval}/spot_ohlcv.parquet"
                )

            df = pd.read_parquet(path)

            # Rename to match downstream expectations
            df = df.rename(columns={'open_time': 'timestamp', 'symbol': 'tic'})

            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Date filter
            df = df[(df['timestamp'] >= pd.Timestamp(start_date)) &
                    (df['timestamp'] <= pd.Timestamp(end_date))]

            df = df.set_index('timestamp')

            # Taker buy ratio = aggressive buy pressure vs total volume
            if 'taker_buy_base_vol' in df.columns and 'volume' in df.columns:
                df['taker_buy_ratio'] = df['taker_buy_base_vol'] / (df['volume'] + 1e-8)

            # Rename useful parquet columns before dropping extras
            if 'quote_asset_volume' in df.columns:
                df = df.rename(columns={'quote_asset_volume': 'quote_vol'})

            # Drop parquet-only columns not needed downstream
            extras = ['interval', 'close_time', 'taker_buy_base_vol',
                      'taker_buy_quote_vol', 'ingested_at']
            df = df.drop(columns=[c for c in extras if c in df.columns])

            # Ensure OHLCV are numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            frames.append(df)

        return pd.concat(frames)

    def _add_technical_indicator(self, df, tech_indicator_list):
        parts = []
        for ticker in df['tic'].unique():
            coin_df = df[df['tic'] == ticker].copy()
            coin_df = self._get_talib_features(coin_df)
            parts.append(coin_df)
        return pd.concat(parts)

    def _get_talib_features(self, tic_df):
        # Momentum
        tic_df['rsi'] = RSI(tic_df['close'], timeperiod=14)
        tic_df['macd'], _, _ = MACD(tic_df['close'], fastperiod=12,
                                    slowperiod=26, signalperiod=9)
        tic_df['cci'] = CCI(tic_df['high'], tic_df['low'],
                            tic_df['close'], timeperiod=14)
        tic_df['dx'] = DX(tic_df['high'], tic_df['low'],
                          tic_df['close'], timeperiod=14)
        tic_df['roc'] = ROC(tic_df['close'], timeperiod=10)
        tic_df['ultosc'] = ULTOSC(tic_df['high'], tic_df['low'],
                                  tic_df['close'])
        tic_df['willr'] = WILLR(tic_df['high'], tic_df['low'],
                                tic_df['close'])
        # Volume
        tic_df['obv'] = OBV(tic_df['close'], tic_df['volume'])
        # Cycle
        tic_df['ht_dcphase'] = HT_DCPHASE(tic_df['close'])
        # Volatility
        tic_df['atr'] = ATR(tic_df['high'], tic_df['low'],
                            tic_df['close'], timeperiod=14)
        upper, middle, lower = BBANDS(tic_df['close'], timeperiod=20)
        tic_df['bband_width'] = (upper - lower) / (middle + 1e-8)
        # Trend
        ema_fast = EMA(tic_df['close'], timeperiod=12)
        ema_slow = EMA(tic_df['close'], timeperiod=26)
        tic_df['ema_ratio'] = ema_fast / (ema_slow + 1e-8)
        # Stationary price signal
        tic_df['log_return'] = np.log(tic_df['close'] / (tic_df['close'].shift(1) + 1e-8))
        return tic_df

    def _add_cross_asset_features(self, df):
        """BTC vs ALL-OTHERS price ratio, volume ratio and rolling return correlation."""
        if len(self.all_tickers) < 2:
            return df

        t0 = self.all_tickers[0]
        c0 = df[df['tic'] == t0]['close']
        v0 = df[df['tic'] == t0]['volume']

        for i in range(1, len(self.all_tickers)):
            t_other = self.all_tickers[i]
            coin_suffix = t_other.upper().replace('USDT', '').lower()

            c_other = df[df['tic'] == t_other]['close']
            v_other = df[df['tic'] == t_other]['volume']

            price_ratio  = (c0 / (c_other + 1e-8)).rename(f'cross_price_ratio_{coin_suffix}')
            volume_ratio = (v0 / (v_other + 1e-8)).rename(f'cross_volume_ratio_{coin_suffix}')
            corr_20      = (c0.pct_change().rolling(20).corr(c_other.pct_change())).rename(f'cross_corr_20_{coin_suffix}')

            for series in [price_ratio, volume_ratio, corr_20]:
                df[series.name] = df.index.map(series.to_dict())

        # Explicit VIX panic signal — rate of change of fear (volatility of volatility)
        vix_ticker = next((t for t in self.all_tickers if 'VIX' in t.upper()), None)
        if vix_ticker:
            vix_close = df[df['tic'] == vix_ticker]['close']
            vix_log_ret = np.log(vix_close / (vix_close.shift(1) + 1e-8)).rename('vix_log_return')
            df['vix_log_return'] = df.index.map(vix_log_ret.to_dict())

        return df

    def _drop_correlated_features(self, df):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        corr_matrix = df[numeric_cols].corr().abs()
        mask = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        upper_tri = corr_matrix.where(mask)
        auto_drop = [c for c in upper_tri.columns
                     if any(upper_tri[c] > self.correlation_threshold)]
        if 'close' in auto_drop:
            auto_drop.remove('close')
        print('Correlation analysis suggests dropping:', auto_drop)

        # Fixed drop list for model consistency (matches BinanceProcessor)
        fixed_drop = ['high', 'low', 'open', 'macd', 'cci', 'roc', 'willr']
        fixed_drop = [c for c in fixed_drop if c in df.columns]
        print('Dropping for model consistency:', fixed_drop)

        return df.drop(columns=fixed_drop)

    def _df_to_array(self, df, if_vix):
        self.tech_indicator_list = [c for c in df.columns if c != 'tic']
        print(f'Technical indicators ({len(self.tech_indicator_list)}):',
              self.tech_indicator_list)
        print(f'Trade tickers: {self.ticker_list} | Feature tickers: {[t for t in self.all_tickers if t not in self.ticker_list]}')

        # price_array — only tradeable coins (agent buys/sells these)
        first = True
        for tic in self.ticker_list:
            tic_df = df[df['tic'] == tic]
            if first:
                price_array = tic_df[['close']].values
                first = False
            else:
                price_array = np.hstack([price_array, tic_df[['close']].values])

        # tech_array — all coins (trade + feature-only) stacked as indicators
        first = True
        for tic in self.all_tickers:
            tic_df = df[df['tic'] == tic]
            if first:
                tech_array = tic_df[self.tech_indicator_list].values
                first = False
            else:
                tech_array = np.hstack([tech_array, tic_df[self.tech_indicator_list].values])

        time_array = df[df['tic'] == self.ticker_list[0]].index
        assert price_array.shape[0] == tech_array.shape[0]
        return price_array, tech_array, time_array
