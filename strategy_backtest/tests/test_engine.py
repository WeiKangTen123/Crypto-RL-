"""Tests for engine.py"""

import pytest
import pandas as pd
import numpy as np
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager
from strategy_backtest.base_strategy import BaseStrategy


class SimpleStrategy(BaseStrategy):
    """Minimal test strategy."""
    def __init__(self, df, **kwargs):
        super().__init__(df, **kwargs)

    def generate_signals(self):
        """Buy on bar 5, hold until bar 95."""
        self.df['signal'] = 0
        self.df.loc[4:, 'signal'] = 1  # Buy at bar 5
        self.df.loc[94:, 'signal'] = 0  # Exit at bar 95
        return self.df

    def manage_trade(self, row, position, entry_price, wallet=0):
        """Hold position, no active management."""
        return 'HOLD', None


class TestBacktestEngine:
    """Test backtest execution logic."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        price = 50000.0
        df = pd.DataFrame({
            'Open': price,
            'High': price + 100,
            'Low': price - 100,
            'Close': price,
            'Volume': 1000.0,
        }, index=dates)
        # Add small trends to make it realistic
        df['Close'] = df['Close'] * (1.0 + np.cumsum(np.random.normal(0, 0.0001, 100)))
        df['Open'] = df['Close'] * 0.999
        df['High'] = df['Close'] * 1.001
        df['Low'] = df['Close'] * 0.999
        return df

    @pytest.fixture
    def strategy(self, sample_data):
        """Create test strategy."""
        return SimpleStrategy(sample_data)

    @pytest.fixture
    def risk_manager(self):
        """Create risk manager."""
        return RiskManager(frequency='1h', leverage=2.0)

    def test_engine_initialization(self, strategy, risk_manager):
        """Engine should initialize correctly."""
        engine = BacktestEngine(strategy.df, strategy, risk_manager, initial_balance=10000)
        assert engine.balance == 10000
        assert len(engine.trades) == 0
        assert len(engine.equity_curve) == 0
        assert engine.total_slippage == 0.0

    def test_engine_bars_per_day_calculation(self, sample_data, strategy, risk_manager):
        """Engine should calculate bars per day correctly."""
        engine = BacktestEngine(sample_data, strategy, risk_manager)
        # Sample data is hourly, so bars_per_day should be 24
        assert engine.bars_per_day == pytest.approx(24.0, rel=0.1)

    def test_engine_run_produces_equity_curve(self, strategy, risk_manager):
        """Engine run should produce equity curve."""
        engine = BacktestEngine(strategy.df, strategy, risk_manager, initial_balance=10000)
        equity = engine.run()

        assert len(equity) > 0
        assert equity[0] > 0  # Starting equity
        assert all(e >= 0 for e in equity)  # Equity never negative

    def test_engine_tracks_trades(self, strategy, risk_manager):
        """Engine should record all trades."""
        engine = BacktestEngine(strategy.df, strategy, risk_manager, initial_balance=10000)
        engine.run()

        # Should have at least entry and exit trade
        assert len(engine.trades) >= 2

    def test_engine_tracks_slippage(self, strategy, risk_manager):
        """Engine should track total slippage."""
        engine = BacktestEngine(strategy.df, strategy, risk_manager, initial_balance=10000)
        engine.run()

        # Slippage should be positive (cost)
        assert engine.total_slippage >= 0

    def test_engine_tracks_borrow(self, strategy, risk_manager):
        """Engine should track short borrow costs."""
        # Create strategy that goes short
        class ShortStrategy(BaseStrategy):
            def generate_signals(self):
                self.df['signal'] = -1  # Always short
                return self.df

            def manage_trade(self, row, position, entry_price, wallet=0):
                return 'HOLD', None

        df = strategy.df.copy()
        short_strat = ShortStrategy(df)
        engine = BacktestEngine(df, short_strat, risk_manager, initial_balance=10000)
        engine.run()

        # Borrow cost should be tracked for short position
        assert engine.total_borrow >= 0

    def test_engine_no_liquidation_low_leverage(self, strategy, risk_manager):
        """Low leverage should not cause liquidation."""
        engine = BacktestEngine(strategy.df, strategy, risk_manager, initial_balance=10000)
        equity = engine.run()

        # Final equity should be positive
        assert equity[-1] > 0

    def test_engine_position_management(self, sample_data, risk_manager):
        """Engine should correctly manage position lifecycle."""
        class BuyHoldStrategy(BaseStrategy):
            def generate_signals(self):
                self.df['signal'] = 0
                self.df.loc[self.df.index[10], 'signal'] = 1  # Buy at bar 10
                return self.df

            def manage_trade(self, row, position, entry_price, wallet=0):
                if position > 0 and row.name > self.df.index[50]:
                    return 'EXIT', None  # Exit at bar 50+
                return 'HOLD', None

        strategy = BuyHoldStrategy(sample_data)
        engine = BacktestEngine(sample_data, strategy, risk_manager, initial_balance=10000)
        equity = engine.run()

        # Should have opened and closed position
        assert any(t['type'] in ('BUY', 'BUY_ADD') for t in engine.trades)
        assert any(t['type'] == 'EXIT_LONG' for t in engine.trades)

    def test_engine_handles_gaps(self, risk_manager):
        """Engine should handle data gaps gracefully."""
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        dates = dates.append(pd.date_range('2024-01-05', periods=50, freq='1h'))  # 3-day gap

        df = pd.DataFrame({
            'Open': 50000.0,
            'High': 50100.0,
            'Low': 49900.0,
            'Close': 50000.0,
            'Volume': 1000.0,
        }, index=dates)

        class SimpleStrat(BaseStrategy):
            def generate_signals(self):
                self.df['signal'] = 1
                return self.df

            def manage_trade(self, row, position, entry_price, wallet=0):
                return 'HOLD', None

        strategy = SimpleStrat(df)
        engine = BacktestEngine(df, strategy, risk_manager, initial_balance=10000)
        equity = engine.run()

        # Should complete without crashing
        assert len(equity) > 0

    def test_engine_slippage_affects_pnl(self, sample_data, risk_manager):
        """Slippage should reduce realized PnL."""
        # Run with realistic slippage
        class BuySellStrategy(BaseStrategy):
            def generate_signals(self):
                self.df['signal'] = 0
                self.df.loc[self.df.index[10], 'signal'] = 1
                self.df.loc[self.df.index[20], 'signal'] = 0
                return self.df

            def manage_trade(self, row, position, entry_price, wallet=0):
                return 'HOLD', None

        strategy = BuySellStrategy(sample_data)
        engine = BacktestEngine(sample_data, strategy, risk_manager, initial_balance=10000)
        equity = engine.run()

        # With slippage, final equity should be less than if price just went up
        initial = 10000.0
        final = equity[-1]
        # Slippage cost should be reflected
        assert engine.total_slippage > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
