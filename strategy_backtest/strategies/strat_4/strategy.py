from collections import deque
from bt.core import Strategy, BarEvent

class MTF_MACDKDJ_ADX_ATR_Strategy(Strategy):
    def __init__(self, **params):
        super().__init__(**params)
        self.macd_fast = params.get('macd_fast', 5)
        self.macd_slow = params.get('macd_slow', 63)
        self.macd_signal = params.get('macd_signal', 19)
        self.kdj_period = params.get('kdj_period', 25)
        self.kdj_oversold = params.get('kdj_oversold', 12.0)
        self.kdj_overbought = params.get('kdj_overbought', 76.0)
        self.entry_window = params.get('entry_window', 19)
        self.adx_threshold_1h = params.get('adx_threshold_1h', 17.4943)
        self.adx_threshold_4h = params.get('adx_threshold_4h', 18.5091)
        self.ema_trend_4h = params.get('ema_trend_4h', 97)
        self.atr_multiplier_sl = params.get('atr_multiplier_sl', 0.5639)
        self.atr_multiplier_tp = params.get('atr_multiplier_tp', 5.6043)
        self.exit_mode = params.get('exit_mode', "FIXED_RR")
        
        self.risk_per_trade = params.get('risk_per_trade', 0.1)
        self.leverage = params.get('leverage', 10)
        
        self._reset()

    def _reset(self):
        self.ema_fast = None
        self.ema_slow = None
        self.ema_signal = None
        self.prev_macd_hist = None
        
        self.high_q = deque(maxlen=self.kdj_period)
        self.low_q = deque(maxlen=self.kdj_period)
        self.prev_k = None
        self.prev_d = None
        
        self.k_oversold_q = deque(maxlen=self.entry_window)
        self.k_overbought_q = deque(maxlen=self.entry_window)
        self.kdj_golden_q = deque(maxlen=self.entry_window)
        self.kdj_death_q = deque(maxlen=self.entry_window)
        self.macd_turn_pos_q = deque(maxlen=self.entry_window)
        self.macd_turn_neg_q = deque(maxlen=self.entry_window)
        
        self.prev_long_ok = False
        self.prev_short_ok = False
        
        self.position = 0
        self.entry_price = 0.0
        self.hold_bars = 0
        self.qty = 0.0
        
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.ts_price = 0.0
        
        self.adx_1h_prev_high = None
        self.adx_1h_prev_low = None
        self.adx_1h_prev_close = None
        self.adx_1h_smoothed_tr = None
        self.adx_1h_smoothed_pdm = None
        self.adx_1h_smoothed_ndm = None
        self.adx_1h_smoothed_dx = None
        self.adx_1h_val = 0.0
        
        self.atr_1h_prev_close = None
        self.atr_1h_val = 0.0
        
        self.bar_count = 0
        self.h4_open = None
        self.h4_high = None
        self.h4_low = None
        
        self.ema_4h = None
        self.adx_4h_prev_high = None
        self.adx_4h_prev_low = None
        self.adx_4h_prev_close = None
        self.adx_4h_smoothed_tr = None
        self.adx_4h_smoothed_pdm = None
        self.adx_4h_smoothed_ndm = None
        self.adx_4h_smoothed_dx = None
        self.adx_4h_val = 0.0

    def _calc_ema(self, val, prev, span):
        if prev is None: return val
        return (val - prev) * (2.0 / (span + 1.0)) + prev

    def _calc_smma(self, val, prev, com):
        if prev is None: return val
        return (val - prev) * (1.0 / (com + 1.0)) + prev

    def _update_adx_1h(self, high, low, close):
        if self.adx_1h_prev_close is None:
            self.adx_1h_prev_high = high
            self.adx_1h_prev_low = low
            self.adx_1h_prev_close = close
            return 0.0
        tr = max(high - low, abs(high - self.adx_1h_prev_close), abs(low - self.adx_1h_prev_close))
        up_move = high - self.adx_1h_prev_high
        down_move = self.adx_1h_prev_low - low
        pdm = up_move if up_move > down_move and up_move > 0 else 0.0
        ndm = down_move if down_move > up_move and down_move > 0 else 0.0
        alpha = 1.0 / 14
        if self.adx_1h_smoothed_tr is None:
            self.adx_1h_smoothed_tr = tr
            self.adx_1h_smoothed_pdm = pdm
            self.adx_1h_smoothed_ndm = ndm
        else:
            self.adx_1h_smoothed_tr = (tr - self.adx_1h_smoothed_tr) * alpha + self.adx_1h_smoothed_tr
            self.adx_1h_smoothed_pdm = (pdm - self.adx_1h_smoothed_pdm) * alpha + self.adx_1h_smoothed_pdm
            self.adx_1h_smoothed_ndm = (ndm - self.adx_1h_smoothed_ndm) * alpha + self.adx_1h_smoothed_ndm
        pdi = 100.0 * self.adx_1h_smoothed_pdm / self.adx_1h_smoothed_tr if self.adx_1h_smoothed_tr > 0 else 0.0
        ndi = 100.0 * self.adx_1h_smoothed_ndm / self.adx_1h_smoothed_tr if self.adx_1h_smoothed_tr > 0 else 0.0
        dx = 100.0 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) > 0 else 0.0
        if self.adx_1h_smoothed_dx is None:
            self.adx_1h_smoothed_dx = dx
        else:
            self.adx_1h_smoothed_dx = (dx - self.adx_1h_smoothed_dx) * alpha + self.adx_1h_smoothed_dx
        self.adx_1h_val = self.adx_1h_smoothed_dx
        self.adx_1h_prev_high = high
        self.adx_1h_prev_low = low
        self.adx_1h_prev_close = close

    def _update_adx_4h(self, high, low, close):
        if self.adx_4h_prev_close is None:
            self.adx_4h_prev_high = high
            self.adx_4h_prev_low = low
            self.adx_4h_prev_close = close
            return 0.0
        tr = max(high - low, abs(high - self.adx_4h_prev_close), abs(low - self.adx_4h_prev_close))
        up_move = high - self.adx_4h_prev_high
        down_move = self.adx_4h_prev_low - low
        pdm = up_move if up_move > down_move and up_move > 0 else 0.0
        ndm = down_move if down_move > up_move and down_move > 0 else 0.0
        alpha = 1.0 / 14
        if self.adx_4h_smoothed_tr is None:
            self.adx_4h_smoothed_tr = tr
            self.adx_4h_smoothed_pdm = pdm
            self.adx_4h_smoothed_ndm = ndm
        else:
            self.adx_4h_smoothed_tr = (tr - self.adx_4h_smoothed_tr) * alpha + self.adx_4h_smoothed_tr
            self.adx_4h_smoothed_pdm = (pdm - self.adx_4h_smoothed_pdm) * alpha + self.adx_4h_smoothed_pdm
            self.adx_4h_smoothed_ndm = (ndm - self.adx_4h_smoothed_ndm) * alpha + self.adx_4h_smoothed_ndm
        pdi = 100.0 * self.adx_4h_smoothed_pdm / self.adx_4h_smoothed_tr if self.adx_4h_smoothed_tr > 0 else 0.0
        ndi = 100.0 * self.adx_4h_smoothed_ndm / self.adx_4h_smoothed_tr if self.adx_4h_smoothed_tr > 0 else 0.0
        dx = 100.0 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) > 0 else 0.0
        if self.adx_4h_smoothed_dx is None:
            self.adx_4h_smoothed_dx = dx
        else:
            self.adx_4h_smoothed_dx = (dx - self.adx_4h_smoothed_dx) * alpha + self.adx_4h_smoothed_dx
        self.adx_4h_val = self.adx_4h_smoothed_dx
        self.adx_4h_prev_high = high
        self.adx_4h_prev_low = low
        self.adx_4h_prev_close = close

    def _update_atr_1h(self, high, low, close):
        if self.atr_1h_prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.atr_1h_prev_close), abs(low - self.atr_1h_prev_close))
        if self.atr_1h_prev_close is None:
            self.atr_1h_val = tr
        else:
            self.atr_1h_val = (tr - self.atr_1h_val) * (1.0 / 14) + self.atr_1h_val
        self.atr_1h_prev_close = close

    def on_bar(self, bar: BarEvent):
        # 1. Manage Position
        if self.position != 0:
            self.hold_bars += 1
            exit_flag = False
            
            if self.exit_mode == 'FIXED_RR':
                if self.position == 1:
                    if bar.low <= self.sl_price: exit_flag = True
                    elif bar.high >= self.tp_price: exit_flag = True
                else:
                    if bar.high >= self.sl_price: exit_flag = True
                    elif bar.low <= self.tp_price: exit_flag = True
            elif self.exit_mode == 'TRAILING_STOP':
                if self.position == 1:
                    if bar.low <= self.sl_price:
                        exit_flag = True
                    else:
                        new_ts = bar.high - self.atr_multiplier_sl * self.atr_1h_val
                        if new_ts > self.ts_price: self.ts_price = new_ts
                        if bar.low <= self.ts_price: exit_flag = True
                else:
                    if bar.high >= self.sl_price:
                        exit_flag = True
                    else:
                        new_ts = bar.low + self.atr_multiplier_sl * self.atr_1h_val
                        if new_ts < self.ts_price: self.ts_price = new_ts
                        if bar.high >= self.ts_price: exit_flag = True
                        
            if exit_flag:
                self.submit_market_order(bar.symbol, 'sell' if self.position == 1 else 'buy', self.qty)
                self.position = 0
                self.hold_bars = 0
                
        # 2. Update Indicators
        # 1h MACD
        self.ema_fast = self._calc_ema(bar.close, self.ema_fast, self.macd_fast)
        self.ema_slow = self._calc_ema(bar.close, self.ema_slow, self.macd_slow)
        macd_line = self.ema_fast - self.ema_slow
        self.ema_signal = self._calc_ema(macd_line, self.ema_signal, self.macd_signal)
        macd_hist = macd_line - self.ema_signal
        
        macd_turn_pos = (macd_hist > 0) and (self.prev_macd_hist is not None and self.prev_macd_hist <= 0)
        macd_turn_neg = (macd_hist < 0) and (self.prev_macd_hist is not None and self.prev_macd_hist >= 0)
        self.prev_macd_hist = macd_hist
        
        # 1h KDJ
        self.high_q.append(bar.high)
        self.low_q.append(bar.low)
        kdj_golden = False
        kdj_death = False
        k = 50.0
        
        if len(self.high_q) > 0:
            hh = max(self.high_q)
            ll = min(self.low_q)
            rsv = (bar.close - ll) / (hh - ll + 1e-8) * 100.0
            k = self._calc_smma(rsv, self.prev_k if self.prev_k is not None else rsv, 2)
            d = self._calc_smma(k, self.prev_d if self.prev_d is not None else k, 2)
            if self.prev_k is not None and self.prev_d is not None:
                kdj_golden = (k > d) and (self.prev_k <= self.prev_d)
                kdj_death = (k < d) and (self.prev_k >= self.prev_d)
            self.prev_k = k
            self.prev_d = d
            
        self.k_oversold_q.append(k < self.kdj_oversold)
        self.k_overbought_q.append(k > self.kdj_overbought)
        self.kdj_golden_q.append(kdj_golden)
        self.kdj_death_q.append(kdj_death)
        self.macd_turn_pos_q.append(macd_turn_pos)
        self.macd_turn_neg_q.append(macd_turn_neg)
        
        # 1h ADX & ATR
        self._update_adx_1h(bar.high, bar.low, bar.close)
        self._update_atr_1h(bar.high, bar.low, bar.close)
        
        # 4h Simulation
        if self.bar_count % 4 == 0:
            self.h4_open = bar.open
            self.h4_high = bar.high
            self.h4_low = bar.low
        else:
            self.h4_high = max(self.h4_high, bar.high)
            self.h4_low = min(self.h4_low, bar.low)
            
        # Update 4h indicators at the end of the 4h block
        if self.bar_count % 4 == 3:
            h4_close = bar.close
            self.ema_4h = self._calc_ema(h4_close, self.ema_4h, self.ema_trend_4h)
            self._update_adx_4h(self.h4_high, self.h4_low, h4_close)
            
        self.bar_count += 1
        
        # 3. KDJ Exit Check
        if self.position == 1 and kdj_death:
            self.submit_market_order(bar.symbol, 'sell', self.qty)
            self.position = 0
            self.hold_bars = 0
        elif self.position == -1 and kdj_golden:
            self.submit_market_order(bar.symbol, 'buy', self.qty)
            self.position = 0
            self.hold_bars = 0
            
        # 4. Entry Check
        trend_up = False
        trend_down = False
        if self.ema_4h is not None:
            trend_up = bar.close > self.ema_4h
            trend_down = bar.close < self.ema_4h
            
        adx_1h_strong = self.adx_1h_val > self.adx_threshold_1h
        adx_4h_strong = self.adx_4h_val > self.adx_threshold_4h
        
        long_ok = any(self.k_oversold_q) and any(self.kdj_golden_q) and any(self.macd_turn_pos_q) and trend_up and adx_4h_strong and adx_1h_strong
        short_ok = any(self.k_overbought_q) and any(self.kdj_death_q) and any(self.macd_turn_neg_q) and trend_down and adx_4h_strong and adx_1h_strong
        
        long_edge = long_ok and not self.prev_long_ok
        short_edge = short_ok and not self.prev_short_ok
        
        self.prev_long_ok = long_ok
        self.prev_short_ok = short_ok
        
        if self.position == 0:
            if long_edge:
                self.entry_price = bar.close
                self.sl_price = self.entry_price - self.atr_multiplier_sl * self.atr_1h_val
                self.tp_price = self.entry_price + self.atr_multiplier_tp * self.atr_1h_val
                self.ts_price = self.sl_price
                risk_usd = 10000.0 * self.risk_per_trade * self.leverage
                self.qty = risk_usd / self.entry_price
                self.submit_market_order(bar.symbol, 'buy', self.qty)
                self.position = 1
                self.hold_bars = 0
            elif short_edge:
                self.entry_price = bar.close
                self.sl_price = self.entry_price + self.atr_multiplier_sl * self.atr_1h_val
                self.tp_price = self.entry_price - self.atr_multiplier_tp * self.atr_1h_val
                self.ts_price = self.sl_price
                risk_usd = 10000.0 * self.risk_per_trade * self.leverage
                self.qty = risk_usd / self.entry_price
                self.submit_market_order(bar.symbol, 'sell', self.qty)
                self.position = -1
                self.hold_bars = 0

    def on_stop(self):
        pass
