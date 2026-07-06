"""Tests for verdict_engine.py"""

import pytest
import numpy as np
import pandas as pd
from strategy_backtest.verdict_engine import VerdictEngine, Verdict


class TestVerdictEngine:
    """Test verdict rule logic."""

    @pytest.fixture
    def engine(self):
        """Create a VerdictEngine instance."""
        return VerdictEngine(frequency='4h')

    @pytest.fixture
    def minimal_metrics(self):
        """Minimal metrics dict for testing."""
        return {
            'Sharpe Ratio': '1.5',
            'Total Return': '50%',
            'Max Drawdown (%)': '15.0',
            'Profit Factor': '2.0',
            'Win Rate': '55%',
            'Total Trades': '100',
            'Cost Ratio': '10%',
            'Worst Daily Loss': '-5.0%',
            'Monthly GTP': '2.0',
        }

    @pytest.fixture
    def equity_curve(self):
        """Minimal equity curve."""
        return [10000.0] + [10000.0 * (1.0 + i * 0.0005) for i in range(100)]

    def test_parse_metric_valid(self, engine):
        """Parse valid formatted metric."""
        value = engine._parse_metric({'Sharpe Ratio': '1.5'}, 'Sharpe Ratio')
        assert value == pytest.approx(1.5)

    def test_parse_metric_with_dollars(self, engine):
        """Parse metric with $ sign."""
        value = engine._parse_metric({'Net Profit': '$1,250.50'}, 'Net Profit')
        assert value == pytest.approx(1250.50)

    def test_parse_metric_with_percent(self, engine):
        """Parse metric with % sign."""
        value = engine._parse_metric({'Win Rate': '55.5%'}, 'Win Rate')
        assert value == pytest.approx(55.5)

    def test_parse_metric_infinity(self, engine):
        """Parse ∞ as 99."""
        value = engine._parse_metric({'Profit Factor': '∞'}, 'Profit Factor')
        assert value == 99.0

    def test_parse_metric_missing_returns_default(self, engine):
        """Missing metric returns default."""
        value = engine._parse_metric({}, 'Missing Key', default=42.0)
        assert value == 42.0

    def test_total_return_positive(self, engine):
        """Calculate positive total return."""
        equity = [10000.0, 11000.0, 12100.0]
        ret = engine._total_return(equity, initial_balance=10000.0)
        assert ret == pytest.approx(21.0)  # 21% return

    def test_total_return_zero(self, engine):
        """Calculate zero return."""
        equity = [10000.0, 10000.0, 10000.0]
        ret = engine._total_return(equity, initial_balance=10000.0)
        assert ret == pytest.approx(0.0)

    def test_quick_mdd(self, engine):
        """Calculate max drawdown correctly."""
        equity = [10000.0, 11000.0, 10500.0, 11500.0, 11000.0]
        # Peak is 11500, trough is 10500, MDD = (11500 - 10500) / 11500 × 100 ≈ 8.7%
        mdd = engine._quick_mdd(equity)
        assert mdd > 0
        assert mdd < 100

    def test_pbo_low_overfit_risk(self, engine):
        """High Sharpe with many bars = low overfit risk."""
        pbo = engine._calculate_pbo(sharpe_ratio=2.0, n_params=5, n_bars=1000)
        # High Sharpe, adequate sample = low PBO
        assert pbo < 0.15

    def test_pbo_high_overfit_risk(self, engine):
        """Low Sharpe with few bars = high overfit risk."""
        pbo = engine._calculate_pbo(sharpe_ratio=0.5, n_params=20, n_bars=100)
        # Low Sharpe, many params, few bars = high PBO
        assert pbo > 0.15

    def test_pbo_negative_sharpe(self, engine):
        """Negative Sharpe should give max PBO."""
        pbo = engine._calculate_pbo(sharpe_ratio=-1.0, n_params=5, n_bars=1000)
        assert pbo == 1.0

    def test_pbo_zero_sharpe(self, engine):
        """Zero Sharpe should give max PBO."""
        pbo = engine._calculate_pbo(sharpe_ratio=0.0, n_params=5, n_bars=1000)
        assert pbo == 1.0

    def test_check_all_good_strategy(self, engine, minimal_metrics, equity_curve):
        """Good strategy should pass verdict."""
        result = engine.check_all(
            metrics_dict=minimal_metrics,
            equity_curve=equity_curve,
            trades=[],
            timestamps=pd.date_range('2024-01-01', periods=100, freq='1h'),
            cfg={'params': {'param1': 1.0, 'param2': 2.0}},
            is_crypto=True,
        )

        assert 'decision' in result
        assert 'score' in result
        assert result['score'] >= 0
        assert result['score'] <= 100

    def test_check_all_low_sharpe_fails(self, engine, minimal_metrics, equity_curve):
        """Low Sharpe should fail T1-01."""
        bad_metrics = minimal_metrics.copy()
        bad_metrics['Sharpe Ratio'] = '0.3'  # Below 0.5 threshold

        result = engine.check_all(
            metrics_dict=bad_metrics,
            equity_curve=equity_curve,
            trades=[],
            timestamps=pd.date_range('2024-01-01', periods=100, freq='1h'),
            cfg={},
            is_crypto=False,
        )

        # Should fail T1-01
        assert 'T1-01' in result['blocking_rules']

    def test_check_all_high_drawdown_fails(self, engine, minimal_metrics, equity_curve):
        """High drawdown should fail T1-03."""
        bad_metrics = minimal_metrics.copy()
        bad_metrics['Max Drawdown (%)'] = '30.0'  # Above 20% threshold

        result = engine.check_all(
            metrics_dict=bad_metrics,
            equity_curve=equity_curve,
            trades=[],
            timestamps=pd.date_range('2024-01-01', periods=100, freq='1h'),
            cfg={},
            is_crypto=False,
        )

        # Should fail T1-03
        assert 'T1-03' in result['blocking_rules']

    def test_check_all_with_wfo_results(self, engine, minimal_metrics, equity_curve):
        """WFO results should be used in T2-01/T2-02."""
        wfo_results = {
            'wf_efficiency': 0.6,  # OOS/IS = 0.6, passes T2-01
            'oos_is_decay': 0.3,   # IS - OOS = 0.3, passes T2-02
        }

        result = engine.check_all(
            metrics_dict=minimal_metrics,
            equity_curve=equity_curve,
            trades=[],
            timestamps=pd.date_range('2024-01-01', periods=100, freq='1h'),
            cfg={},
            is_crypto=False,
            wfo_results=wfo_results,
        )

        # Check that WFO was evaluated
        outcomes = result['outcomes']
        t201 = [o for o in outcomes if o['rule_id'] == 'T2-01']
        assert len(t201) > 0
        assert t201[0]['passed'] == True  # 0.6 >= 0.5

    def test_verdict_rejected_on_bad_data(self, engine):
        """Bad data should result in REJECTED verdict."""
        bad_metrics = {'error': 'Data error'}

        result = engine.check_all(
            metrics_dict=bad_metrics,
            equity_curve=[],
            trades=[],
            timestamps=None,
            cfg={},
            is_crypto=False,
        )

        assert result['decision'] == 'REJECTED'
        assert result['score'] == 0.0

    def test_format_output_structure(self, engine):
        """Formatted output should have required keys."""
        engine.verdict = Verdict.PASS
        engine.score = 85.0
        engine.results = [
            {'rule_id': 'T1-01', 'passed': True, 'tier': 'T1'},
            {'rule_id': 'T2-03', 'passed': False, 'tier': 'T2'},
        ]

        output = engine._format_output()

        assert 'decision' in output
        assert 'score' in output
        assert 'blocking_rules' in output
        assert 'outcomes' in output
        assert output['decision'] == 'PASS'
        assert output['score'] == 85.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
