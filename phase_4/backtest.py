"""
This script contains a set of functions for loading and processing data for trading.

It contains the following functions:

load_validated_model: Loads the best trial from the pickle file in the specified directory and returns the best trial's attributes.
download_CVIX: Downloads the CVIX dataframe from Yahoo finance and returns it.
load_and_process_data: loads and process the trade data from the specified data folder and returns the data.

After that, the large loop analyzes every result by creating an instance of an Alpaca environment and checking
what the model would do through the environment using the new trading data

Finally, the resulting backtests are analyzes for performance a performance metric per benchmark (EQW, S&P BCI) plus
all the input DRL agents are analyzed.

"""


import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import json
import pickle
import matplotlib.dates as mdates
from datetime import datetime

from config_main import *
from function_finance_metrics import *
from environment_CCXT import CryptoEnvCCXT
from drl_agents.elegantrl_models import DRLAgent as DRLAgent_erl

SLIPPAGE_PCT = 0.0005  # 0.05% per side — bid-ask spread + market impact (BTC/ETH spot)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_validated_model(result):

    with open(os.path.join(_PROJECT_ROOT, 'train_results', result, 'best_trial'), 'rb') as handle:
        best_trial = pickle.load(handle)

    print('BEST TRIAL: ', best_trial.number)
    timeframe = best_trial.user_attrs['timeframe']
    ticker_list = best_trial.user_attrs['ticker_list']
    technical_ind = best_trial.user_attrs['technical_indicator_list']
    net_dim = best_trial.params['net_dimension']
    model_name = best_trial.user_attrs['model_name']

    print('\nMODEL_NAME: ', model_name)
    print(best_trial.params)
    print(timeframe)

    name_test = best_trial.user_attrs['name_test']

    env_params = {
        "lookback": best_trial.params['lookback'],
        "norm_cash": best_trial.params['norm_cash'],
        "norm_stocks": best_trial.params['norm_stocks'],
        "norm_tech": best_trial.params['norm_tech'],
        "norm_reward": best_trial.params['norm_reward'],
        "norm_action": best_trial.params['norm_action'],
        "drawdown_weight":   best_trial.params.get('drawdown_weight', 0.0),
        "jitter_weight":     best_trial.params.get('jitter_weight', 0.0),
        "holding_penalty":   best_trial.params.get('holding_penalty', 0.0)
    }
    return env_params, net_dim, timeframe, ticker_list, technical_ind, name_test, model_name


def download_external_indicator(trade_start_date, trade_end_date):
    """
    Download external indicator data (CVIX alternative) from Binance or create dummy data.
    This function replaces CVOL-USD data which was previously fetched from Yahoo Finance.
    """
    try:
        # Try to get Bitcoin dominance index or another market indicator from Binance
        # For now, create dummy data that mimics volatility patterns

        # Create time range for the trading period
        start_date = pd.to_datetime(trade_start_date[:10])
        end_date = pd.to_datetime(trade_end_date[:10])
        time_range = pd.date_range(start=start_date, end=end_date, freq='5Min')

        # Generate realistic-looking indicator data (simulating volatility index)
        np.random.seed(42)  # For reproducibility
        base_value = 50.0

        # Create more realistic patterns
        values = []
        current_value = base_value

        for i in range(len(time_range)):
            # Random walk with mean reversion
            change = np.random.normal(0, 2)  # Small random changes
            mean_reversion = (base_value - current_value) * 0.01  # Gentle pull to mean

            current_value = current_value + change + mean_reversion
            current_value = np.clip(current_value, 20, 150)  # Keep in reasonable range

            values.append(current_value)

        indicator_series = pd.Series(values, index=time_range)
        indicator_series.name = 'close'

        print("Using dummy external indicator data (CVIX replacement)")
        return indicator_series.to_frame()

    except Exception as e:
        print(f"Error creating external indicator data: {e}")
        # Fallback: flat values
        time_range = pd.date_range(start=trade_start_date[:10],
                                  end=trade_end_date[:10],
                                  freq='5Min')
        dummy_series = pd.Series(50.0, index=time_range, name='close')
        return dummy_series.to_frame()


