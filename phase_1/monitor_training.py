"""
Training progress monitor — run this while optimize_cpcv.py is training.

Usage:
    ./venv/bin/python phase_1/monitor_training.py
    ./venv/bin/python phase_1/monitor_training.py --refresh 10

Power/thermal notes (M4 Max):
    Die temperatures are not exposed by powermetrics on Apple Silicon.
    CPU/GPU power draw and thermal pressure are shown instead.
    Requires passwordless sudo for powermetrics (/etc/sudoers.d/powermetrics).
"""

import re
import sys
import time
import joblib
import argparse
import threading
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CWD_TESTS    = _PROJECT_ROOT / 'train_results' / 'cwd_tests'
_RESULTS_DIR  = _PROJECT_ROOT / 'train_results'

BAR_WIDTH = 22

# ── Shared thermal state (updated by background thread) ──────────────────────
_thermal = {
    'cpu_power_w':      None,   # Watts
    'gpu_power_w':      None,   # Watts
    'combined_power_w': None,   # Watts (CPU + GPU + ANE)
    'gpu_freq_mhz':     None,   # MHz
    'pressure':         None,   # Nominal / Moderate / Heavy / Critical
    'cpu_pct':          None,   # % from psutil
    'available':        False,  # True once powermetrics starts producing data
}
_thermal_lock = threading.Lock()


def _parse_powermetrics_line(line):
    """Parse one line of powermetrics text output into _thermal dict updates."""
    updates = {}

    # M4 Max format: "Current pressure level: Nominal"
    m = re.search(r'Current pressure level[:\s]+(\w+)', line, re.I)
    if m:
        updates['pressure'] = m.group(1).capitalize()

    m = re.search(r'CPU Power[:\s]+([\d.]+)\s*mW', line, re.I)
    if m:
        updates['cpu_power_w'] = float(m.group(1)) / 1000

    # Exclude "Combined Power" line — match only the standalone GPU Power line
    m = re.search(r'^GPU Power[:\s]+([\d.]+)\s*mW', line, re.I)
    if m:
        updates['gpu_power_w'] = float(m.group(1)) / 1000

    # Combined Power (CPU + GPU + ANE): best single proxy for total chip heat
    m = re.search(r'Combined Power[^:]*[:\s]+([\d.]+)\s*mW', line, re.I)
    if m:
        updates['combined_power_w'] = float(m.group(1)) / 1000

    # M4 Max: "GPU HW active frequency: 1495 MHz"
    m = re.search(r'GPU HW active frequency[:\s]+([\d.]+)\s*MHz', line, re.I)
    if m:
        updates['gpu_freq_mhz'] = float(m.group(1))

    return updates


