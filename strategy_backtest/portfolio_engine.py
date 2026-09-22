import numpy as np
import pandas as pd
from strategy_backtest.cost_calculator import CostCalculator

class _Bar:
    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        """Mirror pandas Series.get() -- see the same method on engine._Bar. The live
        engine passes strategies a real Series, so `row.get('col', default)` works there;
        without this the same strategy raises AttributeError under backtest."""
        return getattr(self, key, default)

class PortfolioBacktestEngine:
    """
    Portfolio-level bar-by-bar backtesting engine.
    Supports running multiple coins simultaneously with a shared account balance.

    Gross exposure cap: each symbol used to size its entry as risk_per_trade *
    cur_equity independently, with no awareness of what other symbols already
    had open — so several coins entering on the same bar could commit far more
    aggregate notional than a real shared cross-margin book allows (external
    replay platforms cap this, e.g. "one cross-margin book, gross exposure
    capped at 3x, <=95% equity per position"). New entries are now sized
    against remaining headroom under GROSS_EXPOSURE_CAP so simultaneous
    multi-symbol entries share one exposure budget instead of each claiming
    the same equity snapshot in full.
    """
    GROSS_EXPOSURE_CAP = 3.0   # total notional across all open positions, as a multiple of equity
    MAX_POSITION_PCT = 0.95    # single position notional cap, as a fraction of equity * leverage

    def __init__(self, dfs: dict, strategy, risk_manager, initial_balance=10_000, cost_calculator=None):
        self.strategy = strategy
        self.dfs = strategy.generate_signals()
        self.rm = risk_manager
        # BacktestEngine (single-coin) always builds its own CostCalculator so
        # every backtest gets realistic square-root market-impact slippage.
        # This engine used to leave cost_calc as None whenever the caller
        # didn't pass one — and none of run_backtest.py / scan_all.py /
        # submit_batch.py ever did — so every multi-coin portfolio backtest
        # in the system silently ran with zero slippage. Default to a real
        # CostCalculator here too, matching BacktestEngine's behavior.
        self.cost_calc = cost_calculator or CostCalculator(
            maker_fee=self.rm.trading_fee,
            taker_fee=self.rm.trading_fee,
            borrow_rate_daily=0.0003,
        )
        self.balance = float(initial_balance)
        self.equity_curve = []
        self.trades = []
        self.total_slippage = 0.0
        
        self.symbols = list(self.dfs.keys())
        
        # Align timestamps across all dfs
        all_times = None
        for df in self.dfs.values():
            if all_times is None:
                all_times = df.index
            else:
                all_times = all_times.union(df.index)
        self._times = all_times.sort_values()
        
        self._data = {}
        for sym, df in self.dfs.items():
            # Reindex to aligned times, forward fill so missing bars don't cause NaNs in prices
            df_reidx = df.reindex(self._times)
            df_reidx['Close'] = df_reidx['Close'].ffill()
            df_reidx['Open'] = df_reidx['Open'].fillna(df_reidx['Close'])
            df_reidx['High'] = df_reidx['High'].fillna(df_reidx['Close'])
            df_reidx['Low'] = df_reidx['Low'].fillna(df_reidx['Close'])
            df_reidx['Volume'] = df_reidx['Volume'].fillna(0)
            if 'signal' in df_reidx.columns:
                df_reidx['signal'] = df_reidx['signal'].fillna(0)
            else:
                df_reidx['signal'] = 0
                
            if 'funding_rate' in df_reidx.columns:
                df_reidx['funding_rate'] = df_reidx['funding_rate'].fillna(0)
                
            self._data[sym] = {col: df_reidx[col].to_numpy() for col in df_reidx.columns}
            self._data[sym]['_col_names'] = df_reidx.columns.tolist()

    def _close(self, sym, row, qty, entry_price, side, reason, exec_price=None):
        raw_price = float(exec_price) if exec_price is not None else float(row['Close'])
        
        slippage_frac = 0.0
        if self.cost_calc:
            volume = float(row.get('Volume', 1.0)) if hasattr(row, 'get') else float(getattr(row, 'Volume', 1.0))
            slippage_frac = self.cost_calc.calculate_slippage(qty, raw_price, volume)
        else:
            slippage_frac = self.rm.slippage_pct

        price = raw_price * (1.0 - slippage_frac * side)
        slippage_usd = qty * abs(price - raw_price)
        self.total_slippage += slippage_usd

        gross = qty * (price - entry_price) * side
        fee = qty * price * self.rm.trading_fee
        net = gross - fee
        self.balance += net
        self.balance = max(self.balance, 0.0)
        self.trades.append({
            'time': row.name,
            'symbol': sym,
            'type': 'EXIT_LONG' if side == 1 else 'EXIT_SHORT',
            'price': price,
            'raw_price': raw_price,
            'slippage_usd': round(slippage_usd, 4),
            'slippage_pct': slippage_frac * 100,
            'qty': round(qty, 6),
            'reason': reason,
            'fee': fee,
            'pnl': net,
            'gross_pnl': gross,
            'balance_after': self.balance,
        })
        return net

    def _total_open_notional(self, positions):
        """Aggregate notional (at cost) across every currently-open position."""
        return sum(p['long_ntl'] + p['short_ntl'] for p in positions.values())

    def _max_notional_for(self, equity_basis, positions):
        """Remaining exposure budget for a new/added position: whichever is
        tighter of the shared gross-exposure cap (headroom left in the book)
        or the single-position cap (MAX_POSITION_PCT of this position's own
        equity basis)."""
        headroom = self.GROSS_EXPOSURE_CAP * equity_basis - self._total_open_notional(positions)
        per_position_cap = self.MAX_POSITION_PCT * equity_basis * self.rm.leverage
        return max(0.0, min(headroom, per_position_cap))

    def _open(self, sym, row, side, existing_qty=0.0, existing_price=0.0, sizing_equity=None, use_open=False, max_notional=None):
        raw_price = float(row['Open'] if use_open else row['Close'])

        slippage_frac = 0.0
        if self.cost_calc:
            volume = float(row.get('Volume', 1.0)) if hasattr(row, 'get') else float(getattr(row, 'Volume', 1.0))
            # Rough estimate of slippage before qty is known for calculating margin
            slippage_frac = self.rm.slippage_pct
        else:
            slippage_frac = self.rm.slippage_pct

        size_basis = sizing_equity if sizing_equity is not None else self.balance
        # Use initial slippage estimate to calculate affordable qty
        margin, ntl, qty = self.rm.calculate_position(size_basis, raw_price * (1.0 + slippage_frac * side))

        # Scale down to fit the shared portfolio's remaining exposure headroom
        # (see GROSS_EXPOSURE_CAP) — mirrors a real cross-margin book reducing
        # an order to fit available margin rather than ignoring the cap.
        if max_notional is not None and ntl > max_notional:
            scale = max(0.0, max_notional) / ntl if ntl > 0 else 0.0
            margin *= scale
            ntl *= scale
            qty *= scale

        # Now calculate actual realistic slippage with known qty
        if self.cost_calc:
            volume = float(row.get('Volume', 1.0)) if hasattr(row, 'get') else float(getattr(row, 'Volume', 1.0))
            slippage_frac = self.cost_calc.calculate_slippage(qty, raw_price, volume)
        
        price = raw_price * (1.0 + slippage_frac * side)
        slippage_usd = qty * abs(price - raw_price)
        self.total_slippage += slippage_usd

        fee = ntl * self.rm.trading_fee
        self.balance -= fee
        
        total_qty = existing_qty + qty
        avg_price = (existing_qty * existing_price + qty * price) / total_qty if total_qty > 0 else price
        
        self.trades.append({
            'time': row.name,
            'symbol': sym,
            'type': f'BUY{"_ADD" if existing_qty > 0 else ""}' if side == 1 else f'SELL{"_ADD" if existing_qty > 0 else ""}',
            'price': price,
            'raw_price': raw_price,
            'slippage_usd': round(slippage_usd, 4),
            'slippage_pct': slippage_frac * 100,
            'qty': qty,
            'fee': fee,
            'margin': margin,
            'notional': ntl,
            'leverage': self.rm.leverage,
            'liq_price': 0,
        })
        return total_qty, avg_price, (total_qty * avg_price)

    def run(self):
        times = self._times
        n = len(times)
        
        positions = {sym: {'long_qty': 0.0, 'short_qty': 0.0, 'long_entry': 0.0, 'short_entry': 0.0, 
                           'long_ntl': 0.0, 'short_ntl': 0.0, 'long_entry_bal': 0.0, 'short_entry_bal': 0.0,
                           'closed_long_this_bar': False, 'closed_short_this_bar': False,
                           'long_skipped': False, 'short_skipped': False} 
                     for sym in self.symbols}
        
        _last_funding_key = None
        _bars = {sym: _Bar() for sym in self.symbols}

        for i in range(n):
            current_time = times[i]
            
            for sym in self.symbols:
                for col in self._data[sym]['_col_names']:
                    setattr(_bars[sym], col, self._data[sym][col][i])
                _bars[sym].name = current_time

                positions[sym]['closed_long_this_bar'] = False
                positions[sym]['closed_short_this_bar'] = False
                positions[sym]['long_skipped'] = False
                positions[sym]['short_skipped'] = False

            # 1. Check account level liquidation across portfolio
            mm = self.rm.maintenance_margin_rate
            total_intra_ntl = 0.0
            total_intra_unreal = 0.0
            
            for sym in self.symbols:
                pos = positions[sym]
                _b = _bars[sym]
                close = _b.Close
                if pos['long_qty'] > 0 or pos['short_qty'] > 0:
                    worst_l = _b.Low if pos['long_qty'] > 0 else close
                    worst_s = _b.High if pos['short_qty'] > 0 else close
                    
                    total_intra_unreal += (pos['long_qty'] * (worst_l - pos['long_entry']) if pos['long_qty'] > 0 else 0.0)
                    total_intra_unreal += (pos['short_qty'] * (pos['short_entry'] - worst_s) if pos['short_qty'] > 0 else 0.0)
                    
                    total_intra_ntl += (pos['long_qty'] * worst_l if pos['long_qty'] > 0 else 0.0)
                    total_intra_ntl += (pos['short_qty'] * worst_s if pos['short_qty'] > 0 else 0.0)
            
            intra_eq = self.balance + total_intra_unreal
            
            if total_intra_ntl > 0 and intra_eq <= total_intra_ntl * mm:
                for sym in self.symbols:
                    pos = positions[sym]
                    _b = _bars[sym]
                    if pos['long_qty'] > 0:
                        self._close(sym, _b, pos['long_qty'], pos['long_entry'], 1, 'LIQUIDATION', _b.Low)
                    if pos['short_qty'] > 0:
                        self._close(sym, _b, pos['short_qty'], pos['short_entry'], -1, 'LIQUIDATION', _b.High)
                    
                    pos['long_qty'] = pos['short_qty'] = 0.0
                    pos['long_entry'] = pos['short_entry'] = 0.0
                    pos['long_ntl'] = pos['short_ntl'] = 0.0
                
                self.equity_curve.append(self.balance)
                continue

            # 2. Manage existing positions per symbol
            for sym in self.symbols:
                pos = positions[sym]
                _b = _bars[sym]
                close = _b.Close
                reversed_short_this_bar = False
                
                if pos['long_qty'] > 0:
                    action, exec_price = self.strategy.manage_trade(sym, _b, pos['long_qty'], pos['long_entry'], pos['long_entry_bal'])
                    if action in ('SL', 'TP', 'TS', 'EXIT'):
                        if exec_price is not None and action in ('SL', 'TS'):
                            if float(_b.Open) < exec_price: exec_price = float(_b.Open)
                        self._close(sym, _b, pos['long_qty'], pos['long_entry'], 1, action, exec_price)
                        pos['long_qty'] = pos['long_entry'] = pos['long_ntl'] = pos['long_entry_bal'] = 0.0
                        pos['closed_long_this_bar'] = True
                    elif action == 'REVERSE':
                        self._close(sym, _b, pos['long_qty'], pos['long_entry'], 1, 'REVERSE', exec_price)
                        pos['long_qty'] = pos['long_entry'] = pos['long_ntl'] = pos['long_entry_bal'] = 0.0
                        pos['closed_long_this_bar'] = True
                        _eq_r = self.balance + (pos['short_qty'] * (pos['short_entry'] - close) if pos['short_qty'] > 0 else 0.0)
                        _cap = self._max_notional_for(_eq_r, positions)
                        pos['short_qty'], pos['short_entry'], pos['short_ntl'] = self._open(sym, _b, -1, pos['short_qty'], pos['short_entry'], sizing_equity=_eq_r, max_notional=_cap)
                        pos['short_entry_bal'] = self.balance
                        reversed_short_this_bar = True
                    elif action == 'ADD':
                        _ul = pos['long_qty'] * (close - pos['long_entry'])
                        _us = pos['short_qty'] * (pos['short_entry'] - close) if pos['short_qty'] > 0 else 0.0
                        _eq_add = self.balance + _ul + _us
                        _cap = self._max_notional_for(_eq_add, positions)
                        pos['long_qty'], pos['long_entry'], pos['long_ntl'] = self._open(sym, _b, 1, pos['long_qty'], pos['long_entry'], sizing_equity=_eq_add, max_notional=_cap)
                    elif action == 'SKIP':
                        pos['long_skipped'] = True

                if pos['short_qty'] > 0 and not reversed_short_this_bar:
                    action, exec_price = self.strategy.manage_trade(sym, _b, -pos['short_qty'], pos['short_entry'], pos['short_entry_bal'])
                    if action in ('SL', 'TP', 'TS', 'EXIT'):
                        if exec_price is not None and action in ('SL', 'TS'):
                            if float(_b.Open) > exec_price: exec_price = float(_b.Open)
                        self._close(sym, _b, pos['short_qty'], pos['short_entry'], -1, action, exec_price)
                        pos['short_qty'] = pos['short_entry'] = pos['short_ntl'] = pos['short_entry_bal'] = 0.0
                        pos['closed_short_this_bar'] = True
                    elif action == 'REVERSE':
                        self._close(sym, _b, pos['short_qty'], pos['short_entry'], -1, 'REVERSE', exec_price)
                        pos['short_qty'] = pos['short_entry'] = pos['short_ntl'] = pos['short_entry_bal'] = 0.0
                        pos['closed_short_this_bar'] = True
                        _eq_r = self.balance + (pos['long_qty'] * (close - pos['long_entry']) if pos['long_qty'] > 0 else 0.0)
                        _cap = self._max_notional_for(_eq_r, positions)
                        pos['long_qty'], pos['long_entry'], pos['long_ntl'] = self._open(sym, _b, 1, pos['long_qty'], pos['long_entry'], sizing_equity=_eq_r, max_notional=_cap)
                        pos['long_entry_bal'] = self.balance
                    elif action == 'ADD':
                        _ul = pos['long_qty'] * (close - pos['long_entry']) if pos['long_qty'] > 0 else 0.0
                        _us = pos['short_qty'] * (pos['short_entry'] - close)
                        _eq_add = self.balance + _ul + _us
                        _cap = self._max_notional_for(_eq_add, positions)
                        pos['short_qty'], pos['short_entry'], pos['short_ntl'] = self._open(sym, _b, -1, pos['short_qty'], pos['short_entry'], sizing_equity=_eq_add, max_notional=_cap)
                    elif action == 'SKIP':
                        pos['short_skipped'] = True

            # Calculate total portfolio equity for sizing before new entries
            total_unreal = 0.0
            for sym in self.symbols:
                p = positions[sym]
                c = _bars[sym].Close
                total_unreal += (p['long_qty'] * (c - p['long_entry']) if p['long_qty'] > 0 else 0.0)
                total_unreal += (p['short_qty'] * (p['short_entry'] - c) if p['short_qty'] > 0 else 0.0)
            
            cur_equity = self.balance + total_unreal

            # 3. Open new positions based on PREVIOUS bar's signal.
            # Recompute headroom fresh before each call — if several symbols
            # signal an entry on the same bar, each one claims from whatever
            # exposure budget the PRIOR symbols in this loop left behind,
            # instead of every symbol independently sizing off the same full
            # cur_equity snapshot.
            for sym in self.symbols:
                pos = positions[sym]
                _b = _bars[sym]
                prev_signal = int(self._data[sym]['signal'][i - 1]) if i > 0 else 0

                if (prev_signal == 1 and pos['long_qty'] == 0 and not pos['short_skipped'] and not pos['closed_long_this_bar']):
                    _cap = self._max_notional_for(cur_equity, positions)
                    if _cap > 0:
                        pos['long_qty'], pos['long_entry'], pos['long_ntl'] = self._open(sym, _b, 1, sizing_equity=cur_equity, use_open=True, max_notional=_cap)
                        pos['long_entry_bal'] = self.balance

                if (prev_signal == -1 and pos['short_qty'] == 0 and not pos['long_skipped'] and not pos['closed_short_this_bar']):
                    _cap = self._max_notional_for(cur_equity, positions)
                    if _cap > 0:
                        pos['short_qty'], pos['short_entry'], pos['short_ntl'] = self._open(sym, _b, -1, sizing_equity=cur_equity, use_open=True, max_notional=_cap)
                        pos['short_entry_bal'] = self.balance

            # Funding rate logic
            _fkey = (current_time.date(), (current_time.hour // 8) * 8)
            if _fkey != _last_funding_key:
                _last_funding_key = _fkey
                for sym in self.symbols:
                    if 'funding_rate' in self._data[sym]:
                        fr = float(self._data[sym]['funding_rate'][i])
                        pos = positions[sym]
                        close = _bars[sym].Close
                        if fr != 0.0 and (pos['long_qty'] > 0 or pos['short_qty'] > 0):
                            if pos['long_qty'] > 0:
                                self.balance -= pos['long_qty'] * close * fr
                                self.balance = max(self.balance, 0.0)
                            if pos['short_qty'] > 0:
                                self.balance += pos['short_qty'] * close * fr
                                self.balance = max(self.balance, 0.0)

            # Mark-to-market equity
            total_unreal_end = 0.0
            for sym in self.symbols:
                p = positions[sym]
                c = _bars[sym].Close
                total_unreal_end += (p['long_qty'] * (c - p['long_entry']) if p['long_qty'] > 0 else 0.0)
                total_unreal_end += (p['short_qty'] * (p['short_entry'] - c) if p['short_qty'] > 0 else 0.0)
            
            self.equity_curve.append(self.balance + total_unreal_end)

        return self.equity_curve
