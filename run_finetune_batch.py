"""
Parallel finetune batch runner — 79 BAD strategies, max 3 concurrent jobs (≤40% RAM).
Skips IDs where a completed log already exists. Detects externally running finetune
processes so it never exceeds MAX_PARALLEL total (including inherited jobs).
"""
import subprocess, os, sys, time, signal, re
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(ROOT, 'venv', 'bin', 'python')
SCRIPT = os.path.join(ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'scripts', 'finetune.py')
LOG_DIR = os.path.join(ROOT, 'logs', 'finetune_batch')
os.makedirs(LOG_DIR, exist_ok=True)

MAX_PARALLEL = 3

# Full 79 candidates: (id, trials) — sorted best Sharpe first
ALL_CANDIDATES = [
    ('117', 500), ('16',  500), ('36',  500), ('146', 500),
    ('3',   500), ('14',  500), ('11',  400), ('6',   400),
    ('78',  400), ('105', 400), ('61',  400), ('86',  400),
    ('84',  400), ('20',  400), ('93',  400), ('97',  400),
    ('85',  400), ('153', 400), ('5',   400), ('32',  400),
    ('73',  400), ('41',  400), ('39',  300), ('99',  300),
    ('62',  300), ('101', 300), ('63',  300), ('59',  300),
    ('79',  300), ('26',  300), ('40',  300), ('46',  300),
    ('111', 300), ('75',  300), ('104', 300), ('30',  300),
    ('12',  300), ('67',  300), ('19',  300), ('47',  300),
    ('139', 300), ('34',  300), ('147', 300), ('54',  300),
    ('100', 300), ('98',  300), ('151', 300), ('108', 300),
    ('8',   300), ('33',  300), ('57',  300), ('102', 300),
    ('154', 300), ('7',   300), ('45',  300), ('71',  300),
    ('31',  300), ('91',  300), ('95',  300), ('65',  300),
    ('48',  300), ('56',  300), ('53',  300), ('150', 300),
    ('10',  300), ('42',  300), ('140', 300), ('136', 300),
    ('134', 300), ('29',  300), ('94',  300), ('43',  300),
    ('103', 300), ('143', 300), ('87',  300), ('27',  300),
    ('131', 300), ('90',  300), ('69',  300),
]


def is_started(sid):
    """Return True if a log file already exists for this ID (complete or in-progress)."""
    logpath = os.path.join(LOG_DIR, f'finetune_{sid}.log')
    return os.path.exists(logpath)


def count_running_finetune():
    """Count finetune.py processes currently running in the OS (any PID)."""
    try:
        out = subprocess.check_output(['ps', 'aux'], text=True)
        return sum(1 for line in out.splitlines() if 'finetune.py' in line and 'grep' not in line)
    except Exception:
        return 0


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)


def main():
    # Filter out IDs that already have a log file (done or in-progress)
    queue = [(sid, tr) for sid, tr in ALL_CANDIDATES if not is_started(sid)]
    skipped = len(ALL_CANDIDATES) - len(queue)

    log(f'Total candidates: {len(ALL_CANDIDATES)} | Already done: {skipped} | Remaining: {len(queue)}')
    log(f'Max parallel: {MAX_PARALLEL} | Logs → {LOG_DIR}')
    print('─' * 60, flush=True)

    total = len(queue)
    done = 0
    failed = []
    running = {}   # pid → (sid, trials, logfile, proc, start_time, file_handle)
    start_all = time.time()

    try:
        while queue or running:
            # Count total finetune processes (ours + any externally inherited)
            external = count_running_finetune() - len(running)
            available_slots = MAX_PARALLEL - len(running) - max(0, external)

            while available_slots > 0 and queue:
                sid, trials = queue.pop(0)
                logpath = os.path.join(LOG_DIR, f'finetune_{sid}.log')
                cmd = [VENV_PYTHON, SCRIPT, '--strategy_id', sid, '--trials', str(trials)]
                lf = open(logpath, 'w')
                proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                        cwd=ROOT, start_new_session=True)
                running[proc.pid] = (sid, trials, logpath, proc, time.time(), lf)
                log(f'▶ START  ID={sid:>4} ({trials} trials)  PID={proc.pid}  '
                    f'[{len(running)} own + {max(0,external)} ext / {MAX_PARALLEL} max]')
                available_slots -= 1

            time.sleep(8)

            for pid in list(running):
                sid, trials, logpath, proc, t0, lf = running[pid]
                ret = proc.poll()
                if ret is not None:
                    lf.close()
                    elapsed = int(time.time() - t0)
                    done += 1
                    remaining_count = total - done
                    avg_sec = (time.time() - start_all) / done
                    eta_min = int(avg_sec * remaining_count / 60)

                    result_line = ''
                    try:
                        with open(logpath) as rf:
                            for line in reversed(rf.readlines()):
                                if 'Best Sharpe' in line or 'Worth saving' in line or 'ERROR' in line.upper():
                                    result_line = line.strip()
                                    break
                    except Exception:
                        pass

                    status = '✓' if ret == 0 else '✗'
                    log(f'{status} DONE   ID={sid:>4}  {elapsed}s  {done}/{total}  ETA≈{eta_min}m  | {result_line}')
                    if ret != 0:
                        failed.append(sid)
                    del running[pid]

    except KeyboardInterrupt:
        log('Interrupted — killing running jobs...')
        for pid in running:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception:
                pass
        sys.exit(1)

    total_min = int((time.time() - start_all) / 60)
    print('─' * 60, flush=True)
    log(f'Batch complete. {done} new jobs finished in {total_min}min.')
    if failed:
        log(f'FAILED IDs: {", ".join(failed)}')
    else:
        log('All jobs succeeded.')


if __name__ == '__main__':
    main()
