import numpy as np
from strategy_backtest.cost_calculator import CostCalculator


class _Bar:
    """
    Reusable per-bar proxy — avoids allocating a pandas Series each iteration.

    For multi-coin portfolio mode, also includes:
      - symbol: str (e.g., 'BTCUSDT') — use to key strategy state per symbol
      - Example: self._ema[bar.symbol] = new_ema

    Single-coin mode: symbol is not present (or can be ignored).
    """
    def __getitem__(self, key):
        return getattr(self, key)


class BacktestEngine:
    """
    Bar-by-bar backtesting engine — Binance Cross Margin + Hedge Mode.

    ✅ NEW (July 2026): Realistic square-root market impact slippage
       - Slippage = max(0.5 bps, 8 × √(qty/vol × 100))
       - Per-trade realistic cost modeling (no more flat 0.05%)
       - Track all costs for all-in cost ratio: fees + slippage + borrow + funding

    Entry timing:  signal fires at bar N close → fills at bar N+1 open (no look-ahead).
    TP/SL priority: each strategy's manage_trade() checks SL before TP (pessimistic).
                    If both are breached in the same bar, SL is filled first.
    Gap-through:   SL/TS gaps fill at Open (worse price — pessimistic).
                   TP gaps fill at TP price (not Open — no price improvement given).
    Liquidation:   checked against intrabar worst price (Low for longs, High for shorts).
    Same-bar re-entry after a close is blocked — must wait for bar N+1.
    REVERSE guard: a position opened via REVERSE is not managed until bar N+1.
    """

    def __init__(self, df, strategy, risk_manager, initial_balance=10_000):
        self.strategy = strategy
        self.df       = strategy.generate_signals()
        self.rm       = risk_manager
        self.balance  = float(initial_balance)
        self.equity_curve = []
        self.trades       = []

        # Pre-convert all columns to numpy for speed
        self._data     = {col: self.df[col].to_numpy() for col in self.df.columns}
        self._times    = self.df.index
        self._col_names = self.df.columns.tolist()

        # Initialize cost calculator for realistic slippage (square-root market impact)
        self.cost_calc = CostCalculator(
            maker_fee=self.rm.trading_fee,  # Usually 0.0002 (2 bps)
            taker_fee=self.rm.trading_fee,  # Usually 0.0004 (4 bps) in risk_manager
            borrow_rate_daily=0.0003        # 3 bps/day
        )
        # Track all-in costs for verdict system
        self.total_slippage = 0.0
        self.total_borrow = 0.0
        self.total_funding = 0.0

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _close(self, row, qty, entry_price, side, reason, exec_price=None):
        """Close a position. Uses exec_price if provided (e.g. exact SL/TP price),
        otherwise falls back to the bar's close price.

        Uses realistic square-root market impact slippage based on order size vs bar volume.
        """
        raw_price    = float(exec_price) if exec_price is not None else float(row['Close'])
        volume       = float(row.get('Volume', 1.0)) if hasattr(row, 'get') else float(getattr(row, 'Volume', 1.0))

        # Calculate realistic slippage: max(0.5 bps, 8 × √(qty/vol × 100))
        slippage_frac = self.cost_calc.calculate_slippage(qty, raw_price, volume)

        # Slippage is adverse: long exits fill lower, short exits fill higher
        price        = raw_price * (1.0 - slippage_frac * side)
        slippage_usd = qty * abs(price - raw_price)
        gross        = qty * (price - entry_price) * side
        fee          = qty * price * self.rm.trading_fee
        net          = gross - fee

        self.balance += net
        self.balance  = max(self.balance, 0.0)  # floor: balance cannot go negative
        self.total_slippage += slippage_usd

        self.trades.append({
            'time':          row.name,
            'type':          'EXIT_LONG' if side == 1 else 'EXIT_SHORT',
            'price':         price,
            'raw_price':     raw_price,
            'slippage_usd':  round(slippage_usd, 4),
            'slippage_pct':  slippage_frac * 100,
            'qty':           round(qty, 6),
            'reason':        reason,
            'fee':           fee,
            'pnl':           net,
            'gross_pnl':     gross,
            'balance_after': self.balance,
        })
        return net

    def _open(self, row, side, existing_qty=0.0, existing_price=0.0,
              sizing_equity=None, use_open=False):
        """Open or add to a position. Returns (new_qty, new_avg_price, new_notional).

        use_open: fill at bar Open instead of Close (used for next-bar entries so
                  the fill price matches what a live order would receive).
        sizing_equity: balance + open unrealized P&L at the moment of opening.

        Uses realistic square-root market impact slippage based on order size vs bar volume.
        """
        raw_price        = float(row['Open'] if use_open else row['Close'])
        volume           = float(row.get('Volume', 1.0)) if hasattr(row, 'get') else float(getattr(row, 'Volume', 1.0))

        size_basis       = sizing_equity if sizing_equity is not None else self.balance
        margin, ntl, qty = self.rm.calculate_position(size_basis, raw_price)

        # Calculate realistic slippage: max(0.5 bps, 8 × √(qty/vol × 100))
        slippage_frac    = self.cost_calc.calculate_slippage(qty, raw_price, volume)

        # Slippage is adverse: long entries fill higher, short entries fill lower
        price            = raw_price * (1.0 + slippage_frac * side)
        slippage_usd     = qty * abs(price - raw_price)
        fee              = ntl * self.rm.trading_fee
        self.balance    -= fee

        total_qty = existing_qty + qty
        avg_price = (existing_qty * existing_price + qty * price) / total_qty if total_qty > 0 else price

        self.total_slippage += slippage_usd

        self.trades.append({
            'time':         row.name,
            'type':         f'BUY{"_ADD" if existing_qty > 0 else ""}' if side == 1
                            else f'SELL{"_ADD" if existing_qty > 0 else ""}',
            'price':        price,
            'raw_price':    raw_price,
            'slippage_usd': round(slippage_usd, 4),
            'slippage_pct': slippage_frac * 100,
            'qty':          qty,
            'fee':          fee,
            'margin':       margin,
            'notional':     ntl,
            'leverage':     self.rm.leverage,
            'liq_price':    0,
        })
        return total_qty, avg_price, (total_qty * avg_price)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        data  = self._data
        times = self._times
        cols  = self._col_names
        n     = len(times)
        _bar  = _Bar()

        long_qty   = short_qty   = 0.0
        long_entry = short_entry = 0.0
        long_ntl   = short_ntl   = 0.0
        long_entry_bal = short_entry_bal = 0.0
        _last_funding_key = None
        _has_funding = 'funding_rate' in data

        for i in range(n):
            for col in cols:
                setattr(_bar, col, data[col][i])
            _bar.name = times[i]

            close = _bar.Close

            # Signal from the PREVIOUS bar drives entries on this bar's Open.
            # This eliminates look-ahead bias: you can only act on a closed bar's signal.
            prev_signal = int(data['signal'][i - 1]) if i > 0 else 0

            # Per-bar re-entry guard: track whether a side was closed THIS bar.
            # Prevents immediately re-entering on the same bar Open after an exit.
            closed_long_this_bar  = False
            closed_short_this_bar = False

            # ── Manage existing positions ─────────────────────────────────────
            long_skipped = False
            reversed_short_this_bar = False  # guard: new short from REVERSE must not be managed same bar
            if long_qty > 0:
                action, exec_price = self.strategy.manage_trade(
                    _bar, long_qty, long_entry, long_entry_bal)
                if action in ('SL', 'TP', 'TS', 'EXIT'):
                    # Gap-through guard (long): SL/TS fills at Open if bar gaps past stop level.
                    # TP keeps its exact price — no upside price improvement (pessimistic).
                    if exec_price is not None and action in ('SL', 'TS'):
                        if float(_bar.Open) < exec_price:
                            exec_price = float(_bar.Open)
                    self._close(_bar, long_qty, long_entry, 1, action, exec_price)
                    long_qty = long_entry = long_ntl = long_entry_bal = 0.0
                    closed_long_this_bar = True
                elif action == 'REVERSE':
                    self._close(_bar, long_qty, long_entry, 1, 'REVERSE', exec_price)
                    long_qty = long_entry = long_ntl = long_entry_bal = 0.0
                    closed_long_this_bar = True
                    _eq_r = self.balance + (short_qty * (short_entry - close) if short_qty > 0 else 0.0)
                    short_qty, short_entry, short_ntl = self._open(_bar, -1, short_qty, short_entry, sizing_equity=_eq_r)
                    short_entry_bal = self.balance
                    reversed_short_this_bar = True  # skip manage_trade for this new short this bar
                elif action == 'ADD':
                    _ul = long_qty * (close - long_entry)
                    _us = short_qty * (short_entry - close) if short_qty > 0 else 0.0
                    long_qty, long_entry, long_ntl = self._open(
                        _bar, 1, long_qty, long_entry,
                        sizing_equity=self.balance + _ul + _us)
                elif action == 'SKIP':
                    long_skipped = True

            short_skipped = False
            if short_qty > 0 and not reversed_short_this_bar:
                action, exec_price = self.strategy.manage_trade(
                    _bar, -short_qty, short_entry, short_entry_bal)
                if action in ('SL', 'TP', 'TS', 'EXIT'):
                    # Gap-through guard (short): SL/TS fills at Open if bar gaps past stop level.
                    # TP keeps its exact price — no downside price improvement (pessimistic).
                    if exec_price is not None and action in ('SL', 'TS'):
                        if float(_bar.Open) > exec_price:
                            exec_price = float(_bar.Open)
                    self._close(_bar, short_qty, short_entry, -1, action, exec_price)
                    short_qty = short_entry = short_ntl = short_entry_bal = 0.0
                    closed_short_this_bar = True
                elif action == 'REVERSE':
                    self._close(_bar, short_qty, short_entry, -1, 'REVERSE', exec_price)
                    short_qty = short_entry = short_ntl = short_entry_bal = 0.0
                    closed_short_this_bar = True
                    _eq_r = self.balance + (long_qty * (close - long_entry) if long_qty > 0 else 0.0)
                    long_qty, long_entry, long_ntl = self._open(_bar, 1, long_qty, long_entry, sizing_equity=_eq_r)
                    long_entry_bal = self.balance
                elif action == 'ADD':
                    _ul = long_qty * (close - long_entry) if long_qty > 0 else 0.0
                    _us = short_qty * (short_entry - close)
                    short_qty, short_entry, short_ntl = self._open(
                        _bar, -1, short_qty, short_entry,
                        sizing_equity=self.balance + _ul + _us)
                elif action == 'SKIP':
                    short_skipped = True

            # ── Account-level liquidation ─────────────────────────────────────
            # Check against intrabar worst price, not just bar Close, so positions
            # that touched the liquidation level intrabar are correctly liquidated.
            mm = self.rm.maintenance_margin_rate

            if long_qty > 0 or short_qty > 0:
                worst_l = _bar.Low  if long_qty  > 0 else close
                worst_s = _bar.High if short_qty > 0 else close
                intra_ul  = long_qty  * (worst_l - long_entry)  if long_qty  > 0 else 0.0
                intra_us  = short_qty * (short_entry - worst_s) if short_qty > 0 else 0.0
                intra_eq  = self.balance + intra_ul + intra_us
                intra_ntl = (long_qty * worst_l  if long_qty  > 0 else 0.0) + \
                            (short_qty * worst_s if short_qty > 0 else 0.0)

                if intra_eq <= intra_ntl * mm:
                    net_qty = long_qty - short_qty
                    if net_qty != 0:
                        numerator   = self.balance - long_qty * long_entry + short_qty * short_entry
                        denominator = (long_qty + short_qty) * mm - net_qty
                        liq_price   = (numerator / denominator) if denominator != 0 else worst_l
                        liq_price   = float(np.clip(liq_price, _bar.Low, _bar.High))
                    else:
                        liq_price = (worst_l + worst_s) / 2
                    if long_qty  > 0: self._close(_bar, long_qty,  long_entry,  1,  'LIQUIDATION', liq_price)
                    if short_qty > 0: self._close(_bar, short_qty, short_entry, -1, 'LIQUIDATION', liq_price)
                    long_qty = long_entry = long_ntl = short_qty = short_entry = short_ntl = 0.0
                    self.strategy._bars_held_long  = 0
                    self.strategy._bars_held_short = 0
                    self.strategy._exit_state      = {}
                    self.equity_curve.append(self.balance)
                    continue

            # ── Open new positions at this bar's Open ─────────────────────────
            # Entry fires from the PREVIOUS bar's signal (no look-ahead).
            # Skip if this side was just closed on this bar (no same-bar re-entry).
            _ul_now = long_qty  * (close - long_entry)  if long_qty  > 0 else 0.0
            _us_now = short_qty * (short_entry - close) if short_qty > 0 else 0.0
            _cur_equity = self.balance + _ul_now + _us_now

            if (prev_signal == 1 and long_qty == 0
                    and not short_skipped and not closed_long_this_bar):
                long_qty, long_entry, long_ntl = self._open(
                    _bar, 1, sizing_equity=_cur_equity, use_open=True)
                long_entry_bal = self.balance

            if (prev_signal == -1 and short_qty == 0
                    and not long_skipped and not closed_short_this_bar):
                short_qty, short_entry, short_ntl = self._open(
                    _bar, -1, sizing_equity=_cur_equity, use_open=True)
                short_entry_bal = self.balance

            # ── Funding rate (Binance Futures: every 8h at 00:00, 08:00, 16:00 UTC) ──
            # Deduct once per 8h period regardless of bar frequency.
            # Long pays funding_rate * notional; short receives (positive rate) or pays (negative).
            if _has_funding:
                _fkey = (times[i].date(), (times[i].hour // 8) * 8)
                if _fkey != _last_funding_key:
                    _last_funding_key = _fkey
                    fr = float(data['funding_rate'][i])
                    if fr != 0.0 and (long_qty > 0 or short_qty > 0):
                        if long_qty > 0:
                            self.balance -= long_qty * close * fr
                            self.balance  = max(self.balance, 0.0)
                        if short_qty > 0:
                            self.balance += short_qty * close * fr
                            self.balance  = max(self.balance, 0.0)

            # ── Mark-to-market equity ─────────────────────────────────────────
            unreal_l = long_qty  * (close - long_entry)  if long_qty  > 0 else 0.0
            unreal_s = short_qty * (short_entry - close) if short_qty > 0 else 0.0
            self.equity_curve.append(self.balance + unreal_l + unreal_s)

        return self.equity_curve
