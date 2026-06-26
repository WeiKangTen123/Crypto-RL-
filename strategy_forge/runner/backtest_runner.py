"""
backtest_runner.py — plugs StrategyDNA into the existing BacktestEngine.

score_dna()        : run one DNA, return scalar score (ROI by default)
score_population() : run a list of DNAs in sequence, return scored list
"""
import math
from typing import List, Tuple

import pandas as pd

from strategy_backtest.engine  import BacktestEngine
from strategy_backtest.risk    import RiskManager
from strategy_backtest.metrics import compute_metrics, _extract_numeric
from strategy_forge.composer.dna import StrategyDNA


# Default risk config — overridable per call
DEFAULT_RISK = dict(
    risk_per_trade=0.01,
    leverage=5,
    trading_fee=0.0004,
    slippage_pct=0.0005,
    maintenance_margin_rate=0.004,
    initial_balance=10_000,
)


def score_dna(dna: StrategyDNA, df,
              risk: dict = None,
              score_mode: str = 'roi',
              min_trades: int = 20) -> Tuple[float, dict]:
    """
    Run one StrategyDNA through BacktestEngine and return (score, metrics_dict).

    Parameters
    ----------
    dna        : StrategyDNA instance
    df         : OHLCV DataFrame OR Dict[str, pd.DataFrame] for multi-coin test.
    risk       : override DEFAULT_RISK fields
    score_mode : 'roi'    → Total Return %
                 'sharpe' → Sharpe Ratio
                 'blend'  → 0.5 × log(ROI+1) + 0.5 × Sharpe
    min_trades : return -999 score if fewer trades than this

    Returns
    -------
    (score, metrics) — metrics is the raw _extract_numeric dict
    """
    r = {**DEFAULT_RISK, **(risk or {})}

    if isinstance(df, dict):
        # Multi-coin mode: run backtest on each coin and average the results
        total_roi = 0.0
        total_annual = 0.0
        total_sharpe = 0.0
        total_mdd = 0.0
        total_wr = 0.0
        total_trades = 0
        total_tpw = 0.0
        valid_coins = 0

        for coin, df_c in df.items():
            sc, m = score_dna(dna, df_c, risk, score_mode, min_trades=1) # bypass min_trades per coin
            if sc != -999.0:
                total_roi    += m.get('Total Return', 0)
                total_annual += m.get('Annual Return', 0)
                total_sharpe += m.get('Sharpe Ratio', 0)
                total_mdd    += m.get('Max Drawdown %', 0)
                total_wr     += m.get('Win Rate', 0)
                total_trades += m.get('Total Trades', 0)
                total_tpw    += m.get('trades_per_week', 0)
                valid_coins  += 1

        if valid_coins == 0 or total_trades < min_trades:
            return -999.0, {'error': 'Failed multi-coin or min_trades not met'}

        avg_roi    = total_roi    / valid_coins
        avg_annual = total_annual / valid_coins
        avg_sharpe = total_sharpe / valid_coins
        avg_mdd    = total_mdd    / valid_coins
        avg_wr     = total_wr     / valid_coins
        avg_tpw    = total_tpw    / valid_coins

        if avg_mdd > 80 or avg_roi < -90:
            return -999.0, {'error': 'drawdown/roi limit exceeded'}

        if score_mode == 'roi':
            score = avg_roi
        elif score_mode == 'sharpe':
            score = avg_sharpe
        else:  # blend
            roi_log = math.copysign(math.log1p(abs(avg_roi) / 25.0), avg_roi)
            score   = 0.5 * avg_sharpe + 0.5 * roi_log

        style = 'hft' if avg_tpw >= 30 else 'mft' if avg_tpw >= 8 else 'swing' if avg_tpw >= 2 else 'position'

        metrics = {
            'Total Return':   avg_roi,
            'Annual Return':  avg_annual,
            'Sharpe Ratio':   avg_sharpe,
            'Max Drawdown %': avg_mdd,
            'Win Rate':       avg_wr,
            'Total Trades':   total_trades,
            'trades_per_week': avg_tpw,
            'style':          style
        }
        return round(score, 4), metrics

    # Single coin logic
    # Rebind DNA to fresh df copy so generate_signals() is clean
    dna_copy = StrategyDNA(df.copy(), dna.entry, dna.filters,
                           dna.exit_method, dna.params)
    try:
        rm = RiskManager(
            risk_per_trade=r['risk_per_trade'],
            leverage=r['leverage'],
            trading_fee=r['trading_fee'],
            slippage_pct=r['slippage_pct'],
            maintenance_margin_rate=r['maintenance_margin_rate'],
        )
        engine = BacktestEngine(df.copy(), dna_copy, rm,
                                initial_balance=r['initial_balance'])
        equity = engine.run()
        if not equity or len(equity) < 2:
            return -999.0, {}

        m  = compute_metrics(equity, r['initial_balance'],
                             timestamps=engine.df.index, trades=engine.trades)
        nm = _extract_numeric(m)

        total_ret  = float(nm.get('Total Return',  -999) or -999)
        sharpe     = float(nm.get('Sharpe Ratio',  -999) or -999)
        trades     = int(nm.get('Total Trades',    0))
        mdd        = abs(float(nm.get('Max Drawdown %', 100) or 100))
        pf_raw     = nm.get('Profit Factor', 0) or 0
        pf         = 2.0 if float(pf_raw) >= 99 else float(pf_raw)

        if trades < min_trades:
            return -999.0, nm
        if mdd > 80:
            return -999.0, nm
        if total_ret < -90:
            return -999.0, nm

        # Compute trade frequency and style label
        try:
            weeks = (df.index[-1] - df.index[0]).total_seconds() / (7 * 86400)
            tpw   = round(trades / weeks, 1) if weeks > 0 else 0
        except Exception:
            tpw = 0
        if tpw >= 30:
            style = 'hft'
        elif tpw >= 8:
            style = 'mft'
        elif tpw >= 2:
            style = 'swing'
        else:
            style = 'position'
        nm['trades_per_week'] = tpw
        nm['style']           = style

        if score_mode == 'roi':
            score = total_ret
        elif score_mode == 'sharpe':
            score = sharpe
        else:  # blend
            roi_log = math.copysign(math.log1p(abs(total_ret) / 25.0), total_ret)
            score   = 0.5 * sharpe + 0.5 * roi_log

        return round(score, 4), nm

    except Exception as e:
        return -999.0, {'error': str(e)}


def score_population(population: List[StrategyDNA],
                     df: pd.DataFrame,
                     risk: dict = None,
                     score_mode: str = 'roi',
                     min_trades: int = 20,
                     verbose: bool = True) -> List[Tuple[float, StrategyDNA, dict]]:
    """
    Score all DNAs in the population. Returns list of (score, dna, metrics),
    sorted descending by score.
    """
    results = []
    for i, dna in enumerate(population):
        score, metrics = score_dna(dna, df, risk, score_mode, min_trades)
        results.append((score, dna, metrics))
        if verbose:
            roi   = metrics.get('Total Return', '?')
            sh    = metrics.get('Sharpe Ratio', '?')
            trd   = metrics.get('Total Trades', '?')
            tpw   = metrics.get('trades_per_week', '?')
            style = metrics.get('style', '')
            status = (f"score={score:>8.2f}  ROI={roi}%  Sharpe={sh}  "
                      f"Trades={trd}  ({tpw}/wk)  [{style}]")
            print(f"  [{i+1:>3}/{len(population)}] {dna.entry:<20} {status}")

    results.sort(key=lambda x: x[0], reverse=True)
    return results
