"""Tests for data_validator.py"""

import pytest
import pandas as pd
import numpy as np
from strategy_backtest.data_validator import DataValidator, ValidationIssue


class TestDataValidator:
    """Test data validation logic."""

    @pytest.fixture
    def valid_df(self):
        """Create a valid OHLCV DataFrame."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({
            'Open': np.random.uniform(30000, 35000, 100),
            'High': np.random.uniform(35000, 36000, 100),
            'Low': np.random.uniform(29000, 30000, 100),
            'Close': np.random.uniform(30000, 35000, 100),
            'Volume': np.random.uniform(100, 1000, 100),
        }, index=dates)
        # Fix OHLC logic: ensure H >= L, O/C within [L,H]
        df['High'] = df[['Open', 'High', 'Close']].max(axis=1) + 100
        df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1) - 100
        df = df.sort_index()
        return df

    def test_valid_data_passes(self, valid_df):
        """Valid data should pass all checks."""
        validator = DataValidator()
        issues = validator.validate(valid_df, symbol='BTCUSDT')
        errors = [i for i in issues if i.severity == 'ERROR']
        assert len(errors) == 0, f"Valid data should have no errors: {errors}"

    def test_empty_dataframe_fails(self):
        """Empty DataFrame should fail."""
        validator = DataValidator()
        issues = validator.validate(pd.DataFrame())
        errors = [i for i in issues if i.severity == 'ERROR']
        assert len(errors) > 0
        assert any(i.type == 'EMPTY_DATA' for i in errors)

    def test_missing_required_columns(self):
        """DataFrame missing required columns should fail."""
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'Close': [101, 102, 103],
            # Missing High, Low, Volume
        }, index=pd.date_range('2024-01-01', periods=3, freq='1h'))

        validator = DataValidator()
        issues = validator.validate(df)
        errors = [i for i in issues if i.severity == 'ERROR']
        assert any(i.type == 'MISSING_COLUMNS' for i in errors)

    def test_high_less_than_low_fails(self):
        """High < Low should be caught."""
        dates = pd.date_range('2024-01-01', periods=3, freq='1h')
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [95, 96, 97],  # Less than Low
            'Low': [105, 106, 107],
            'Close': [102, 103, 104],
            'Volume': [100, 100, 100],
        }, index=dates)

        validator = DataValidator()
        issues = validator.validate(df)
        errors = [i for i in issues if i.severity == 'ERROR']
        assert any(i.type == 'HIGH_LT_LOW' for i in errors)

    def test_zero_volume_warning(self):
        """Zero volume should generate warning."""
        dates = pd.date_range('2024-01-01', periods=3, freq='1h')
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [110, 111, 112],
            'Low': [90, 91, 92],
            'Close': [102, 103, 104],
            'Volume': [0, 100, 100],  # One zero volume
        }, index=dates)

        validator = DataValidator()
        issues = validator.validate(df)
        warns = [i for i in issues if i.severity == 'WARN']
        assert any(i.type == 'ZERO_VOLUME' for i in warns)

    def test_negative_volume_fails(self):
        """Negative volume should be caught."""
        dates = pd.date_range('2024-01-01', periods=3, freq='1h')
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [110, 111, 112],
            'Low': [90, 91, 92],
            'Close': [102, 103, 104],
            'Volume': [-50, 100, 100],  # Negative volume
        }, index=dates)

        validator = DataValidator()
        issues = validator.validate(df)
        errors = [i for i in issues if i.severity == 'ERROR']
        assert any(i.type == 'NEGATIVE_VOLUME' for i in errors)

    def test_data_gaps_detected(self):
        """Missing bars (gaps) should be detected."""
        dates = [
            pd.Timestamp('2024-01-01 00:00:00'),
            pd.Timestamp('2024-01-01 01:00:00'),
            pd.Timestamp('2024-01-01 02:00:00'),
            pd.Timestamp('2024-01-01 10:00:00'),  # 8 hour gap!
        ]
        df = pd.DataFrame({
            'Open': [100, 101, 102, 103],
            'High': [110, 111, 112, 113],
            'Low': [90, 91, 92, 93],
            'Close': [102, 103, 104, 105],
            'Volume': [100, 100, 100, 100],
        }, index=dates)

        validator = DataValidator()
        issues = validator.validate(df)
        warns = [i for i in issues if i.severity == 'WARN']
        assert any(i.type == 'DATA_GAPS' for i in warns)

    def test_duplicate_timestamps_detected(self):
        """Duplicate timestamps should be caught."""
        dates = [
            pd.Timestamp('2024-01-01 00:00:00'),
            pd.Timestamp('2024-01-01 01:00:00'),
            pd.Timestamp('2024-01-01 01:00:00'),  # Duplicate!
        ]
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [110, 111, 112],
            'Low': [90, 91, 92],
            'Close': [102, 103, 104],
            'Volume': [100, 100, 100],
        }, index=dates)

        validator = DataValidator()
        issues = validator.validate(df)
        errors = [i for i in issues if i.severity == 'ERROR']
        assert any(i.type == 'DUPLICATE_TIMESTAMPS' for i in errors)

    def test_summary_generation(self, valid_df):
        """Summary should be generated correctly."""
        validator = DataValidator()
        validator.validate(valid_df)
        summary = validator.summary()

        assert 'status' in summary
        assert 'error_count' in summary
        assert 'warn_count' in summary

    def test_missing_funding_rate_warning(self, valid_df):
        """Missing funding_rate should generate warning."""
        # valid_df has no funding_rate column
        validator = DataValidator()
        issues = validator.validate(valid_df)
        warns = [i for i in issues if i.severity == 'WARN']
        assert any(i.type == 'NO_FUNDING_RATE' for i in warns)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