def load_and_process_data(TIMEFRAME, trade_start_date, trade_end_date):
    data_folder = os.path.join(_PROJECT_ROOT, 'data', 'trade_data',
                               f'{TIMEFRAME}_{str(trade_start_date[2:10])}_{str(trade_end_date[2:10])}')
    print(f'\nLOADING DATA FOLDER: {data_folder}\n')
    data_from_processor = pd.read_pickle(data_folder + '/data_from_processor')
    price_array = pd.read_pickle(data_folder + '/price_array')
    tech_array = pd.read_pickle(data_folder + '/tech_array')
    time_array = pd.read_pickle(data_folder + '/time_array')

    # Load external indicator data (could be CVIX, volatility, etc.)
    external_data = download_external_indicator(trade_start_date, trade_end_date)
    time_series = time_array.to_series()
    time_series.name = 'time'
    external_data = pd.merge(time_series, external_data, left_index=True, right_index=True, how='left')
    indicator_array = external_data['close'].values
    indicator_array_growth = np.diff(indicator_array)

    return data_from_processor, price_array, tech_array, time_array, indicator_array, indicator_array_growth


# Inputs
#######################################################################################################
#######################################################################################################
#######################################################################################################

print('TRADE_START_DATE             ', trade_start_date)
print('TRADE_END_DATE               ', trade_end_date, '\n')

# ── Interactive result selection ───────────────────────────────────────────────
_results_dir = os.path.join(_PROJECT_ROOT, 'train_results')
_available = sorted([
    d for d in os.listdir(_results_dir)
    if os.path.isdir(os.path.join(_results_dir, d))
    and os.path.isfile(os.path.join(_results_dir, d, 'best_trial'))
    and d != 'cwd_tests'
])

if len(sys.argv) > 1:
    pickle_results = [sys.argv[1]]
else:
    print('Available results with a saved best_trial:\n')
    for i, r in enumerate(_available):
        print(f'  [{i}] {r}')
    print()
    _choice = input('Enter number (or full folder name): ').strip()
    if _choice.isdigit() and int(_choice) < len(_available):
        pickle_results = [_available[int(_choice)]]
    else:
        pickle_results = [_choice]

print(f'\nLoading result: {pickle_results[0]}\n')

# Execution
#######################################################################################################
#######################################################################################################

drl_cumrets_list = []
model_names_list = []

_, _, timeframe, ticker_list, technical_ind, _, _ = load_validated_model(pickle_results[0])
data_from_processor, price_array, tech_array, time_array, indicator_array, indicator_array_growth = load_and_process_data(TIMEFRAME, trade_start_date, trade_end_date)
time_array_full = time_array  # save full reference before loop slices it

