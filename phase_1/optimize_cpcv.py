"""This code is for training a reinforcement learning agent for trading cryptocurrencies using Optuna and Alpaca API.
It includes functions for setting up the environment, cross-validation, and training, as well as saving the best
performing agent.

print_config(): This function prints out the current configuration settings for the training.

set_Pandas_Timedelta(TIMEFRAME): This is a helper function that converts the time frame input to a pandas Timedelta
object.

save_best_agent(study, trial): This is a callback function that is called at the end of each trial, it checks if the
current trial is the best one, and if so, it copies the agent from the working directory to the results directory and
pickles the trial object.

sample_hyperparams(trial): This function samples the hyperparameters for the agent during the training process.

objective(trial, name_test, model_name, cwd, res_timestamp, gpu_id) : This function is used as the objective function
for the Optuna optimization. It sets up the environment and cross-validation for the agent training and returns the
final evaluation metric as the objective value.

optimize(name_test:str, model_name:str, gpu_id:str) : This function optimizes the agent training using Optuna by
calling the objective function and specifying the search space for the hyperparameters. It also includes a callback
function to save the best agent and logging of the results.

setup_CPCV(erl_params, tech_array, time_array, NUM_PATHS, K_TEST_GROUPS, TIMEFRAME): This function sets up the Purged
Combinatorial Cross-Validation for the agent training. It takes in parameters for the environment, technical
indicators, and time frame, and returns the cross-validation object to be used in the training.

back_test_paths_generator(data, y, cv, n_samples, n_total_groups, k_test_groups, prediction_times, evaluation_times,
verbose): This function generates the paths for backtesting of the agent. It takes in the data, labels,
cross-validation object, number of samples, and parameters for the paths and returns the is_test, paths,
and evaluation times.

class bcolors: : This class defines the color codes for the terminal output.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import argparse
import contextlib
import hashlib
import io
import json
import joblib
import optuna
import datetime
import pickle
import shutil
import os
import sys
from pathlib import Path

# ── Parallel split config ─────────────────────────────────────────────────────
# 2 of 14 cores — reduced to lower RAM pressure during SAC training
_N_PARALLEL_SPLITS = 2


# ── Split result cache ────────────────────────────────────────────────────────

def _params_hash(env_params, erl_params):
    """8-char hash that uniquely identifies a hyperparameter combination."""
    key = json.dumps({**env_params, **erl_params}, sort_keys=True, default=str)
    return hashlib.md5(key.encode()).hexdigest()[:8]


def _split_cache_file(split, env_params, erl_params, trial_cwd):
    """Path to the cache file for (hyperparams, split_index)."""
    cache_dir = Path(trial_cwd).parent / 'split_cache'
    ph = _params_hash(env_params, erl_params)
    return cache_dir / f'{ph}_s{split}.npz'


class _TrialProxy:
    """Picklable read-only view of an Optuna trial for use in child processes."""
    def __init__(self, trial):
        self.user_attrs = dict(trial.user_attrs)
        self.params     = dict(trial.params)
        self.number     = trial.number


def _run_split(split, train_indices, test_indices, trial_proxy,
               price_array, tech_array, env, model_name,
               env_params, erl_params, break_step, trial_cwd, gpu_id):
    """Run one CPCV split in its own directory — safe to call in parallel.

    Checks a persistent cache keyed by (hyperparams hash, split index) before
    training. If a prior run already completed this exact split, the result is
    loaded instantly and training is skipped. Results are written to cache on
    completion so future resumes can reuse them.
    """
    split_cwd  = trial_cwd + f'_s{split}'
    cache_file = _split_cache_file(split, env_params, erl_params, trial_cwd)

    # ── Cache hit: return immediately without re-training ──────────────────
    if cache_file.exists():
        try:
            data = np.load(cache_file)
            return (split,
                    float(data['sharpe_bot']),
                    float(data['sharpe_eqw']),
                    data['drl_rets'].tolist())
        except Exception:
            pass  # corrupted cache — fall through and re-train

    # ── Train ───────────────────────────────────────────────────────────────
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        sharpe_bot, sharpe_eqw, drl_rets_tmp = train_and_test(
            trial_proxy, price_array, tech_array, train_indices, test_indices,
            env, model_name, env_params, erl_params, break_step, split_cwd, gpu_id
        )
    sharpe_bot = 0.0 if np.isnan(float(sharpe_bot)) else float(sharpe_bot)
    sharpe_eqw = 0.0 if np.isnan(float(sharpe_eqw)) else float(sharpe_eqw)

    # ── Save to cache so future resumes skip this split ─────────────────────
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache_file,
                 sharpe_bot=np.float32(sharpe_bot),
                 sharpe_eqw=np.float32(sharpe_eqw),
                 drl_rets=np.array(drl_rets_tmp, dtype=np.float32))
    except Exception:
        pass

    return split, sharpe_bot, sharpe_eqw, drl_rets_tmp

from distutils.dir_util import copy_tree
from environment_Alpaca import CryptoEnvAlpaca
from environment_CCXT import CryptoEnvCCXT
from function_CPCV import *
from function_train_test import *
from config_main import *


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_config():
    print('\n' + bcolors.HEADER + '##### Launched hyperparameter optimization with CPCV  #####' + bcolors.ENDC + '\n')
    print('TIMEFRAME                  ', TIMEFRAME)
    print('TRAIN SAMPLES              ', no_candles_for_train)
    print('TRIALS NO.                 ', H_TRIALS)
    print('N                          ', N_GROUPS)
    print('K test groups              ', K_TEST_GROUPS)
    print('SPLITS                     ', NUMBER_OF_SPLITS)

    print('\n')
    print('TRAIN SAMPLES              ', no_candles_for_train)
    print('VAL_SAMPLES                ', no_candles_for_val)
    print('TRAIN_START_DATE           ', TRAIN_START_DATE)
    print('TRAIN_END_DATE             ', TRAIN_END_DATE)
    print('VAL_START_DATE             ', VAL_START_DATE)
    print('VAL_END_DATE               ', VAL_END_DATE, '\n')
    print('TICKER LIST                ', TICKER_LIST, '\n')
    res_timestamp = 'res_' + str(datetime.now().strftime("%Y-%m-%d__%H_%M_%S"))
    return res_timestamp


def set_Pandas_Timedelta(TIMEFRAME):
    timeframe_to_delta = {'1m': pd.Timedelta(minutes=1),
                          '5m': pd.Timedelta(minutes=5),
                          '10m': pd.Timedelta(minutes=10),
                          '30m': pd.Timedelta(minutes=30),
                          '1h': pd.Timedelta(hours=1),
                          '4h': pd.Timedelta(hours=4),
                          '1d': pd.Timedelta(days=1),
                          }
    if TIMEFRAME in timeframe_to_delta:
        return timeframe_to_delta[TIMEFRAME]
    else:
        raise ValueError('Timeframe not supported yet, please manually add!')


def save_best_agent(study, trial):
    # Skip if no trials have completed yet or if trial failed
    try:
        if len(study.trials) == 0:
            return
        if study.best_trial is None:
            return
        if study.best_trial.number != trial.number:
            return
    except (ValueError, AttributeError):
        # Handle case where no trials have completed yet or best_trial is not available
        return

    print('\n' + bcolors.OKGREEN + 'Found new best agent!' + bcolors.ENDC + '\n')

    # Copy agent from workdir and save in result folder
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    name_folder = trial.user_attrs['name_folder']
    from_directory = trial.user_attrs['trial_cwd']
    to_directory = os.path.join(project_root, 'train_results', name_folder, 'stored_agent')

    os.makedirs(to_directory, exist_ok=True)
    copy_tree(from_directory, to_directory)

    with open(os.path.join(project_root, 'train_results', name_folder, 'best_trial'), "wb") as handle:
        pickle.dump(trial, handle, protocol=pickle.HIGHEST_PROTOCOL)


def sample_hyperparams(trial):
    # Data-aware constraints to prevent buffer overflow
    # Calculate maximum viable batch size based on available data
    max_episode_steps = no_candles_for_train * 0.8  # Conservative estimate of usable data

    # Adjust target_step options based on actual data availability
    average_episode_step_min = min(no_candles_for_train * 0.6, max_episode_steps)
    target_step_options = [
        min(average_episode_step_min, max_episode_steps),
        min(round(1.5 * average_episode_step_min), max_episode_steps),
        min(2 * average_episode_step_min, max_episode_steps)
    ]

    sampled_erl_params = {
        # Sweet-spot LR — loud enough for neurons to update, not so loud they explode
        "learning_rate": trial.suggest_categorical("learning_rate", [1e-4, 2e-4, 3e-4]),
        # Large batch — smooths macro noise, agent sees the big picture
        "batch_size": trial.suggest_categorical("batch_size", [1024, 2048]),
        "gamma": trial.suggest_categorical("gamma", [0.85, 0.99, 0.999]),
        # Large network — needed to handle 5000-8700 input dims without bottleneck
        "net_dimension": trial.suggest_categorical("net_dimension", [1024, 2048]),
        "target_step": trial.suggest_categorical("target_step", target_step_options),
        "eval_time_gap": trial.suggest_categorical("eval_time_gap", [60]),
        "break_step": trial.suggest_categorical("break_step", [2e5, 3e5, 5e5])
    }

    # environment normalization and lookback
    sampled_env_params = {
        # Longer memory — macro trends (DXY, SPY, VIX) only make sense over days not 1 candle
        "lookback": trial.suggest_categorical("lookback", [30, 40, 50]),
        "norm_cash": trial.suggest_categorical("norm_cash", [2 ** -12]),
        "norm_stocks": trial.suggest_categorical("norm_stocks", [2 ** -8]),
        "norm_tech": trial.suggest_categorical("norm_tech", [2 ** -15]),
        # Higher reward scale — absolute Sharpe signal needs amplification to cut through noise
        "norm_reward": trial.suggest_categorical("norm_reward", [2 ** 0, 2 ** 2, 2 ** 4]),
        "norm_action": trial.suggest_categorical("norm_action", [10000]),
        "drawdown_weight": trial.suggest_categorical("drawdown_weight", [0.0, 0.05, 0.1, 0.2]),
        "jitter_weight": trial.suggest_categorical("jitter_weight", [0.0, 0.01, 0.05]),
        "holding_penalty": trial.suggest_categorical("holding_penalty", [0.0, 0.01, 0.05])
    }
    return sampled_erl_params, sampled_env_params


def set_pickle_attributes(trial, model_name, TIMEFRAME, TRAIN_START_DATE, TRAIN_END_DATE, VAL_START_DATE, VAL_END_DATE, TICKER_LIST, TECHNICAL_INDICATORS_LIST, name_folder, name_test, study):
    # user attributes for saving in the pickle model file later
    trial.set_user_attr("model_name", model_name)
    trial.set_user_attr("timeframe", TIMEFRAME)
    trial.set_user_attr("train_start_date", TRAIN_START_DATE)
    trial.set_user_attr("train_end_date", TRAIN_END_DATE)
    trial.set_user_attr("test_start_date", VAL_START_DATE)
    trial.set_user_attr("test_end_date", VAL_END_DATE)
    trial.set_user_attr("ticker_list", TICKER_LIST)
    trial.set_user_attr("technical_indicator_list", TECHNICAL_INDICATORS_LIST)
    trial.set_user_attr("name_folder", name_folder)
    trial.set_user_attr("name_test", name_test)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    joblib.dump(study, os.path.join(project_root, 'train_results', name_folder, 'study.pkl'))


def load_saved_data(TIMEFRAME, no_candles_for_train):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(project_root, 'data', TIMEFRAME + '_' + str(no_candles_for_train + no_candles_for_val))
    print('\nLOADING DATA FOLDER: ', data_folder, '\n')
    data_from_processor = pd.read_pickle(data_folder + '/data_from_processor')
    price_array = pd.read_pickle(data_folder + '/price_array')
    tech_array = pd.read_pickle(data_folder + '/tech_array')
    time_array = pd.read_pickle(data_folder + '/time_array')
    return data_from_processor, price_array, tech_array, time_array


def write_logs(name_folder, model_name, trial, cwd, erl_params, env_params, num_paths, n_total_groups, n_splits):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_logs = os.path.join(project_root, 'train_results', name_folder, 'logs.txt')
    with open(path_logs, 'a') as f:
        f.write('\n' + 'MODEL NAME: ' + model_name + '\n')
        f.write('TRIAL NUMBER: ' + str(trial.number) + '\n')
        f.write('CWD: ' + cwd + '\n')
        f.write(str(erl_params) + '\n')
        f.write(str(env_params) + '\n')
        f.write('\n' + 'TIME START OUTER: ' + str(datetime.now()) + '\n')

        f.write('\n######### CPCV Settings #########' + '\n')
        f.write("Paths  : " + str(num_paths) + '\n')
        f.write("N      : " + str(n_total_groups) + '\n')
        f.write("splits : " + str(n_splits) + '\n\n')
    return path_logs


def setup_CPCV(data_from_processor, erl_params, tech_array, time_array, NUM_PATHS, K_TEST_GROUPS, TIMEFRAME):
    # Set constants - Use CCXT environment for crypto trading
    env = CryptoEnvCCXT
    break_step = erl_params["break_step"]

    # Setup Purged CombinatorialCross-Validation
    num_paths = NUM_PATHS
    k_test_groups = K_TEST_GROUPS
    n_total_groups = num_paths + 1
    t_final = 10
    embargo_td = set_Pandas_Timedelta(TIMEFRAME) * t_final * 5
    n_splits = np.array(list(itt.combinations(np.arange(n_total_groups), k_test_groups))).reshape(-1, k_test_groups)
    n_splits = len(n_splits)
    cv = CombPurgedKFoldCV(n_splits=n_total_groups, n_test_splits=k_test_groups, embargo_td=embargo_td)

    # Set placeholder target variable
    data = pd.DataFrame(tech_array)
    data = data.set_index(time_array)
    data.drop(data.tail(t_final).index, inplace=True)
    y = pd.Series([0] * data_from_processor.shape[0])
    y = y.reindex(data.index)
    y = y.squeeze()

    # prediction and evaluation times
    prediction_times = pd.Series(data.index, index=data.index)
    evaluation_times = pd.Series(data.index, index=data.index)

    # Compute paths
    is_test, paths, _ = back_test_paths_generator(data, y, cv, data.shape[0], n_total_groups, k_test_groups,
                                                  prediction_times, evaluation_times, verbose=False)

    return cv, env, data, y, num_paths, paths, n_total_groups, n_splits, break_step, prediction_times, evaluation_times


def objective(trial, name_test, model_name, cwd, res_timestamp, gpu_id):

    # Set full name_folder
    name_folder = res_timestamp + '_' + name_test

    set_pickle_attributes(trial, model_name, TIMEFRAME, TRAIN_START_DATE, TRAIN_END_DATE, VAL_START_DATE, VAL_END_DATE,
                          TICKER_LIST, TECHNICAL_INDICATORS_LIST, name_folder, name_test, study)

    # Sample set of hyperparameters
    erl_params, env_params = sample_hyperparams(trial)

    # Each trial gets its own cwd so different net_dimensions don't collide on checkpoints
    trial_cwd = cwd + f'_t{trial.number}'
    trial.set_user_attr("trial_cwd", trial_cwd)

    # Load data from hard disk
    data_from_processor, price_array, tech_array, time_array = load_saved_data(TIMEFRAME, no_candles_for_train)

    # Validate hyperparameters against available data
    max_episode_length = price_array.shape[0] - env_params.get('lookback', 1) - 1

    # Additional validation for extreme cases
    if erl_params['batch_size'] > max_episode_length:
        print(f"Warning: batch_size ({erl_params['batch_size']}) > max_episode_length ({max_episode_length})")
        # Force compatible batch_size
        erl_params['batch_size'] = min(erl_params['batch_size'], max(max_episode_length // 2, 1))

    if erl_params['net_dimension'] > 2048 and max_episode_length < 1000:
        print(f"Warning: Large network ({erl_params['net_dimension']}) with limited data ({max_episode_length})")
        erl_params['net_dimension'] = min(erl_params['net_dimension'], 1024)

    # Setup Combinatorial Purged Cross-Validation
    cpcv, \
        env, \
        data, y, \
        num_paths, \
        paths, \
        n_total_groups, \
        n_splits, \
        break_step, \
        prediction_times, \
        evaluation_times = setup_CPCV(data_from_processor, erl_params, tech_array, time_array, NUM_PATHS, K_TEST_GROUPS,
                                      TIMEFRAME)

    # initiate logs for tracking behaviour during training
    path_logs = write_logs(name_folder, model_name, trial, cwd, erl_params, env_params, num_paths, n_total_groups,
                           n_splits)

    # CPCV Split function eval
    #######################################################################################################
    #######################################################################################################

    # CV loop — parallel across splits (n_jobs=_N_PARALLEL_SPLITS)
    trial_proxy = _TrialProxy(trial)
    splits_list = list(enumerate(
        cpcv.split(data, y, pred_times=prediction_times, eval_times=evaluation_times)))
    n_splits_total = len(splits_list)

    print(f'\n  Trial {trial.number} | {model_name.upper()} | {n_splits_total} splits × {int(erl_params["break_step"]):,} steps  ({_N_PARALLEL_SPLITS} workers)')
    print(f'  {"Split":<6}  {"Bot Sharpe":>10}  {"HODL Sharpe":>11}  {"Diff":>8}')
    print(f'  {"─"*6}  {"─"*10}  {"─"*11}  {"─"*8}')

    with open(path_logs, 'a') as f:
        f.write(f'PARALLEL SPLITS START ({_N_PARALLEL_SPLITS} workers): {datetime.now()}\n')

    split_results = joblib.Parallel(n_jobs=_N_PARALLEL_SPLITS, prefer='processes')(
        joblib.delayed(_run_split)(
            split, train_idx, test_idx, trial_proxy,
            price_array, tech_array, env, model_name,
            env_params, erl_params, break_step, trial_cwd, gpu_id
        )
        for split, (train_idx, test_idx) in splits_list
    )

    # Sort by split index (parallel results may arrive out of order)
    split_results.sort(key=lambda r: r[0])
    sharpe_list_bot   = [r[1] for r in split_results]
    sharpe_list_ewq   = [r[2] for r in split_results]
    drl_rets_val_list = [r[3] for r in split_results]

    # Print clean per-split table and write logs
    with open(path_logs, 'a') as f:
        for s_idx, s_bot, s_eqw, _ in split_results:
            diff = s_bot - s_eqw
            sign = '+' if diff >= 0 else ''
            print(f'  {s_idx:<6}  {s_bot:>10.4f}  {s_eqw:>11.4f}  {sign}{diff:>7.4f}')
            f.write('\nSPLIT: ' + str(s_idx) + '     # Optimizing for Sharpe ratio!\n')
            f.write('BOT:         ' + str(s_bot) + '\n')
            f.write('HODL:        ' + str(s_eqw) + '\n')
        f.write('PARALLEL SPLITS END: ' + str(datetime.now()) + '\n\n')

    # Consolidate best split model → trial_cwd (required by save_best_agent)
    # Pick the split whose (bot - hodl) excess Sharpe was highest
    best_split_idx = max(split_results, key=lambda r: r[1] - r[2])[0]
    best_split_cwd = trial_cwd + f'_s{best_split_idx}'
    if os.path.isdir(best_split_cwd):
        os.makedirs(trial_cwd, exist_ok=True)
        copy_tree(best_split_cwd, trial_cwd)

    # Delete all per-split working directories — each is ~500–950 MB and not needed after this point.
    # The best split's weights have been copied to trial_cwd above; all others are discarded.
    for s_idx, _, _, _ in split_results:
        split_path = trial_cwd + f'_s{s_idx}'
        if os.path.isdir(split_path):
            shutil.rmtree(split_path, ignore_errors=True)

    # Set trial user attrs once (same value every split, set once here)
    trial.set_user_attr("price_array", price_array)
    trial.set_user_attr("tech_array", tech_array)
    trial.set_user_attr("time_array", time_array)

    # Hyperparameter bjective function eval
    #######################################################################################################
    #######################################################################################################

    # Matrices
    trial.set_user_attr("drl_rets_val_list", drl_rets_val_list)

    # Interesting values
    trial.set_user_attr("sharpe_list_bot", sharpe_list_bot)
    trial.set_user_attr("sharpe_list_ewq", sharpe_list_ewq)
    trial.set_user_attr("paths", paths)

    avg_bot  = np.mean(sharpe_list_bot)
    avg_hodl = np.mean(sharpe_list_ewq)
    objective_val = avg_bot - avg_hodl
    sign = '+' if objective_val >= 0 else ''
    print(f'  {"─"*6}  {"─"*10}  {"─"*11}  {"─"*8}')
    print(f'  {"AVG":<6}  {avg_bot:>10.4f}  {avg_hodl:>11.4f}  {sign}{objective_val:>7.4f}  ← objective\n')

    with open(path_logs, 'a') as f:
        f.write('\nHYPERPARAMETER EVAL || SHARPE AVG BOT    :  ' + str(avg_bot) + '\n')
        f.write('HYPERPARAMETER EVAL || SHARPE AVG HODL     : ' + str(avg_hodl) + '\n')
        f.write('DIFFERENCE                                 : ' + str(objective_val) + '\n')
        f.write('\n' + 'TIME END OUTER: ' + str(datetime.now()) + '\n')

    return objective_val


# Optuna
#######################################################################################################

def optimize(name_test, model_name, gpu_id, resume_folder=None):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    name_test = f"{name_test}_CPCV_{model_name}_{TIMEFRAME}_{H_TRIALS}H_{round((no_candles_for_train + no_candles_for_val) / 1000)}k"
    cwd = os.path.join(project_root, 'train_results', 'cwd_tests', name_test)

    global study

    if resume_folder:
        # ── Resume mode: load existing study, continue in same result folder ──
        study_path = os.path.join(project_root, 'train_results', resume_folder, 'study.pkl')
        if not os.path.exists(study_path):
            raise FileNotFoundError(f'study.pkl not found in {resume_folder}')
        print(f'\n▶  Resuming from: {resume_folder}')

        # Extract original timestamp so new trials write to the same folder
        # folder = res_2026-05-15__11_21_43_model_CPCV_ppo_4h_50H_15k
        # name_test = model_CPCV_ppo_4h_50H_15k  → strip it to get timestamp
        res_timestamp = resume_folder.replace('_' + name_test, '')
        path = os.path.join(project_root, 'train_results', resume_folder)

        study_corrupted = False
        try:
            study = joblib.load(study_path)
        except Exception as e:
            print(f'   ⚠  study.pkl corrupted ({e.__class__.__name__}: {e})')
            print(f'   ⚠  Starting a fresh Optuna study — trial history lost, but stored_agent weights are preserved.')
            study_corrupted = True

        if study_corrupted:
            sampler = optuna.samplers.TPESampler(multivariate=True, seed=SEED_CFG)
            study = optuna.create_study(
                study_name=None,
                direction='maximize',
                sampler=sampler,
                pruner=optuna.pruners.HyperbandPruner(
                    min_resource=1,
                    max_resource=300,
                    reduction_factor=3
                )
            )
            completed = 0
            remaining = H_TRIALS
        else:
            # Re-queue stuck RUNNING trials with same hyperparams, then mark as FAILED.
            # The cache in _run_split() will skip any splits that already completed,
            # so only the missing splits are re-trained — no work is lost.
            from optuna.trial import TrialState
            for t in study.trials:
                if t.state.name == 'RUNNING':
                    ph = _params_hash(t.params, {})  # t.params is already the merged flat dict
                    split_cache_dir = Path(cwd).parent / 'split_cache'
                    cached = sum(1 for s in range(10)
                                 if (split_cache_dir / f'{ph}_s{s}.npz').exists())
                    try:
                        study.enqueue_trial(t.params)
                        print(f'   Re-queued trial #{t.number} ({cached}/10 splits cached — those will be skipped)')
                    except Exception:
                        pass
                    try:
                        study._storage.set_trial_state_values(t._trial_id, state=TrialState.FAIL, values=None)
                        print(f'   Marked stuck trial #{t.number} as FAILED')
                    except Exception:
                        pass

            completed = sum(1 for t in study.trials if t.state.name == 'COMPLETE')
            remaining = max(0, H_TRIALS - completed)
        print(f'   Completed trials : {completed}')
        print(f'   Remaining trials : {remaining}\n')
        if remaining == 0:
            print('All trials already complete. Nothing to do.')
            return
    else:
        # ── Fresh run ──
        res_timestamp = print_config()
        path = os.path.join(project_root, 'train_results', f'{res_timestamp}_{name_test}')
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'logs.txt'), "w") as f:
            f.write(f"##################################  || {model_name} || ##################################")

        sampler = optuna.samplers.TPESampler(multivariate=True, seed=SEED_CFG)
        study = optuna.create_study(
            study_name=None,
            direction='maximize',
            sampler=sampler,
            pruner=optuna.pruners.HyperbandPruner(
                min_resource=1,
                max_resource=300,
                reduction_factor=3
            )
        )
        remaining = H_TRIALS

    def obj_with_argument(trial):
        return objective(trial, name_test, model_name, cwd, res_timestamp, gpu_id)

    study.optimize(
        obj_with_argument,
        n_trials=remaining,
        catch=(ValueError, RuntimeError, FileNotFoundError),
        callbacks=[save_best_agent]
    )
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    joblib.dump(study, os.path.join(project_root, 'train_results', f"{res_timestamp}_{name_test}", 'study.pkl'))

# Main
#######################################################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CPCV hyperparameter optimization')
    parser.add_argument('--ppo', action='store_true', help='Train PPO only')
    parser.add_argument('--sac', action='store_true', help='Train SAC only')
    parser.add_argument('--gpu', type=int, default=0, help='GPU id (default: 0)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from existing result folder (e.g. res_2026-05-15__11_21_43_model_CPCV_ppo_4h_50H_15k)')
    args = parser.parse_args()

    # Default: train both unless one flag is explicitly set
    run_ppo = args.ppo or (not args.ppo and not args.sac)
    run_sac = args.sac or (not args.ppo and not args.sac)

    gpu_id    = args.gpu
    name_test = 'model'

    print('\nStarting CPCV optimization')
    print('gpu_id:   ', gpu_id)
    print('run PPO:  ', run_ppo)
    print('run SAC:  ', run_sac, '\n')

    if run_ppo:
        print('── Training PPO ──')
        optimize(name_test, 'ppo', gpu_id, resume_folder=args.resume)

    if run_sac:
        print('── Training SAC ──')
        optimize(name_test, 'sac', gpu_id, resume_folder=args.resume)
