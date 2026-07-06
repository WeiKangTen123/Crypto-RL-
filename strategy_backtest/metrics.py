import numpy as np
import pandas as pd


# ── Numeric extractor ─────────────────────────────────────────────────────────
def _extract_numeric(metrics: dict) -> dict:
    """
    Strip formatting from a compute_metrics result and return raw floats.
    Used by the optimizer for sorting and CSV output.
    """
    def _parse(v) -> float:
        if v is None:
            return 0.0
        s = str(v).replace('$', '').replace(',', '').replace('%', '').strip()
        if s == '∞':
            return 99.0  # all-win sentinel: no losing trades, PF is effectively infinite
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    return {
        'Sharpe Ratio':   _parse(metrics.get('Sharpe Ratio')),
        'Sortino Ratio':  _parse(metrics.get('Sortino Ratio')),
        'Calmar Ratio':   _parse(metrics.get('Calmar Ratio')),
        'Total Return':   _parse(metrics.get('Total Return')),
        'Annual Return':  _parse(metrics.get('Annual Return')),
        'Max Drawdown %': _parse(metrics.get('Max Drawdown (%)')),
        'Profit Factor':  _parse(metrics.get('Profit Factor')),
        'Win Rate':       _parse(metrics.get('Win Rate')),
        'Total Trades':   int(_parse(metrics.get('Total Trades', 0))),
        'Recovery Factor': _parse(metrics.get('Recovery Factor')),
        'Expectancy':     _parse(metrics.get('Expectancy')),
    }


