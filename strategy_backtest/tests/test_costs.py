"""Tests for cost_calculator.py"""

import pytest
import numpy as np
from strategy_backtest.cost_calculator import CostCalculator


class TestCostCalculator:
    """Test cost calculation logic."""

    @pytest.fixture
    def calc(self):
        """Create a CostCalculator instance."""
        return CostCalculator(
            maker_fee=0.0002,  # 2 bps
            taker_fee=0.0004,  # 4 bps
            borrow_rate_daily=0.0003,  # 3 bps/day
        )

    def test_slippage_floor(self, calc):
        """Very small orders should hit 0.5 bps floor."""
        slippage = CostCalculator.calculate_slippage(
            qty=0.001,  # Tiny order
            price=50000,
            volume=1000000,  # Huge volume
        )
        # Min slippage is 0.5 bps = 0.000005
        assert slippage >= 0.000005

    def test_slippage_scales_with_size(self, calc):
        """Larger orders should have more slippage."""
        slippage_small = CostCalculator.calculate_slippage(
            qty=0.1,
            price=50000,
            volume=100000,
        )
        slippage_large = CostCalculator.calculate_slippage(
            qty=10,  # 100x larger
            price=50000,
            volume=100000,
        )
        # Larger order should have more slippage
        assert slippage_large > slippage_small

    def test_slippage_no_volume_uses_floor(self):
        """Zero volume should use minimum slippage."""
        slippage = CostCalculator.calculate_slippage(
            qty=1,
            price=50000,
            volume=0,  # No volume
        )
        assert slippage == 0.000005  # Should use floor

    def test_entry_cost_includes_slippage(self, calc):
        """Entry cost should include both fee and slippage."""
        cost = calc.calculate_entry_cost(
            qty=1,
            price=50000,
            volume=10000,
            is_maker=False,  # Taker fee
        )
        # Cost = fee + slippage
        # Fee = 1 × 50000 × 0.0004 = 20
        # Slippage ≈ sqrt(1/10000 × 100) × 8 / 10000 × 50000 ≈ 0.4
        assert cost > 20  # At least fee

    def test_borrow_cost_scales_with_size(self, calc):
        """Larger short positions should have higher borrow cost."""
        cost_small = calc.calculate_borrow_cost(
            qty=0.1,
            price=50000,
            num_days=1,
        )
        cost_large = calc.calculate_borrow_cost(
            qty=1,  # 10x larger
            price=50000,
            num_days=1,
        )
        assert cost_large == 10 * cost_small

    def test_borrow_cost_scales_with_time(self, calc):
        """Longer positions should have higher borrow cost."""
        cost_1day = calc.calculate_borrow_cost(
            qty=1,
            price=50000,
            num_days=1,
        )
        cost_7day = calc.calculate_borrow_cost(
            qty=1,
            price=50000,
            num_days=7,
        )
        assert cost_7day == 7 * cost_1day

    def test_borrow_cost_calculation(self, calc):
        """Verify exact borrow cost calculation."""
        # Cost = qty × price × daily_rate × num_days
        # = 1 × 50000 × 0.0003 × 1 = 15
        cost = calc.calculate_borrow_cost(
            qty=1,
            price=50000,
            num_days=1,
        )
        assert cost == pytest.approx(15.0)

    def test_funding_cost_long_pays(self, calc):
        """Longs should pay positive funding rates."""
        funding = calc.calculate_funding_cost(
            qty=1,
            price=50000,
            funding_rate=0.0001,  # 0.01% per period
            is_long=True,
        )
        # Cost = qty × price × funding_rate = 1 × 50000 × 0.0001 = 5
        assert funding == pytest.approx(5.0)

    def test_funding_cost_short_receives(self, calc):
        """Shorts should receive (negative cost) positive funding rates."""
        funding = calc.calculate_funding_cost(
            qty=1,
            price=50000,
            funding_rate=0.0001,  # 0.01% per period
            is_long=False,
        )
        # Shorts RECEIVE positive funding rates (negative cost)
        assert funding == pytest.approx(-5.0)

    def test_cost_ratio_calculation(self, calc):
        """Verify all-in cost ratio formula."""
        ratio = calc.calculate_cost_ratio(
            fees_total=100,
            slippage_total=200,
            borrow_total=50,
            funding_paid_total=10,
            gross_pnl=5000,
        )
        # Cost ratio = (100 + 200 + 50 + 10) / 5000 = 360/5000 = 0.072
        assert ratio == pytest.approx(0.072)

    def test_cost_ratio_zero_pnl(self, calc):
        """Cost ratio should be inf if gross_pnl is zero."""
        ratio = calc.calculate_cost_ratio(
            fees_total=100,
            slippage_total=200,
            borrow_total=50,
            funding_paid_total=10,
            gross_pnl=0,
        )
        assert ratio == float('inf')

    def test_cost_ratio_no_costs(self, calc):
        """Cost ratio should be zero if no costs."""
        ratio = calc.calculate_cost_ratio(
            fees_total=0,
            slippage_total=0,
            borrow_total=0,
            funding_paid_total=-100,  # Negative = received, doesn't count
            gross_pnl=5000,
        )
        assert ratio == pytest.approx(0.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