for count, result in enumerate(pickle_results):
    env_params, net_dim, timeframe, ticker_list, technical_ind, name_test, model_name = load_validated_model(result)
    model_names_list.append(model_name)
    cwd = os.path.join(_PROJECT_ROOT, 'train_results', result, 'stored_agent')

    data_config = {
        "cvix_array": indicator_array,
        "cvix_array_growth": indicator_array_growth,
        "time_array": time_array,
        "price_array": price_array,
        "tech_array": tech_array,
        "if_train": False,
    }

    # Use CCXT environment for crypto trading
    env = CryptoEnvCCXT
    env_instance = env(config=data_config,
                       env_params=env_params,
                       if_log=True,
                       exchange_name='binance'
                       )

    account_value_erl = DRLAgent_erl.DRL_prediction(
        model_name=model_name,
        cwd=cwd,
        net_dimension=net_dim,
        environment=env_instance,
        gpu_id=0
    )

    # Correct slicing (due to DRL start/end)
    lookback = env_params['lookback']
    indice_start = lookback - 1
    indice_end = len(price_array) - lookback
    time_array = time_array[indice_start:indice_end]

    # Slice indicator array
    if count == 0:
        indicator_array = indicator_array[indice_start:indice_end]
        indicator_array_growth = indicator_array_growth[indice_start:indice_end]

    # Compute Sharpe's of each coin
    account_value_eqw, ewq_rets, eqw_cumrets = compute_eqw(price_array, indice_start, indice_end)

    # Compute annualization factor
    data_points_per_year = compute_data_points_per_year(timeframe)
    dataset_size = np.shape(ewq_rets)[0]
    factor = data_points_per_year / dataset_size

    # Compute DRL rets
    account_value_erl = np.array(account_value_erl)
    drl_rets = (account_value_erl[1:] - account_value_erl[:-1]) / account_value_erl[:-1]
    drl_cumrets = [x / account_value_erl[0] - 1 for x in account_value_erl]
    drl_cumrets_list.append(drl_cumrets)

    # Compute metrics per pickle result
    #######################################################################################################

    # Only compute consistent metrics once
    if count == 0:
        # S&P index data removed - not available for Binance setup
        print("S&P Broad Crypto Market Index skipped - not available for Binance setup")

        # Write buy-and-hold strategy
        eqw_annual_ret, eqw_annual_vol, eqw_sharpe_rat, eqw_vol = aggregate_performance_array(np.array(ewq_rets),
                                                                                                 factor)
        write_metrics_to_results('Buy-and-Hold',
                                 os.path.join(_PROJECT_ROOT, 'plots_and_metrics', 'test_metrics.txt'),
                                 eqw_cumrets,
                                 eqw_annual_ret,
                                 eqw_annual_vol,
                                 eqw_sharpe_rat,
                                 eqw_vol,
                                 'a'
                                 )

    # Then compute the actual metrics from the DRL agents
    drl_annual_ret, drl_annual_vol, drl_sharpe_rat, drl_vol = aggregate_performance_array(np.array(drl_rets), factor)
    write_metrics_to_results(model_name,
                             os.path.join(_PROJECT_ROOT, 'plots_and_metrics', 'test_metrics.txt'),
                             drl_cumrets,
                             drl_annual_ret,
                             drl_annual_vol,
                             drl_sharpe_rat,
                             drl_vol,
                             'a'
                             )

    # ── Dashboard data generation ───────────────────────────────────────────────
    erl_arr = np.array(account_value_erl, dtype=float)
    eqw_arr = np.array(account_value_eqw, dtype=float)

    # Pct returns for sortino & win rate
    drl_pct = np.diff(erl_arr) / erl_arr[:-1]
    hodl_pct = np.diff(eqw_arr) / eqw_arr[:-1]

    drl_sortino_val  = float(sortino(drl_pct,  target_rtn=0, factor=data_points_per_year, log=False))
    hodl_sortino_val = float(sortino(hodl_pct, target_rtn=0, factor=data_points_per_year, log=False))

    drl_mdd_val  = float(max_drawdown(pd.Series(erl_arr)))
    hodl_mdd_val = float(max_drawdown(pd.Series(eqw_arr[1:])))

    drl_dd_curve  = drawdown(pd.Series(erl_arr)).tolist()
    hodl_dd_curve = drawdown(pd.Series(eqw_arr[1:])).tolist()

    nonzero = drl_pct[drl_pct != 0]
    win_rate_val = float(np.sum(nonzero > 0) / len(nonzero) * 100) if len(nonzero) > 0 else 0.0

    # Build trade list and round-trip trades
    all_trades = []
    round_trips = []
    active_positions = {}  # {asset_name: {amount, cost_basis, entry_time, fees_paid}}

    for entry in env_instance.step_log:
        tidx = entry['time_idx']
        try:
            ts = str(time_array_full.iloc[tidx]) if hasattr(time_array_full, 'iloc') else str(time_array_full[tidx])
        except Exception:
            ts = str(tidx)

        for t in entry['trades']:
            ai = t['asset_idx']
            asset_name = ticker_list[ai] if ai < len(ticker_list) else f"Asset_{ai}"
            side = t['side']
            amount = float(t['amount'])
            raw_price = float(t['price'])
            # Slippage adverse to direction: buys fill higher, sells fill lower
            slip_dir = 1 if side == 'BUY' else -1
            price = raw_price * (1.0 + SLIPPAGE_PCT * slip_dir)
            slippage_usd = amount * abs(price - raw_price)
            value_usd = amount * price
            fee_usd = value_usd * 0.001  # 0.1% taker fee

            all_trades.append({
                'time': ts, 'side': side, 'asset': asset_name,
                'amount': round(amount, 8),
                'raw_price': round(raw_price, 2),
                'price': round(price, 2),
                'slippage_usd': round(slippage_usd, 4),
                'slippage_pct': SLIPPAGE_PCT * 100,
                'value_usd': round(value_usd, 2),
                'fee_usd': round(fee_usd, 2)
            })

            # Round trip logic
            if asset_name not in active_positions:
                active_positions[asset_name] = {'amount': 0.0, 'cost_basis': 0.0, 'entry_time': ts,
                                                'fees_paid': 0.0, 'slippage_paid': 0.0}

            pos = active_positions[asset_name]

            if side == 'BUY':
                if pos['amount'] == 0:
                    pos['entry_time'] = ts
                # Weighted average cost basis (using slipped price)
                pos['cost_basis'] = (pos['cost_basis'] * pos['amount'] + value_usd) / (pos['amount'] + amount)
                pos['amount'] += amount
                pos['fees_paid'] += fee_usd
                pos['slippage_paid'] += slippage_usd
            else:  # SELL
                if pos['amount'] > 0:
                    sold_amount = min(pos['amount'], amount)
                    gross_profit_usd = (price - pos['cost_basis']) * sold_amount
                    total_position_fees = (sold_amount / pos['amount'] * pos['fees_paid']) + fee_usd
                    total_position_slippage = (sold_amount / pos['amount'] * pos['slippage_paid']) + slippage_usd
                    net_profit_usd = gross_profit_usd - total_position_fees

                    profit_pct = (price / pos['cost_basis'] - 1) * 100 if pos['cost_basis'] > 0 else 0

                    try:
                        d1 = datetime.strptime(pos['entry_time'], '%Y-%m-%d %H:%M:%S')
                        d2 = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                        duration = str(d2 - d1)
                    except:
                        duration = "N/A"

                    round_trips.append({
                        'asset': asset_name,
                        'entry_time': pos['entry_time'],
                        'exit_time': ts,
                        'entry_price': round(pos['cost_basis'], 2),
                        'exit_price': round(price, 2),
                        'gross_profit_usd': round(gross_profit_usd, 2),
                        'net_profit_usd': round(net_profit_usd, 2),
                        'total_fees_usd': round(total_position_fees, 2),
                        'total_slippage_usd': round(total_position_slippage, 4),
                        'slippage_pct': SLIPPAGE_PCT * 100,
                        'profit_pct': round(profit_pct, 2),
                        'duration': duration
                    })
                    
                    # Update remaining position fees and slippage
                    remaining_ratio = (pos['amount'] - sold_amount) / pos['amount'] if pos['amount'] > 0 else 0
                    pos['fees_paid'] *= remaining_ratio
                    pos['slippage_paid'] *= remaining_ratio
                    pos['amount'] -= sold_amount

                    if pos['amount'] <= 1e-10:
                        pos['amount'] = 0.0
                        pos['cost_basis'] = 0.0
                        pos['fees_paid'] = 0.0
                        pos['slippage_paid'] = 0.0

    # Per-coin holding value and price curves
    n_coins = price_array.shape[1]
    coin_value_series = [[] for _ in range(n_coins)]
    coin_price_series = [[] for _ in range(n_coins)]

    # Slice price array to match test period
    lookback = env_params['lookback']
    indice_start = lookback - 1
    indice_end = len(price_array) - lookback
    price_array_test = price_array[indice_start:indice_end]

    for entry in env_instance.step_log:
        cv = entry.get('coin_values', [0.0] * n_coins)
        for ci in range(n_coins):
            coin_value_series[ci].append(float(cv[ci]) if ci < len(cv) else 0.0)

    initial_cap = 1_000_000
    per_coin_cumrets = []
    for ci in range(n_coins):
        vals = np.array(coin_value_series[ci])
        base = initial_cap / n_coins
        per_coin_cumrets.append((vals / base - 1).tolist())
        coin_price_series[ci] = price_array_test[:, ci].tolist()

    # Align lengths
    n = min(len(time_array), len(drl_cumrets), len(eqw_cumrets) - 1, len(drl_dd_curve), len(hodl_dd_curve))
    times_str = [str(t) for t in time_array[:n]]

    # Monthly/Yearly Returns Calculation
    periodic_returns = {"monthly": {"labels": [], "values": []}, "yearly": {"labels": [], "values": []}}
    try:
        df_periodic = pd.DataFrame({
            'timestamp': pd.to_datetime(time_array[:n]),
            'value': erl_arr[:n]
        }).set_index('timestamp')
        
        monthly_vals = df_periodic['value'].resample('ME').last()
        yearly_vals = df_periodic['value'].resample('YE').last()
        
        start_cap = erl_arr[0]
        if not monthly_vals.empty:
            m_rets = monthly_vals.pct_change().fillna(monthly_vals.iloc[0]/start_cap - 1) * 100
            periodic_returns["monthly"] = {
                "labels": m_rets.index.strftime('%b %Y').tolist(),
                "values": [round(float(x), 2) for x in m_rets.values]
            }
        
        if not yearly_vals.empty:
            y_rets = yearly_vals.pct_change().fillna(yearly_vals.iloc[0]/start_cap - 1) * 100
            periodic_returns["yearly"] = {
                "labels": y_rets.index.strftime('%Y').tolist(),
                "values": [round(float(x), 2) for x in y_rets.values]
            }
    except Exception as e:
        print(f"⚠️ Warning: Could not calculate periodic returns: {e}")

    # Advanced Trading Metrics Calculation
    wins = [t['net_profit_usd'] for t in round_trips if t['net_profit_usd'] > 0]
    losses = [abs(t['net_profit_usd']) for t in round_trips if t['net_profit_usd'] < 0]
    
    # Correct Gross totals
    gross_profit_sum = sum(t['gross_profit_usd'] for t in round_trips if t['gross_profit_usd'] > 0)
    gross_loss_sum = sum(abs(t['gross_profit_usd']) for t in round_trips if t['gross_profit_usd'] < 0)
    
    trade_win_rate = (len(wins) / len(round_trips) * 100) if round_trips else 0.0
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    
    # Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
    expectancy = (trade_win_rate/100 * avg_win) - ((1 - trade_win_rate/100) * avg_loss)
    
    # Max Consecutive Wins/Losses
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for t in round_trips:
        if t['net_profit_usd'] > 0:
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        else:
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)

    # TRUE Recovery Factor & MDD USD Calculation
    vals_series = pd.Series(erl_arr)
    rolling_peak = vals_series.cummax()
    drawdowns_usd = rolling_peak - vals_series
    max_drawdown_usd = drawdowns_usd.max()
    
    total_net_profit = erl_arr[-1] - erl_arr[0]
    recovery_factor = total_net_profit / max_drawdown_usd if max_drawdown_usd > 0 else (total_net_profit if total_net_profit > 0 else 0.0)
    calmar_ratio = (drl_annual_ret / abs(drl_mdd_val)) if drl_mdd_val != 0 else 0.0

    # Avg Duration Calculation
    durations = []
    for t in round_trips:
        try:
            d_str = t['duration']
            if 'day' in d_str:
                days = int(d_str.split(' day')[0])
                time_part = d_str.split(', ')[1]
            else:
                days = 0
                time_part = d_str
            h, m, s = map(float, time_part.split(':'))
            durations.append(days * 24 + h + m/60)
        except: continue
    avg_duration_hours = np.mean(durations) if durations else 0.0

    total_fees = sum(t['fee_usd'] for t in all_trades)

    advanced_metrics = {
        "account": {
            "initial_balance": round(float(erl_arr[0]), 2),
            "final_balance": round(float(erl_arr[-1]), 2),
            "net_profit": round(float(total_net_profit), 2),
            "gross_profit": round(float(gross_profit_sum), 2),
            "gross_loss": round(float(gross_loss_sum), 2),
            "total_fees": round(float(total_fees), 2)
        },
        "efficiency": {
            "profit_factor": round(float(gross_profit_sum / gross_loss_sum) if gross_loss_sum > 0 else 1.0, 2),
            "expectancy": round(float(expectancy), 2),
            "calmar_ratio": round(float(calmar_ratio), 2),
            "recovery_factor": round(float(recovery_factor), 2),
            "sharpe": round(float(drl_sharpe_rat), 4),
            "sortino": round(float(drl_sortino_val), 4)
        },
        "trades": {
            "total_trades": len(round_trips),
            "win_rate": round(float(trade_win_rate), 1),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "best_trade": round(float(max(wins)) if wins else 0.0, 2),
            "worst_trade": round(float(-max(losses)) if losses else 0.0, 2),
            "max_consec_wins": max_consec_wins,
            "max_consec_losses": max_consec_losses,
            "avg_duration_hours": round(float(avg_duration_hours), 1)
        }
    }

    dashboard_data = {
        "metadata": {
            "result_name": result,
            "model_name": model_name,
            "tickers": list(ticker_list),
            "timeframe": timeframe,
            "trade_start": str(trade_start_date)[:10],
            "trade_end": str(trade_end_date)[:10],
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "initial_capital": 1_000_000
        },
        "metrics": {
            "drl": {
                "cumulative_return": round(float(drl_cumrets[-1]) * 100, 2),
                "annual_return": round(float(drl_annual_ret) * 100, 4),
                "annual_vol": round(float(drl_annual_vol) * 100, 4),
                "sharpe": round(float(drl_sharpe_rat), 4),
                "sortino": round(float(drl_sortino_val), 4),
                "mdd": round(drl_mdd_val * 100, 2),
                "mdd_usd": round(float(max_drawdown_usd), 2),
                "win_rate": round(float(trade_win_rate), 1), # SYNCED to Trade-based
                "total_trades": len(round_trips) # SYNCED to Round-trips
            },
            "hodl": {
                "cumulative_return": round(float(eqw_cumrets[-1]) * 100, 2),
                "annual_return": round(float(eqw_annual_ret) * 100, 4),
                "annual_vol": round(float(eqw_annual_vol) * 100, 4),
                "sharpe": round(float(eqw_sharpe_rat), 4),
                "sortino": round(hodl_sortino_val, 4),
                "mdd": round(hodl_mdd_val * 100, 2)
            }
        },
        "advanced": advanced_metrics,
        "equity": {
            "times": times_str,
            "drl":  [round(float(x), 6) for x in drl_cumrets[:n]],
            "hodl": [round(float(x), 6) for x in eqw_cumrets[1:n+1]],
            "coins": {
                ticker_list[ci]: [round(float(x), 6) for x in per_coin_cumrets[ci][:n]]
                for ci in range(n_coins)
            },
            "prices": {
                ticker_list[ci]: [round(float(x), 4) for x in coin_price_series[ci][:n]]
                for ci in range(n_coins)
            }
        },
        "drawdown": {
            "times": times_str,
            "drl":  [round(float(x), 6) for x in drl_dd_curve[:n]],
            "hodl": [round(float(x), 6) for x in hodl_dd_curve[:n]]
        },
        "periodic": periodic_returns,
        "trades": all_trades,
        "round_trips": round_trips,
        "trade_returns": [t['profit_pct'] / 100 for t in round_trips]
    }

    _DASH_DIR = os.path.join(_PROJECT_ROOT, 'phase_4', 'dashboard')
    os.makedirs(_DASH_DIR, exist_ok=True)
    with open(os.path.join(_DASH_DIR, 'data.js'), 'w') as _f:
        _f.write('window.BACKTEST_DATA = ')
        json.dump(dashboard_data, _f, indent=2, default=str)
        _f.write(';\n')
    print(f"✅ Dashboard data → {_DASH_DIR}/data.js")
    print(f"   Open phase_4/dashboard/index.html in your browser.\n")

    # Hold out of loop only add once
    #######################################################################################################

