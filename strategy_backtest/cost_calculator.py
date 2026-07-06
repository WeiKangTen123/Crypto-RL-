"""
cost_calculator.py — SignalHive-compliant cost calculation.

Computes all-in cost ratio using:
  - Square-root market impact slippage
  - Binance taker/maker fees (2 bps / 4 bps)
  - Short borrow cost (3 bps/day)
  - Funding cost (every 8h)

Cost Ratio = (fees + slippage + borrow + funding_paid) / gross_pnl
"""

import numpy as np


class CostCalculator:
    """
    All-in cost calculation for crypto derivatives trading.

    References:
      - Binance Futures fees: https://www.binance.com/en/support/faq/360033544231
      - Slippage model: max(0.5 bps, 8 × √(qty/vol × 100))
      - Funding: every 8h, accrued per bar for simplicity
    """

    MAKER_FEE = 0.0002  # 2 bps
    TAKER_FEE = 0.0004  # 4 bps
    BORROW_RATE_DAILY = 0.0003  # 3 bps/day
    MIN_SLIPPAGE = 0.000005  # 0.5 bps floor

    def __init__(self, maker_fee=None, taker_fee=None, borrow_rate_daily=None):
        """
        Args:
            maker_fee: fraction (default 0.0002 = 2 bps)
            taker_fee: fraction (default 0.0004 = 4 bps)
            borrow_rate_daily: fraction (default 0.0003 = 3 bps/day)
        """
        self.maker_fee = maker_fee if maker_fee is not None else self.MAKER_FEE
        self.taker_fee = taker_fee if taker_fee is not None else self.TAKER_FEE
        self.borrow_rate_daily = borrow_rate_daily if borrow_rate_daily is not None else self.BORROW_RATE_DAILY

    @staticmethod
    def calculate_slippage(qty, price, volume):
        """
        Market impact slippage: max(0.5 bps, 8 × √(qty/vol × 100))

        Args:
            qty: position size (units of asset)
            price: entry/exit price
            volume: bar volume (units of asset)

        Returns:
            slippage as fraction (e.g., 0.0001 = 10 bps)
        """
        if volume <= 0:
            # If no volume data, fall back to 0.5 bps
            return CostCalculator.MIN_SLIPPAGE

        notional = qty * price
        ratio = (notional / volume) * 100 if volume > 0 else 0
        sqrt_ratio = np.sqrt(max(ratio, 0))
        slippage = 8 * sqrt_ratio / 10000  # Convert bps to fraction
        return max(CostCalculator.MIN_SLIPPAGE, slippage)

    def calculate_entry_cost(self, qty, price, volume, is_maker=False):
        """
        Cost of opening a position: fee + slippage

        Args:
            qty: position size
            price: entry price
            volume: bar volume
            is_maker: True if limit order (maker), False if market (taker)

        Returns:
            cost_usd
        """
        notional = qty * price
        fee = notional * (self.maker_fee if is_maker else self.taker_fee)
        slippage = self.calculate_slippage(qty, price, volume) * notional
        return fee + slippage

    def calculate_exit_cost(self, qty, price, volume, is_maker=False):
        """
        Cost of closing a position: fee + slippage

        Args:
            qty: position size
            price: exit price
            volume: bar volume
            is_maker: True if limit order, False if market

        Returns:
            cost_usd
        """
        return self.calculate_entry_cost(qty, price, volume, is_maker)

    def calculate_borrow_cost(self, qty, price, num_days):
        """
        Short borrow cost: 3 bps/day × notional × days

        Args:
            qty: position size
            price: mark price at entry
            num_days: fractional days held

        Returns:
            borrow_cost_usd
        """
        notional = qty * price
        return notional * self.borrow_rate_daily * num_days

    def calculate_funding_cost(self, qty, price, funding_rate, is_long=True):
        """
        Funding payment: notional × funding_rate per 8h period

        Args:
            qty: position size
            price: mark price
            funding_rate: per-period rate (e.g., 0.0001 = 0.01%)
            is_long: True if long position

        Returns:
            funding_paid_usd (positive = paid, negative = received)
        """
        notional = qty * price
        if is_long:
            # Long pays positive funding_rate
            return notional * funding_rate
        else:
            # Short receives positive funding_rate (or pays if negative)
            return -notional * funding_rate

    def calculate_cost_ratio(self, fees_total, slippage_total, borrow_total,
                            funding_paid_total, gross_pnl):
        """
        All-in cost ratio for T1-10 gate.

        cost_ratio = (fees + slippage + borrow + funding_paid) / gross_pnl

        Args:
            fees_total: total maker + taker fees paid
            slippage_total: total slippage cost
            borrow_total: total short borrow cost
            funding_paid_total: total funding paid (net of received)
            gross_pnl: sum of winning trades PnL (before fees/slippage)

        Returns:
            cost_ratio as fraction (e.g., 0.15 = 15%)
        """
        total_costs = fees_total + slippage_total + borrow_total + max(funding_paid_total, 0)
        if gross_pnl <= 0:
            return float('inf') if total_costs > 0 else 0.0
        return total_costs / gross_pnl
