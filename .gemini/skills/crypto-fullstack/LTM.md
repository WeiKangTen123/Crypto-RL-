# Agent Long-Term Memory (LTM)
## Agent: @crypto-fullstack

### Purpose
To store distilled insights, historical constraints, and lessons learned that must persist across sessions. Unlike logs, this file contains *wisdom*, not actions.

### Historical Insights & Constraints
- 2026-06-04 | Initialized LTM system.
- 2026-06-08 | Syntax errors in settings.py (like unexpected indents) often stem from malformed dictionary structures in STRATEGY_LIBRARY.
- 2026-06-19 | Stale module caching in Flask endpoints | Always force reload strategy_backtest.library and strategy_backtest.strategies before executing any backtests or validation runs to prevent ImportError / syntax cache mismatches.