def _thermal_worker():
    """Background daemon: poll powermetrics every ~6 s and update _thermal."""
    while True:
        try:
            result = subprocess.run(
                ['sudo', '-n', 'powermetrics',
                 '--samplers', 'thermal,cpu_power,gpu_power',
                 '-n', '1', '-i', '4000'],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    updates = _parse_powermetrics_line(line.strip())
                    if updates:
                        with _thermal_lock:
                            _thermal.update(updates)
                            _thermal['available'] = True
        except Exception:
            pass
        time.sleep(2)


def _psutil_worker():
    """Background daemon: update CPU % every 4 s using psutil (no sudo needed)."""
    try:
        import psutil
        while True:
            pct = psutil.cpu_percent(interval=3.0)
            with _thermal_lock:
                _thermal['cpu_pct'] = pct
    except Exception:
        pass


def start_thermal_monitor():
    for target in (_thermal_worker, _psutil_worker):
        t = threading.Thread(target=target, daemon=True)
        t.start()


def get_thermal():
    with _thermal_lock:
        return dict(_thermal)


# ── Helpers ───────────────────────────────────────────────────────────────────

def bar(pct):
    filled = int(BAR_WIDTH * pct / 100)
    return '[' + '█' * filled + '░' * (BAR_WIDTH - filled) + f'] {pct:5.1f}%'


def trend_arrow(rec):
    if rec is None or len(rec) < 2:
        return '  '
    diff = rec[-1, 1] - rec[-2, 1]
    if diff > 0.5:  return '↑ '
    if diff < -0.5: return '↓ '
    return '→ '


def fmt_duration(seconds):
    if seconds < 0: return '--:--'
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0: return f'{h}h {m:02d}m'
    if m > 0: return f'{m}m {s:02d}s'
    return f'{s}s'


_PRESSURE_LEVELS = ['Nominal', 'Moderate', 'Heavy', 'Critical']
_PRESSURE_COLOURS = {
    'Nominal':  '\033[92m',   # green
    'Moderate': '\033[93m',   # yellow
    'Heavy':    '\033[91m',   # red
    'Critical': '\033[91;1m', # bold red
}
# Approximate chip temperature ranges for M4 Max (from Apple thermal spec + community data)
_PRESSURE_TEMP_HINT = {
    'Nominal':  '< ~75 °C',
    'Moderate': '~75–85 °C',
    'Heavy':    '~85–95 °C',
    'Critical': '> ~95 °C',
}

def _pressure_bar(p):
    """Visual heat-level bar:  [●●●○]  Heavy ~85-95°C"""
    if p is None:
        return '  Temp : N/A  (powermetrics starting…)'
    idx     = _PRESSURE_LEVELS.index(p) if p in _PRESSURE_LEVELS else 0
    filled  = idx + 1
    empty   = len(_PRESSURE_LEVELS) - filled
    colour  = _PRESSURE_COLOURS.get(p, '')
    hint    = _PRESSURE_TEMP_HINT.get(p, '')
    dots    = '●' * filled + '○' * empty
    return f'  Temp  : {colour}[{dots}] {p:<9}\033[0m  {hint}  (M4 Max — Apple thermal pressure)'


def get_ram_usage():
    try:
        out = subprocess.check_output(['vm_stat'], text=True)
        lines = {l.split(':')[0].strip(): l.split(':')[1].strip()
                 for l in out.splitlines() if ':' in l}
        page  = 16384
        free  = int(lines.get('Pages free', '0').replace('.', '')) * page
        total = 36 * 1024**3
        used_pct = (1 - free / total) * 100
        used_gb  = (total - free) / 1024**3
        return used_gb, used_pct
    except Exception:
        return None, None


# ── Optuna / filesystem helpers ───────────────────────────────────────────────

def detect_active_run():
    folders = [f for f in _RESULTS_DIR.iterdir()
               if f.is_dir() and f.name.startswith('res_')]
    if not folders:
        return None
    return max(folders, key=lambda f: f.stat().st_mtime)


def get_model_prefix(result_folder):
    name = result_folder.name
    idx  = name.find('_model_')
    return name[idx + 1:] if idx != -1 else None


def load_study_state(result_folder):
    study_path = result_folder / 'study.pkl'
    if not study_path.exists():
        return [], None, (None, None, {}), {}, {}
    try:
        study     = joblib.load(study_path)
        completed = sorted(t.number for t in study.trials if t.state.name == 'COMPLETE')
        running   = sorted(t.number for t in study.trials if t.state.name == 'RUNNING')
        active    = running[-1] if running else None

        trial_durations = {}
        for t in study.trials:
            if t.state.name == 'COMPLETE' and t.datetime_start and t.datetime_complete:
                trial_durations[t.number] = (
                    t.datetime_complete - t.datetime_start).total_seconds()

        active_params = {}
        if active is not None:
            for t in study.trials:
                if t.number == active:
                    active_params = t.params
                    break

        try:
            best = study.best_trial
            best_info = (best.number, best.value, best.params)
        except Exception:
            best_info = (None, None, {})

        return completed, active, best_info, trial_durations, active_params
    except Exception:
        return [], None, (None, None, {}), {}, {}


def get_split_data(prefix, trial_num, n_splits=10):
    splits = []
    for s in range(n_splits):
        split_dir = _CWD_TESTS / f'{prefix}_t{trial_num}_s{s}'
        rec_path  = split_dir / 'recorder.npy'
        entry = {'s': s, 'steps': 0, 'reward': None, 'rec': None,
                 'exists': False, 'start_mtime': None}
        if not split_dir.exists():
            splits.append(entry)
            continue
        entry['exists']      = True
        entry['start_mtime'] = split_dir.stat().st_birthtime
        if rec_path.exists():
            try:
                rec             = np.load(rec_path)
                entry['steps']  = int(rec[-1, 0])
                entry['reward'] = float(rec[-1, 1])
                entry['rec']    = rec
            except Exception:
                pass
        splits.append(entry)
    return splits


def get_steps_per_min(splits):
    rates = []
    for sp in splits:
        if sp['rec'] is not None and sp['start_mtime'] and len(sp['rec']) >= 1:
            elapsed = time.time() - sp['start_mtime']
            if elapsed > 60:
                rates.append(sp['steps'] / (elapsed / 60))
    return np.mean(rates) if rates else None


def _estimate_break_step(splits):
    max_steps = max((s['steps'] for s in splits if s['exists']), default=0)
    for bs in [200000, 300000, 500000]:
        if max_steps <= bs * 1.02:
            return bs
    return 500000


# ── Render ────────────────────────────────────────────────────────────────────

def render(result_folder, prefix, completed, active_trial,
           best_info, trial_durations, active_params, total_trials=50):
    print('\033[2J\033[H', end='', flush=True)
    now = datetime.now().strftime('%H:%M:%S')

    print('╔══════════════════════════════════════════════════════════════════╗')
    print(f'║         CPCV Training Monitor  [{now}]               ║')
    print('╚══════════════════════════════════════════════════════════════════╝')

    # ── RAM ─────────────────────────────────────────────────────────────────
    ram_gb, ram_pct = get_ram_usage()
    ram_str = f'{ram_gb:.1f}GB / 36GB ({ram_pct:.0f}%)' if ram_gb else 'N/A'
    print(f'  RAM   : {ram_str}')

    # ── Power / thermal (M4 Max — no die temps via powermetrics) ────────────
    th = get_thermal()
    cpu_w   = f"{th['cpu_power_w']:.1f}W"      if th['cpu_power_w']      is not None else '—'
    gpu_w   = f"{th['gpu_power_w']:.1f}W"      if th['gpu_power_w']      is not None else '—'
    tot_w   = f"{th['combined_power_w']:.1f}W" if th['combined_power_w'] is not None else '—'
    gpu_f   = f"{th['gpu_freq_mhz']:.0f}MHz"   if th['gpu_freq_mhz']     is not None else '—'
    cpu_pct = th['cpu_pct']
    cpu_str = f'{cpu_pct:.0f}%' if cpu_pct is not None else '—'
    print(f'  Power : CPU {cpu_w:<8}  GPU {gpu_w:<8}  Total {tot_w:<8}  GPU@{gpu_f}')
    print(f'  CPU   : {cpu_str} load')
    print(_pressure_bar(th['pressure']))

    print(f'  Run   : {result_folder.name[-40:]}')

    # ── Overall progress ─────────────────────────────────────────────────────
    n_done      = len(completed)
    overall_pct = n_done / total_trials * 100
    print(f'\n  Overall  {bar(overall_pct)}  {n_done}/{total_trials} trials')

    if n_done >= 2 and trial_durations:
        avg_sec   = np.mean(list(trial_durations.values()))
        remaining = total_trials - n_done - (1 if active_trial is not None else 0)
        eta_sec   = remaining * avg_sec
        print(f'  Avg/trial: {fmt_duration(avg_sec)}  |  ETA full run: {fmt_duration(eta_sec)}')

    # ── Best trial ───────────────────────────────────────────────────────────
    best_num, best_val, best_params = best_info
    if best_val is not None:
        sign = '+' if best_val > 0 else ''
        print(f'\n  Best Trial #{best_num}  objective = {sign}{best_val:.6f}')
        if best_params:
            p = best_params
            print(f'  Params → lr={p.get("learning_rate","?")}  '
                  f'lookback={p.get("lookback","?")}  '
                  f'batch={p.get("batch_size","?")}  '
                  f'break={int(p.get("break_step", 0)):,}  '
                  f'net={p.get("net_dimension","?")}  '
                  f'norm_r={p.get("norm_reward","?")}')
    else:
        print(f'\n  Best: (none yet — waiting for first trial to complete)')

    # ── Active trial ─────────────────────────────────────────────────────────
    if active_trial is None:
        print(f'\n  ⏳  Between trials or all done.')
        print(f'\n  (Refreshes every {args.refresh}s — Ctrl+C to exit)')
        return

    break_step_param = int(active_params.get('break_step', 0))
    splits     = get_split_data(prefix, active_trial)
    break_step = break_step_param if break_step_param > 0 else _estimate_break_step(splits)
    done_count = sum(1 for sp in splits if sp['steps'] >= break_step * 0.99)
    spm        = get_steps_per_min(splits)
    round_num  = 2 if done_count >= 7 else 1

    eta_trial_str = '--'
    if spm and spm > 0:
        slowest_remaining = max(
            (break_step - sp['steps'] for sp in splits
             if sp['exists'] and sp['steps'] < break_step * 0.99), default=0)
        eta_trial_str = fmt_duration(slowest_remaining / spm * 60)

    print(f'\n  ▶  Trial {active_trial}  |  Round {round_num}/2  |  '
          f'break_step={break_step:,}  |  ETA: {eta_trial_str}')
    if spm:
        print(f'     Speed: {spm:,.0f} steps/min')

    print(f'\n  {"Spl":<4} {"Trend":<3} {"Progress":<32} {"Steps":>10}   {"Reward":>10}  {"Elapsed":<10}')
    print(f'  {"─"*4} {"─"*3} {"─"*32} {"─"*10}   {"─"*10}  {"─"*10}')

    now_ts = time.time()
    for sp in splits:
        s      = sp['s']
        steps  = sp['steps']
        reward = sp['reward']
        pct    = min(steps / break_step * 100, 100) if sp['exists'] and break_step > 0 else 0
        done   = pct >= 99.0

        status  = '✅' if done else ('▶ ' if sp['exists'] else '⏳')
        arrow   = trend_arrow(sp['rec']) if not done else '  '
        rew_str = f'{reward:>10.4f}' if reward is not None else '         —'

        elapsed_str = ''
        if sp['start_mtime']:
            elapsed_str = fmt_duration(now_ts - sp['start_mtime'])

        print(f'  s{s:<3} {arrow}{status} {bar(pct)}  {steps:>10,}  {rew_str}  {elapsed_str:<10}')

    print(f'\n  {done_count}/10 splits done  |  {10 - done_count} still running')
    print(f'\n  (Refreshes every {args.refresh}s — Ctrl+C to exit)')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    result_folder = detect_active_run()
    if result_folder is None:
        print('No training run found in train_results/.')
        sys.exit(1)

    prefix = get_model_prefix(result_folder)
    if prefix is None:
        print(f'Could not parse model prefix from: {result_folder.name}')
        sys.exit(1)

    start_thermal_monitor()
    print('Starting power monitor… (waiting 5s for first sample)')
    time.sleep(5)  # let powermetrics + psutil workers produce their first readings

    last_good_state = ([], None, (None, None, {}), {}, {})

    while True:
        state = load_study_state(result_folder)
        if state[0] or state[1] is not None or state[2][1] is not None:
            last_good_state = state

        completed, active_trial, best_info, trial_durations, active_params = last_good_state

        render(result_folder, prefix, completed, active_trial,
               best_info, trial_durations, active_params, total_trials=50)
        time.sleep(args.refresh)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', type=int, default=30,
                        help='Refresh interval in seconds (default: 30)')
    args = parser.parse_args()
    try:
        main()
    except KeyboardInterrupt:
        print('\nMonitor stopped.')
