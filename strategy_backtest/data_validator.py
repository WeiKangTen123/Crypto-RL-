"""
data_validator.py — OHLCV data validation for backtests.

Validates:
  - OHLC logic (H ≥ L, O/C within range, etc)
  - Data gaps (missing bars)
  - Volume checks (> 0)
  - Column presence and types

Usage:
    validator = DataValidator()
    issues = validator.validate(df)
    if issues:
        print(f"Data has {len(issues)} issues")
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class ValidationIssue:
    """Single data validation issue."""
    def __init__(self, severity: str, issue_type: str, message: str, details: Dict = None):
        self.severity = severity  # 'ERROR' | 'WARN' | 'INFO'
        self.type = issue_type
        self.message = message
        self.details = details or {}

    def __repr__(self):
        return f"[{self.severity}] {self.type}: {self.message}"


class DataValidator:
    """Validates OHLCV data before backtesting."""

    REQUIRED_COLUMNS = {'Open', 'High', 'Low', 'Close', 'Volume'}
    OPTIONAL_COLUMNS = {'funding_rate', 'bid_spread', 'ask_spread', 'symbol'}

    def __init__(self, strict=False):
        """
        Args:
            strict: If True, WARN becomes ERROR, fails validation
        """
        self.strict = strict
        self.issues: List[ValidationIssue] = []

    def validate(self, df: pd.DataFrame, symbol: str = 'UNKNOWN') -> List[ValidationIssue]:
        """
        Run all validation checks on a DataFrame.

        Args:
            df: OHLCV DataFrame (index should be datetime)
            symbol: Symbol name for error messages

        Returns:
            List of ValidationIssue objects (empty if all OK)
        """
        self.issues = []

        if df is None or len(df) == 0:
            self.issues.append(ValidationIssue(
                'ERROR', 'EMPTY_DATA',
                f"DataFrame is empty or None",
            ))
            return self.issues

        # Check columns
        self._check_columns(df)

        # Check index
        self._check_index(df)

        # Check OHLC logic
        self._check_ohlc_logic(df, symbol)

        # Check volume
        self._check_volume(df, symbol)

        # Check gaps
        self._check_gaps(df, symbol)

        # Check duplicates
        self._check_duplicates(df, symbol)

        return self.issues

    def _check_columns(self, df: pd.DataFrame):
        """Validate required columns exist."""
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            self.issues.append(ValidationIssue(
                'ERROR', 'MISSING_COLUMNS',
                f"Missing required columns: {missing}"
            ))

        # Warn if recommended columns missing
        has_funding = 'funding_rate' in df.columns
        if not has_funding:
            self.issues.append(ValidationIssue(
                'WARN', 'NO_FUNDING_RATE',
                "No 'funding_rate' column. Funding P&L won't be tracked."
            ))

    def _check_index(self, df: pd.DataFrame):
        """Validate index is datetime and sorted."""
        if not isinstance(df.index, pd.DatetimeIndex):
            self.issues.append(ValidationIssue(
                'ERROR', 'BAD_INDEX',
                f"Index must be DatetimeIndex, got {type(df.index).__name__}"
            ))
            return

        # Check sorted
        if not df.index.is_monotonic_increasing:
            self.issues.append(ValidationIssue(
                'ERROR', 'UNSORTED_INDEX',
                "Index is not monotonically increasing (not sorted by time)"
            ))

    def _check_ohlc_logic(self, df: pd.DataFrame, symbol: str):
        """Validate OHLC relationships."""
        required = {'Open', 'High', 'Low', 'Close'} & set(df.columns)
        if len(required) < 4:
            return  # Can't check without all 4

        o = df['Open'].values
        h = df['High'].values
        l = df['Low'].values
        c = df['Close'].values

        # H ≥ L
        bad_hl = np.where(h < l)[0]
        if len(bad_hl) > 0:
            self.issues.append(ValidationIssue(
                'ERROR', 'HIGH_LT_LOW',
                f"High < Low in {len(bad_hl)} bars (e.g., bar {bad_hl[0]})",
                {'symbol': symbol, 'count': len(bad_hl), 'first_idx': int(bad_hl[0])}
            ))

        # O, C within [L, H]
        bad_o = np.where((o < l) | (o > h))[0]
        if len(bad_o) > 0:
            self.issues.append(ValidationIssue(
                'ERROR', 'OPEN_OUT_OF_RANGE',
                f"Open outside [Low, High] in {len(bad_o)} bars",
                {'symbol': symbol, 'count': len(bad_o)}
            ))

        bad_c = np.where((c < l) | (c > h))[0]
        if len(bad_c) > 0:
            self.issues.append(ValidationIssue(
                'ERROR', 'CLOSE_OUT_OF_RANGE',
                f"Close outside [Low, High] in {len(bad_c)} bars",
                {'symbol': symbol, 'count': len(bad_c)}
            ))

    def _check_volume(self, df: pd.DataFrame, symbol: str):
        """Validate volume data."""
        if 'Volume' not in df.columns:
            return

        vol = df['Volume'].values

        # Volume ≥ 0
        bad_vol = np.where(vol < 0)[0]
        if len(bad_vol) > 0:
            self.issues.append(ValidationIssue(
                'ERROR', 'NEGATIVE_VOLUME',
                f"Negative volume in {len(bad_vol)} bars",
                {'symbol': symbol, 'count': len(bad_vol)}
            ))

        # Warn on zero volume
        zero_vol = np.where(vol == 0)[0]
        if len(zero_vol) > 0:
            pct = len(zero_vol) / len(vol) * 100
            severity = 'ERROR' if pct > 10 else 'WARN'
            self.issues.append(ValidationIssue(
                severity, 'ZERO_VOLUME',
                f"Zero volume in {len(zero_vol)} bars ({pct:.1f}%)",
                {'symbol': symbol, 'count': len(zero_vol), 'percent': pct}
            ))

    def _check_gaps(self, df: pd.DataFrame, symbol: str):
        """Detect missing bars (data gaps)."""
        if len(df) < 2:
            return

        idx = df.index
        diffs = idx.to_series().diff().dropna()

        if len(diffs) == 0:
            return

        # Get median bar spacing
        median_diff = diffs.median()
        median_seconds = median_diff.total_seconds()

        # Find bars > 2x median spacing
        bad_gaps = np.where(diffs.values > 2 * median_diff)[0]
        if len(bad_gaps) > 0:
            gap_count = len(bad_gaps)
            severity = 'WARN' if gap_count <= 5 else 'ERROR'
            self.issues.append(ValidationIssue(
                severity, 'DATA_GAPS',
                f"Found {gap_count} data gaps (> 2x bar spacing)",
                {'symbol': symbol, 'count': gap_count, 'median_spacing_sec': median_seconds}
            ))

    def _check_duplicates(self, df: pd.DataFrame, symbol: str):
        """Detect duplicate timestamps."""
        if df.index.duplicated().any():
            dup_count = df.index.duplicated().sum()
            self.issues.append(ValidationIssue(
                'ERROR', 'DUPLICATE_TIMESTAMPS',
                f"Found {dup_count} duplicate timestamps",
                {'symbol': symbol, 'count': dup_count}
            ))

    def summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        if not self.issues:
            return {'status': 'OK', 'issue_count': 0}

        errors = [i for i in self.issues if i.severity == 'ERROR']
        warns = [i for i in self.issues if i.severity == 'WARN']

        return {
            'status': 'FAIL' if errors else 'WARN' if warns else 'OK',
            'error_count': len(errors),
            'warn_count': len(warns),
            'errors': [str(i) for i in errors],
            'warnings': [str(i) for i in warns],
        }

    def print_summary(self):
        """Print validation summary to stdout."""
        summary = self.summary()
        status = summary['status']
        errors = summary.get('error_count', 0)
        warns = summary.get('warn_count', 0)

        icon = '✓' if status == 'OK' else '⚠' if status == 'WARN' else '✗'
        print(f"\n{icon} Data Validation: {status}")
        print(f"  Errors: {errors}  |  Warnings: {warns}")

        if errors > 0:
            print("\n  Errors:")
            for msg in summary.get('errors', []):
                print(f"    ✗ {msg}")

        if warns > 0:
            print("\n  Warnings:")
            for msg in summary.get('warnings', []):
                print(f"    ⚠ {msg}")

        print()

    def assert_valid(self) -> bool:
        """
        Raise error if validation failed (strict mode).

        Returns:
            True if all OK or validation is permissive
        """
        errors = [i for i in self.issues if i.severity == 'ERROR']
        if errors and (self.strict or len(errors) > 0):
            error_msgs = '\n'.join(f"  - {i}" for i in errors)
            raise ValueError(f"Data validation failed:\n{error_msgs}")
        return True
