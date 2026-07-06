from collections import deque
from bt.core import Strategy, BarEvent

class MACDKDJStrategy(Strategy):
    def __init__(self, **params):
        super().__init__(**params)
        self.macd_fast = params.get('macd_fast', 9)
        self.macd_slow = params.get('macd_slow', 43)
        self.macd_signal = params.get('macd_signal', 9)
        self.kdj_period = params.get('kdj_period', 16)
        self.kdj_oversold = params.get('kdj_oversold', 23.0)
        self.kdj_overbought = params.get('kdj_overbought', 83.0)
        self.max_hold_bars = params.get('max_hold_bars', 73)
        self.entry_window = params.get('entry_window', 7)
        self.tp_pct = params.get('tp_pct', 0.1705)
        self.sl_pct = params.get('sl_pct', 0.0384)
        
        self.risk_per_trade = params.get('risk_per_trade', 0.2)
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

    def _calc_ema(self, val, prev, span):
        if prev is None: return val
        return (val - prev) * (2.0 / (span + 1.0)) + prev

    def _calc_smma(self, val, prev, com):
        if prev is None: return val
        return (val - prev) * (1.0 / (com + 1.0)) + prev

    def on_bar(self, bar: BarEvent):
        # 1. Manage Position
        if self.position != 0:
            self.hold_bars += 1
            exit_flag = False
            
            if self.position == 1:
                sl_price = self.entry_price * (1.0 - self.sl_pct) if self.sl_pct else None
                tp_price = self.entry_price * (1.0 + self.tp_pct) if self.tp_pct else None
                if sl_price and bar.low <= sl_price:
                    exit_flag = True
                elif tp_price and bar.high >= tp_price:
                    exit_flag = True
            else:
                sl_price = self.entry_price * (1.0 + self.sl_pct) if self.sl_pct else None
                tp_price = self.entry_price * (1.0 - self.tp_pct) if self.tp_pct else None
                if sl_price and bar.high >= sl_price:
                    exit_flag = True
                elif tp_price and bar.low <= tp_price:
                    exit_flag = True
            
            if exit_flag or (self.max_hold_bars and self.hold_bars >= self.max_hold_bars):
                self.submit_market_order(bar.symbol, 'sell' if self.position == 1 else 'buy', self.qty)
                self.position = 0
                self.hold_bars = 0
        
        # 2. Update Indicators
        self.high_q.append(bar.high)
        self.low_q.append(bar.low)
        
        self.ema_fast = self._calc_ema(bar.close, self.ema_fast, self.macd_fast)
        self.ema_slow = self._calc_ema(bar.close, self.ema_slow, self.macd_slow)
        macd_line = self.ema_fast - self.ema_slow
        self.ema_signal = self._calc_ema(macd_line, self.ema_signal, self.macd_signal)
        macd_hist = macd_line - self.ema_signal
        
        macd_turn_pos = (macd_hist > 0) and (self.prev_macd_hist is not None and self.prev_macd_hist <= 0)
        macd_turn_neg = (macd_hist < 0) and (self.prev_macd_hist is not None and self.prev_macd_hist >= 0)
        self.prev_macd_hist = macd_hist
        
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
        long_ok = any(self.k_oversold_q) and any(self.kdj_golden_q) and any(self.macd_turn_pos_q)
        short_ok = any(self.k_overbought_q) and any(self.kdj_death_q) and any(self.macd_turn_neg_q)
        
        long_edge = long_ok and not self.prev_long_ok
        short_edge = short_ok and not self.prev_short_ok
        
        self.prev_long_ok = long_ok
        self.prev_short_ok = short_ok
        
        if self.position == 0:
            if long_edge:
                self.entry_price = bar.close
                risk_usd = 10000.0 * self.risk_per_trade * self.leverage
                self.qty = risk_usd / self.entry_price
                self.submit_market_order(bar.symbol, 'buy', self.qty)
                self.position = 1
                self.hold_bars = 0
            elif short_edge:
                self.entry_price = bar.close
                risk_usd = 10000.0 * self.risk_per_trade * self.leverage
                self.qty = risk_usd / self.entry_price
                self.submit_market_order(bar.symbol, 'sell', self.qty)
                self.position = -1
                self.hold_bars = 0

    def on_stop(self):
        pass