# Plot
#######################################################################################################
#######################################################################################################

drl_rets_array = np.transpose(np.vstack(drl_cumrets_list))

# Align all series to the length of time_array (lookback offset can cause mismatches)
n_plot = len(time_array)
eqw_plot = np.array(eqw_cumrets[1:])[:n_plot]
drl_plot  = drl_rets_array[:n_plot, :]
ind_plot  = indicator_array[:n_plot]

# General 1
plt.rcParams.update({'font.size': 22})
plt.figure(dpi=300)
f, ax1 = plt.subplots(figsize=(20, 8))

# Plot returns
line_width = 2
ax1.plot(time_array, eqw_plot, linewidth=line_width, label='Equal-weight', color='blue')

for i in range(np.shape(drl_plot)[1]):
    ax1.plot(time_array, drl_plot[:, i], label=model_names_list[i], linewidth=line_width)
ax1.legend(frameon=False, ncol=len(model_names_list) + 1, loc='upper left', bbox_to_anchor=(0, 1.11))
ax1.patch.set_edgecolor('black')
ax1.patch.set_linewidth(3)
ax1.grid()

# Plot External Indicator
ax2 = ax1.twinx()
ax2.plot(time_array, ind_plot, linewidth=4, label='External Indicator', color='black', linestyle='dashed', alpha=0.4)
ax2.legend(frameon=False, loc='upper right', bbox_to_anchor=(0.7, 1.17))
ax2.patch.set_edgecolor('black')
ax2.patch.set_linewidth(3)
ax2.set_ylabel('External Indicator')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=8))
ax1.set_ylabel('Cumulative return')
plt.xlabel('Date')
plt.legend()
plt.savefig(os.path.join(_PROJECT_ROOT, 'plots_and_metrics', 'test_cumulative_return.png'), bbox_inches='tight')
ax2.patch.set_edgecolor('black')
ax2.patch.set_linewidth(3)
ax2.set_ylabel('External Indicator')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=8))
ax1.set_ylabel('Cumulative return')
plt.xlabel('Date')
plt.legend()
plt.savefig(os.path.join(_PROJECT_ROOT, 'plots_and_metrics', 'test_derivative_external_indicator.png'), bbox_inches='tight')