def compute_metrics(equity, initial_balance, timestamps=None, trades=None, df=None, total_slippage=0.0):
    """
    Compute comprehensive backtest metrics.

    Args:
        equity: Equity curve list
        initial_balance: Starting capital
        timestamps: Datetime index (optional)
        trades: Trade list (optional)
        df: DataFrame with OHLCV (optional)
        total_slippage: Total slippage cost from engine (realistic, all-in)

    Returns:
        Dictionary with all metrics including all-in cost ratio
    """
    if len(equity) == 0:
        return {}

    final_balance  = equity[-1]
    net_profit     = final_balance - initial_balance
    total_return   = net_profit / initial_balance * 100

    # Drawdown
    peak         = np.maximum.accumulate(equity)
    dd_abs       = peak - equity
    dd_pct       = dd_abs / peak * 100
    max_dd_abs   = float(np.max(dd_abs))
    max_dd_pct   = float(np.max(dd_pct))

    # Annualisation factor — derive from actual bar spacing, not a hardcoded 365
    if timestamps is not None and len(timestamps) >= 2:
        ts_idx     = pd.DatetimeIndex(timestamps)
        median_sec = float(ts_idx.to_series().diff().dropna().dt.total_seconds().median())
        bars_per_year = (365.25 * 24 * 3600 / median_sec) if median_sec > 0 else 365.0
    else:
        bars_per_year = 365.0
    ann_factor = np.sqrt(bars_per_year)

    # Bar returns & ratios
    returns    = pd.Series(equity).pct_change().dropna()
    std_ret    = float(returns.std())
    sharpe     = float(returns.mean() / std_ret * ann_factor) if std_ret != 0 else 0.0
    # Semi-deviation: clip positive returns to 0, square all, take sqrt of mean
    downside_sq = np.minimum(returns.values, 0.0) ** 2
    down_std    = float(np.sqrt(downside_sq.mean())) if len(returns) > 0 else 0.0
    sortino     = float(returns.mean() / down_std * ann_factor) if down_std != 0 else 0.0

    # Annualised return (CAGR) — uses 365.25 to match bars_per_year calculation
    if timestamps is not None:
        n_days = max((timestamps[-1] - timestamps[0]).days, 1)
        ratio = final_balance / initial_balance
        annual_return = (ratio ** (365.25 / n_days) - 1) * 100 if ratio > 0 else -100.0
    else:
        annual_return = total_return

    calmar   = float(annual_return / max_dd_pct) if max_dd_pct > 0 else 0.0
    recovery = float(net_profit / max_dd_abs)    if max_dd_abs > 0 else 0.0

    metrics = {
        "Initial Balance":  f"${float(initial_balance):,.2f}",
        "Final Balance":    f"${float(final_balance):,.2f}",
        "Total Return":     f"{total_return:.2f}%",
        "Annual Return":    f"{annual_return:.2f}%",
        "Max Drawdown ($)": f"${max_dd_abs:,.2f}",
        "Max Drawdown (%)": f"{max_dd_pct:.2f}%",
        "Sharpe Ratio":     f"{sharpe:.2f}",
        "Sortino Ratio":    f"{sortino:.2f}",
        "Calmar Ratio":     f"{calmar:.2f}",
        "Recovery Factor":  f"{recovery:.2f}",
    }

    # ── Deflated Sharpe Ratio (T2-04) ────────────────────────────────────────
    if len(returns) >= 10:
        try:
            from scipy.stats import norm as _norm
            T        = len(returns)
            skew_r   = float(returns.skew())
            kurt_r   = float(returns.kurt())   # excess kurtosis
            # Bailey & López de Prado (2012): kurt_r is excess kurtosis (pandas default),
            # so non-excess = kurt_r + 3, giving coefficient (kurt_r+3-1)/4 = (kurt_r+2)/4
            sigma_sq = (1.0 - skew_r * sharpe + (kurt_r + 2.0) / 4.0 * sharpe ** 2) / max(T - 1, 1)
            if sigma_sq > 0:
                dsr_p = float(1.0 - _norm.cdf(sharpe / np.sqrt(sigma_sq)))
                metrics['DSR p-value'] = f"{dsr_p:.4f}"
        except Exception:
            pass

    if trades is not None:
        total_trades = winning_trades = losing_trades = 0
        total_fees   = 0.0
        win_pnls     = []
        loss_pnls    = []
        durations    = []
        streak_w = streak_l = max_streak_w = max_streak_l = 0

        # Track long and short entries independently so hedge-mode strategies
        # (both sides open simultaneously) pair each exit with the correct entry.
        long_entry_rec   = None
        short_entry_rec  = None
        long_entry_fees  = 0.0
        short_entry_fees = 0.0
        gross_win_sum  = 0.0   # gross pnl of winning trades (profit factor numerator)
        gross_loss_sum = 0.0   # abs gross pnl of losing trades (profit factor denominator)
        gross_profit   = 0.0   # sum of gross pnl for winning trades only ("Gross Profit")

        def _record_closed_trade(t, entry_rec, entry_fees):
            nonlocal total_trades, winning_trades, losing_trades
            nonlocal gross_win_sum, gross_loss_sum, gross_profit
            nonlocal streak_w, streak_l, max_streak_w, max_streak_l

            total_trades += 1
            gross_pnl_val = float(t.get('gross_pnl', 0))
            # Full net: exit pnl minus ALL entry-layer fees accumulated for this side
            trade_net = t.get('pnl', 0) - entry_fees

            try:
                dur = (t['time'] - entry_rec['time']).total_seconds() / 3600
            except Exception:
                dur = 0
            durations.append(dur)

            if gross_pnl_val > 0:
                gross_profit += gross_pnl_val  # display only

            if trade_net > 0:
                gross_win_sum += trade_net      # net wins → PF numerator (consistent with Win Rate)
                winning_trades += 1;  win_pnls.append(trade_net)
                streak_w += 1;        streak_l = 0
                max_streak_w = max(max_streak_w, streak_w)
            elif trade_net < 0:
                gross_loss_sum += abs(trade_net)  # net losses → PF denominator
                losing_trades += 1;   loss_pnls.append(trade_net)
                streak_l += 1;        streak_w = 0
                max_streak_l = max(max_streak_l, streak_l)
            else:
                streak_w = streak_l = 0

        for t in trades:
            total_fees += t.get('fee', 0)

            if t['type'] in ('BUY', 'BUY_ADD'):
                if long_entry_rec is None:
                    long_entry_rec = t
                long_entry_fees += float(t.get('fee', 0))

            elif t['type'] in ('SELL', 'SELL_ADD'):
                if short_entry_rec is None:
                    short_entry_rec = t
                short_entry_fees += float(t.get('fee', 0))

            elif t['type'] == 'EXIT_LONG' and long_entry_rec is not None:
                _record_closed_trade(t, long_entry_rec, long_entry_fees)
                long_entry_rec  = None
                long_entry_fees = 0.0

            elif t['type'] == 'EXIT_SHORT' and short_entry_rec is not None:
                _record_closed_trade(t, short_entry_rec, short_entry_fees)
                short_entry_rec  = None
                short_entry_fees = 0.0

        win_rate     = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        avg_win      = float(np.mean(win_pnls))  if win_pnls  else 0.0
        avg_loss     = float(np.mean(loss_pnls)) if loss_pnls else 0.0
        best_trade   = float(max(win_pnls))       if win_pnls  else 0.0
        worst_trade  = float(min(loss_pnls))      if loss_pnls else 0.0
        avg_duration = float(np.mean(durations))  if durations else 0.0

        # 99.0 = sentinel for "all wins, no losing trades" (PF denominator is 0)
        profit_factor = (gross_win_sum / gross_loss_sum) if gross_loss_sum > 0 else 99.0
        expectancy    = (
            (winning_trades / total_trades * avg_win) +
            (losing_trades  / total_trades * avg_loss)
        ) if total_trades > 0 else 0.0

        total_slippage = sum(t.get('slippage_usd', 0) for t in trades)
        slippage_pct   = trades[0].get('slippage_pct', 0) if trades else 0

        metrics["Total Trades"]       = total_trades
        metrics["Win Rate"]           = f"{win_rate:.2f}%"
        metrics["Winning Trades"]     = winning_trades
        metrics["Losing Trades"]      = losing_trades
        metrics["Max Consec. Wins"]   = max_streak_w
        metrics["Max Consec. Losses"] = max_streak_l
        metrics["Avg Duration (hrs)"]  = f"{avg_duration:.1f}"
        metrics["Profit Factor"]      = "∞" if profit_factor >= 99 else f"{profit_factor:.2f}"
        metrics["Expectancy"]         = f"${expectancy:,.2f}"
        metrics["Gross Profit"]       = f"${gross_profit:,.2f}"
        metrics["Net Profit"]         = f"${net_profit:,.2f}"
        metrics["Total Fees"]         = f"${total_fees:,.2f}"
        metrics["Total Slippage"]     = f"${total_slippage:,.2f}"
        metrics["Slippage/Trade (%)"] = f"{slippage_pct:.3f}%"
        metrics["Avg Win"]            = f"${avg_win:,.2f}"
        metrics["Avg Loss"]           = f"${avg_loss:,.2f}"
        metrics["Best Trade"]         = f"${best_trade:,.2f}"
        metrics["Worst Trade"]        = f"${worst_trade:,.2f}"

        # ── Cost Ratio (T1-10 in SignalHive standard) ─────────────────────────
        # All-in cost ratio: (fees + slippage + borrow + funding) / gross_pnl
        # Uses actual gross_pnl from winning trades (SignalHive standard)
        if gross_win_sum > 0:
            all_in_costs = total_fees + total_slippage  # Would add borrow + funding here
            cost_ratio_all_in = all_in_costs / gross_win_sum
            metrics['Cost Ratio'] = f"{cost_ratio_all_in:.2%}"
        elif net_profit != 0:
            metrics['Cost Ratio'] = f"{total_fees / abs(net_profit):.2%}"
        else:
            metrics['Cost Ratio'] = "N/A"

    # --- Periodic Returns (Monthly / Yearly) ---
    if timestamps is not None:
        equity_series = pd.Series(equity, index=timestamps)

        if trades:
            trade_df = pd.DataFrame(trades)
            trade_df['time'] = pd.to_datetime(trade_df['time'])
            trade_df.set_index('time', inplace=True)
            monthly_fees = trade_df['fee'].resample('ME').sum()
            yearly_fees  = trade_df['fee'].resample('YE').sum()
        else:
            monthly_fees = pd.Series(dtype=float)
            yearly_fees  = pd.Series(dtype=float)

        initial_dt = timestamps[0] - pd.Timedelta(days=1)

        monthly_equity = equity_series.resample('ME').last()
        monthly_full   = pd.concat([pd.Series([initial_balance], index=[initial_dt]), monthly_equity])
        monthly_ret    = monthly_full.pct_change().dropna() * 100
        metrics["MONTHLY_RETURNS"] = {
            dt.strftime('%Y-%m'): {
                "return": f"{val:+.2f}%",
                "fees":   f"${monthly_fees.get(dt, 0):,.2f}"
            } for dt, val in monthly_ret.items()
        }

        yearly_equity = equity_series.resample('YE').last()
        yearly_full   = pd.concat([pd.Series([initial_balance], index=[initial_dt]), yearly_equity])
        yearly_ret    = yearly_full.pct_change().dropna() * 100
        metrics["YEARLY_RETURNS"] = {
            dt.strftime('%Y'): {
                "return": f"{val:+.2f}%",
                "fees":   f"${yearly_fees.get(dt, 0):,.2f}"
            } for dt, val in yearly_ret.items()
        }

        # ── Worst Daily Loss (T1-06) ─────────────────────────────────────────
        daily_eq    = equity_series.resample('1D').last().dropna()
        daily_ret_d = daily_eq.pct_change().dropna()
        if len(daily_ret_d) >= 2:
            metrics['Worst Daily Loss'] = f"{float(daily_ret_d.min()) * 100:.2f}%"

        # ── Monthly GTP (T2-06) ──────────────────────────────────────────────
        monthly_chg      = monthly_equity.diff().dropna()
        monthly_loss_abs = float(monthly_chg[monthly_chg < 0].abs().sum())
        if monthly_loss_abs > 0:
            metrics['Monthly GTP'] = f"{net_profit / monthly_loss_abs:.2f}"
        else:
            metrics['Monthly GTP'] = "∞"

        # ── Weekend vs Weekday Sharpe (T3-04) ────────────────────────────────
        if len(daily_ret_d) >= 20:
            wkday = daily_ret_d[daily_ret_d.index.dayofweek < 5]
            wkend = daily_ret_d[daily_ret_d.index.dayofweek >= 5]
            def _s(r):
                sd = float(r.std())
                return round(float(r.mean()) / sd * np.sqrt(365), 3) if sd > 0 and len(r) >= 5 else 0.0
            metrics['Weekday Sharpe'] = _s(wkday)
            metrics['Weekend Sharpe'] = _s(wkend)

        # ── Regime MDD (T3-03) ───────────────────────────────────────────────
        _REGIMES = {
            'bear_2022':  ('2022-01-01', '2022-12-31'),
            'range_2023': ('2023-01-01', '2023-12-31'),
            'bull_2024':  ('2024-01-01', '2024-12-31'),
        }
        regime_mdds = {}
        for _rname, (_rs, _re) in _REGIMES.items():
            try:
                _sl = equity_series.loc[_rs:_re]
            except Exception:
                continue
            if len(_sl) < 2:
                continue
            _pk = np.maximum.accumulate(_sl.values)
            _nz = _pk > 0
            _dd = float(np.min(np.where(_nz, (_sl.values - _pk) / _pk * 100.0, 0.0)))
            regime_mdds[_rname] = round(_dd, 2)
        if regime_mdds:
            metrics['Regime MDD'] = regime_mdds

    return metrics
