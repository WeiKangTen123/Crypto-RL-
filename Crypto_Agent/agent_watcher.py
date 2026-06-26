"""
agent_watcher.py — autonomous Gemini agent launcher.

Usage:
    python Crypto_Agent/agent_watcher.py <agent_id>
    agent_id: fullstack | data | researcher | developer | qa | tuner

Behaviour:
  - Polls the agent's inbox every 30 seconds.
  - When inbox messages are found, reads SKILL.md + inbox content and fires:
        gemini -m <model> -p "<prompt>" --yolo --output-format text
  - Also runs a scheduled task for each agent type when no inbox messages exist.
  - Model cascade: tries Pro → fallback Pro → Flash → Flash-Lite on quota exhaustion.
  - Heavy agents (researcher) start at Pro; light agents (data/fullstack) start at Flash.
  - Writes heartbeat.json so the Phase 6 dashboard shows live status.
  - Streams every Gemini output line to activity.log in real-time.
  - Stops cleanly when it receives SIGTERM (dashboard OFFLINE button).
"""

import os
import sys
import json
import glob
import time
import signal
import threading
import subprocess
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────

AGENT_MAP = {
    'fullstack':  'crypto-fullstack',
    'data':       'crypto-data-engineer',
    'researcher': 'alpha-researcher',
    'developer':  'alpha-developer',
    'qa':         'crypto-qa-tester',
    'tuner':      'crypto-strategy-tuner',
}

SCHEDULED_INTERVAL = {
    'fullstack':  1800,   # 30 min
    'data':       3600,   # 60 min
    'researcher': 14400,  # 4h — heavy discovery
    'developer':  3600,   # 60 min — synthesis checks
    'qa':         3600,   # 60 min
    'tuner':      300,    # 5 min
}

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT_DIR, '.gemini', 'skills')
GEMINI_BIN = '/Users/weikangten/.local/bin/agy'

# ── Model cascade ─────────────────────────────────────────────────────────────
# Ordered: most capable → lightest.
# On quota exhaustion the watcher falls back to the next model automatically.

MODEL_CASCADE = [
    'gemini-3.1-pro-preview',        # 0 — Pro (strongest reasoning, researcher default)
    'gemini-2.5-flash',              # 1 — Flash (balanced, fullstack default)
    'gemini-3.1-flash-lite-preview', # 2 — Flash Lite Preview (data default)
    'gemini-2.5-flash-lite',         # 3 — Flash Lite (lightest, qa default)
]

# Starting index per agent (matches assigned model tiers)
AGENT_MODEL_START = {
    'fullstack':  1,  # gemini-2.5-flash
    'data':       2,  # gemini-3.1-flash-lite-preview
    'researcher': 0,  # gemini-3.1-pro-preview
    'developer':  1,  # gemini-2.5-flash
    'qa':         3,  # gemini-2.5-flash-lite
    'tuner':      1,  # gemini-2.5-flash
}

# Keywords that indicate quota/rate-limit exhaustion in Gemini output
QUOTA_SIGNALS = (
    'RESOURCE_EXHAUSTED',
    'quota exceeded',
    'rate limit',
    '429',
    'rateLimitExceeded',
    'Quota exceeded',
)

# ── Signal handling ──────────────────────────────────────────────────────────

_running = True
ACTIVE_WATCHERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'active_watchers.json')
MAX_INBOX_BATCH      = 5          # max messages processed per run (prevents context overflow)
MSG_TTL_HOURS        = 48         # messages older than this are dead-lettered
MAX_DEAD_LETTER_AGE  = 30 * 60   # seconds a message can sit in active/ before dead-lettering


def _handle_sigterm(signum, frame):
    global _running
    _running = False

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT,  _handle_sigterm)


# ── Process lock (active_watchers.json) ──────────────────────────────────────

def _register_watcher(agent_id: str) -> bool:
    """Register this process in active_watchers.json. Returns False if already running."""
    pid = os.getpid()
    try:
        watchers = {}
        if os.path.exists(ACTIVE_WATCHERS_FILE):
            with open(ACTIVE_WATCHERS_FILE) as f:
                watchers = json.load(f)
        existing_pid = watchers.get(agent_id)
        if existing_pid and existing_pid != pid:
            try:
                os.kill(existing_pid, 0)   # check if process is alive
                return False               # still alive — duplicate, abort
            except OSError:
                pass                       # stale PID — safe to overwrite
        watchers[agent_id] = pid
        with open(ACTIVE_WATCHERS_FILE, 'w') as f:
            json.dump(watchers, f, indent=2)
        return True
    except Exception:
        return True  # can't read/write file — proceed anyway


def _unregister_watcher(agent_id: str):
    """Remove this agent's PID from active_watchers.json on shutdown."""
    try:
        watchers = {}
        if os.path.exists(ACTIVE_WATCHERS_FILE):
            with open(ACTIVE_WATCHERS_FILE) as f:
                watchers = json.load(f)
        watchers.pop(agent_id, None)
        with open(ACTIVE_WATCHERS_FILE, 'w') as f:
            json.dump(watchers, f, indent=2)
    except Exception:
        pass

# ── Activity log ─────────────────────────────────────────────────────────────

def log(agent_dir: str, message: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {message}'
    print(line)
    try:
        with open(os.path.join(agent_dir, 'activity.log'), 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

# ── Heartbeat ────────────────────────────────────────────────────────────────

_last_action: dict = {}

def update_heartbeat(agent_dir: str, status: str, action: str,
                     next_run_at: str = '', model: str = ''):
    path = os.path.join(agent_dir, 'heartbeat.json')
    if action == 'Idle' and agent_dir in _last_action:
        last = _last_action[agent_dir]
    else:
        last = action
        _last_action[agent_dir] = action
    try:
        payload = {
            'ts':          datetime.now().isoformat(),
            'status':      status,
            'action':      action,
            'last_action': last,
        }
        if next_run_at:
            payload['next_run_at'] = next_run_at
        if model:
            payload['model'] = model
        with open(path, 'w') as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

# ── Core helpers ─────────────────────────────────────────────────────────────

def read_skill(agent_name: str, stage: int = 0) -> str:
    """Read PROTOCOLS.md and optionally the current stage from STAGES.md."""
    protocols_path = os.path.join(SKILLS_DIR, agent_name, 'PROTOCOLS.md')
    stages_path    = os.path.join(SKILLS_DIR, agent_name, 'STAGES.md')
    
    # Fallback to SKILL.md if not yet refactored
    if not os.path.exists(protocols_path):
        protocols_path = os.path.join(SKILLS_DIR, agent_name, 'SKILL.md')

    content = ''
    if os.path.exists(protocols_path):
        with open(protocols_path) as f:
            content = f.read()

    # If stage > 0, extract specific mission from STAGES.md
    if stage > 0 and os.path.exists(stages_path):
        with open(stages_path) as f:
            stages_content = f.read()
        # Find "## STAGE X:" section
        import re
        pattern = rf'## STAGE {stage}:.*?(?=\n## STAGE|$)'
        match = re.search(pattern, stages_content, re.S)
        if match:
            mission = match.group(0)
            content = f"{content}\n\n# CURRENT MISSION (FOCUS ON THIS ONLY)\n{mission}"
            content += f"\n\nCRITICAL: You are currently in STAGE {stage}. You MUST output the [{stage}/...] marker and complete this mission before moving on."
            
    return content


def drain_inbox(inbox_dir: str) -> list:
    now         = time.time()
    active_dir  = os.path.join(inbox_dir, 'active')
    dead_dir    = os.path.join(inbox_dir, 'dead_letter')

    # Recover messages from active/ — but dead-letter any that have been stuck > MAX_DEAD_LETTER_AGE
    if os.path.exists(active_dir):
        for fpath in glob.glob(os.path.join(active_dir, '*.json')):
            try:
                age = now - os.path.getmtime(fpath)
                if age > MAX_DEAD_LETTER_AGE:
                    os.makedirs(dead_dir, exist_ok=True)
                    dest = os.path.join(dead_dir, os.path.basename(fpath))
                    os.rename(fpath, dest)
                else:
                    dest = os.path.join(inbox_dir, os.path.basename(fpath))
                    os.rename(fpath, dest)
            except Exception:
                pass

    messages = []
    for fpath in sorted(glob.glob(os.path.join(inbox_dir, '*.json'))):
        try:
            # TTL check — dead-letter messages older than MSG_TTL_HOURS
            age_hours = (now - os.path.getmtime(fpath)) / 3600
            if age_hours > MSG_TTL_HOURS:
                os.makedirs(dead_dir, exist_ok=True)
                dest = os.path.join(dead_dir, os.path.basename(fpath))
                os.rename(fpath, dest)
                continue
            with open(fpath) as f:
                msg = json.load(f)
            msg['_file'] = fpath
            messages.append(msg)
        except Exception:
            pass

    # Batch cap — process at most MAX_INBOX_BATCH messages per run (HIGH priority first)
    messages.sort(key=lambda m: (0 if m.get('priority') == 'HIGH' else 1))
    return messages[:MAX_INBOX_BATCH]


def run_gemini(prompt: str, agent_dir: str, action_label: str,
               model_start_idx: int = 2):
    """
    Run Gemini with automatic model cascade on quota exhaustion.
    Includes a background heartbeat thread to keep status ONLINE during long runs.
    """
    log_path = os.path.join(agent_dir, 'activity.log')
    session_log_path = os.path.join(agent_dir, 'session_memory')

    # Force an initial [1/X] progress marker in the heartbeat to light up circle 1
    total_steps = 8 if 'developer' in agent_dir else 5 if 'qa' in agent_dir else 4
    initial_step = f"[1/{total_steps}] INITIALIZING: System handshake..."
    update_heartbeat(agent_dir, 'ONLINE', initial_step)

    # Start background heartbeat thread
    stop_heartbeat = threading.Event()
    def heartbeat_loop():
        while not stop_heartbeat.is_set():
            # Check current action from disk to avoid overwriting detailed [X/Y] steps
            try:
                hb_path = os.path.join(agent_dir, 'heartbeat.json')
                if os.path.exists(hb_path):
                    with open(hb_path, 'r') as f:
                        curr = json.load(f)
                        curr_action = curr.get('action', '')
                        # Only overwrite if current action is generic or doesn't have [X/Y]
                        if not re.search(r'\[\d+/\d+\]', curr_action):
                            update_heartbeat(agent_dir, 'ONLINE', action_label)
                else:
                    update_heartbeat(agent_dir, 'ONLINE', action_label)
            except Exception:
                update_heartbeat(agent_dir, 'ONLINE', action_label)
                
            stop_heartbeat.wait(15) 
            
    hb_thread = threading.Thread(target=heartbeat_loop)
    hb_thread.daemon = True
    hb_thread.start()

    for idx in range(model_start_idx, len(MODEL_CASCADE)):
        model = MODEL_CASCADE[idx]
        log(agent_dir, f'▶ GEMINI START — {action_label} [{model}]')
        
        # Also write the start marker to the session log for context
        with open(session_log_path, 'a') as sf:
            sf.write(f'\n--- GEMINI SESSION START: {model} ---\n')
            
        t0 = time.time()
        quota_hit = False

        try:
            # Debugging: Log prompt length and first few characters
            log(agent_dir, f"DEBUG: Prompt length: {len(prompt)}")
            if len(prompt) > 0:
                log(agent_dir, f"DEBUG: Prompt starts with: {repr(prompt[:50])}")

            # Ensure ripgrep and local tools are visible to Gemini subprocess
            import copy
            gemini_env = copy.copy(os.environ)
            local_bin = os.path.expanduser('~/.local/bin')
            if local_bin not in gemini_env.get('PATH', ''):
                gemini_env['PATH'] = local_bin + os.pathsep + gemini_env.get('PATH', '')
            
            cmd = [GEMINI_BIN, '--model', model, '--print',
                 '--dangerously-skip-permissions']
            log(agent_dir, f"DEBUG: Executing command: {cmd[:4]} ...")
            
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT_DIR,
                env=gemini_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            # Write prompt to stdin and close it
            proc.stdin.write(prompt)
            proc.stdin.close()
            with open(session_log_path, 'a') as sf:
                for line in proc.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    sf.write(f'[{ts}] {line}\n')
                    sf.flush()

                    # --- Live Progress Parsing ---
                    # If agent outputs "[3/8] Writing Logic...", update heartbeat action immediately
                    import re
                    match = re.search(r'\[(\d+)/(\d+)\]\s*(.*)', line)
                    if match:
                        step_text = line.strip()
                        update_heartbeat(agent_dir, 'ONLINE', step_text, model=model)

                    # Detect quota exhaustion mid-stream
                    if any(sig in line for sig in QUOTA_SIGNALS):
                        quota_hit = True
                        proc.kill()
                        break
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except FileNotFoundError:
            log(agent_dir, f'✗ agy not found at {GEMINI_BIN}')
            return

        elapsed = int(time.time() - t0)

        if quota_hit and idx < len(MODEL_CASCADE) - 1:
            next_model = MODEL_CASCADE[idx + 1]
            log(agent_dir,
                f'⚠ Quota hit on {model} ({elapsed}s) — falling back to {next_model}')
            continue

        if quota_hit:
            log(agent_dir, f'✗ All models exhausted — task deferred until quota resets')
        else:
            log(agent_dir, f'✓ GEMINI DONE — {action_label} [{model}] ({elapsed}s)')
            
            # --- AUTOMATED GLOBAL SESSION LOGGING ---
            ts = datetime.now().strftime('%Y-%m-%d %H:%M')
            agent_name = os.path.basename(agent_dir)
            try:
                if not os.path.exists(GLOBAL_MEMORY_PATH):
                    with open(GLOBAL_MEMORY_PATH, 'w') as gm:
                        gm.write("# System Global Session Memory\n\n_No sessions recorded yet._")
                        
                with open(GLOBAL_MEMORY_PATH, 'r') as gm:
                    current_mem = gm.read()
                
                new_entry = f"\n---\n## [{ts}] | Agent: @{agent_name} | Model: {model} | Duration: ~{elapsed}s\n\n**Trigger:** {action_label}\n**Status:** Automated run completed."
                
                # Insert right after the header block to keep it top-down
                blocks = current_mem.split('\n---\n')
                if len(blocks) > 0:
                    header = blocks[0]
                    rest = blocks[1:]
                    new_mem = header + '\n---\n' + new_entry.strip() + '\n\n---\n\n' + '\n\n---\n\n'.join([b.strip() for b in rest if b.strip() and '_No sessions' not in b])
                    with open(GLOBAL_MEMORY_PATH, 'w') as gm:
                        gm.write(new_mem)
                trim_session_memory(agent_dir)
            except Exception as e:
                log(agent_dir, f'⚠ Failed to update global session memory: {e}')

        break

    # Stop heartbeat thread
    stop_heartbeat.set()
    hb_thread.join(timeout=2)
    update_heartbeat(agent_dir, 'ONLINE', 'Idle')


GLOBAL_MEMORY_PATH = os.path.join(ROOT_DIR, '.gemini', 'session_memory.md')

def read_session_memory(agent_dir: str, n_sessions: int = 2) -> str:
    """Return last n session blocks from the global .gemini/session_memory.md as a context string."""
    if not os.path.exists(GLOBAL_MEMORY_PATH):
        return ''
    try:
        with open(GLOBAL_MEMORY_PATH) as f:
            content = f.read()
        # Sessions are separated by \n---\n; first block is the file header
        blocks = content.split('\n---\n')
        sessions = [b.strip() for b in blocks[1:] if b.strip() and b.strip() != '_No sessions recorded yet._']
        if not sessions:
            return ''
        recent = sessions[:n_sessions]
        joined = '\n\n---\n\n'.join(recent)
        return f'## RECENT SYSTEM SESSIONS (context — read Open Items before starting):\n\n{joined}'
    except Exception:
        return ''

def trim_session_memory(agent_dir: str, max_sessions: int = 10):
    """Keep only the most recent max_sessions entries in the global .gemini/session_memory.md."""
    if not os.path.exists(GLOBAL_MEMORY_PATH):
        return
    try:
        with open(GLOBAL_MEMORY_PATH) as f:
            content = f.read()
        blocks  = content.split('\n---\n')
        header  = blocks[0]
        sessions = [b for b in blocks[1:] if b.strip() and b.strip() != '_No sessions recorded yet._']
        if len(sessions) <= max_sessions:
            return
        trimmed  = sessions[:max_sessions]
        new_content = header + '\n---\n' + '\n---\n'.join(trimmed)
        with open(GLOBAL_MEMORY_PATH, 'w') as f:
            f.write(new_content)
    except Exception:
        pass


def build_prompt(skill: str, messages: list, scheduled_task: str = '',
                 agent_dir: str = '', inject_memory: bool = True) -> str:
    parts = [skill.strip()]
    # Prepend last 2 session memory entries so agent has cross-session context
    if agent_dir and inject_memory:
        memory = read_session_memory(agent_dir)
        if memory:
            parts.insert(0, memory + '\n')
    if messages:
        parts.append('\n---\n## INBOX — Handle these messages now:\n')
        parts.append(json.dumps(messages, indent=2))
    elif scheduled_task:
        parts.append(f'\n---\n## SCHEDULED TASK\n{scheduled_task}')
    return '\n'.join(parts)

# ── Scheduled task prompts ────────────────────────────────────────────────────

SCHEDULED_TASKS = {
    'fullstack': (
        "You are now ONLINE. Perform your startup system check:\n"
        "1. Read .gemini/logs/error_log.jsonl — check for any unprocessed errors "
        "(newer than the timestamp in .gemini/logs/last_processed_ts.txt if it exists).\n"
        "2. Run a server health check: curl -s http://127.0.0.1:5001/api/strategy_list "
        "and confirm it returns a valid JSON list.\n"
        "3. If errors are found in the log: diagnose each one, apply a fix, verify the fix.\n"
        "4. If the server is down or returning 500: diagnose main_controller/main.py and restart.\n"
        "5. Check your inbox at .gemini/skills/crypto-fullstack/inbox/ for any pending messages.\n"
        "6. Update main_controller/agent_status.json with your current status.\n"
        "7. Append a summary row to .gemini/shared/AGENT_COLLABORATION.md."
    ),
    'data': (
        "Run the health scout script to perform a full data health check:\n"
        "  ./venv/bin/python .gemini/skills/crypto-data-engineer/scripts/health_scout_v2.py --once\n"
        "This script will: scan all parquets for gaps/anomalies/dtype errors, write results "
        "to .gemini/skills/crypto-data-engineer/logs/HEALTH_SCOUT.log, send inbox messages "
        "to other agents, and update .gemini/shared/AGENT_COLLABORATION.md.\n"
        "After the script completes, append a one-line summary row to .gemini/shared/AGENT_COLLABORATION.md "
        "if the script did not already do so. Do NOT redo the health check manually."
    ),
    'researcher': (
        "Run your autonomous research cycle. Follow §4 in your SKILL.md exactly.\n\n"
        "STEP 1 — Check model tier:\n"
        "  - If on Flash or lower: SKIP to Step 3 (queue check only, no full pipeline).\n"
        "  - If on Pro: continue to Step 2.\n\n"
        "STEP 2 — Web discovery (Pro only). Search in order until you have 1-2 solid ideas:\n"
        "  Tier 1 (search first): TradingView published scripts, "
        "github.com/freqtrade/freqtrade-strategies, github.com/jesse-ai/strategies, "
        "Quantpedia.com (search 'crypto'), SSRN (search 'cryptocurrency trading strategy').\n"
        "  Tier 2: arXiv q-fin ('cryptocurrency momentum'), Reddit r/algotrading ('crypto backtest'), "
        "Binance Research, Glassnode blog, CryptoQuant.\n"
        "  Tier 3: X/Twitter @CryptoCred @KoroushAK #cryptostrategy, QuantConnect forums.\n"
        "  Priority strategy types to look for (gaps in current library):\n"
        "    HIGH: funding rate mean reversion, multi-TF divergence (1h+4h+1d), "
        "volume-profile anchored VWAP, Fear&Greed+RSI combo.\n"
        "    MEDIUM: BTC dominance regime filter, Fibonacci+volume, basis trade.\n"
        "  If google_web_search fails → log 'web search unavailable' and go to Step 3. "
        "Do NOT block or wait for user.\n\n"
        "STEP 3 — Queue check:\n"
        "  - Scan factor_library/ for Candidate Cards (any .md file) with frontmatter status: QUEUED.\n"
        "  - QUEUED + HIGH interest + Pro model: implement top 1-2 using the full 8-stage pipeline.\n"
        "  - Queue empty OR Flash model: log 'no work available' and go idle.\n\n"
        "STEP 4 — After validated strategy:\n"
        "  - Update the Candidate Card in factor_library/ to status: IMPLEMENTED, notify @crypto-fullstack.\n\n"
        "IMPORTANT: Do NOT run the research cycle in response to inbox messages. "
        "Only run this cycle when you wake up with NO inbox to process."
    ),
    'qa': (
        "Run the automated QA test suite:\n"
        "1. Execute: ./venv/bin/python .gemini/skills/crypto-qa-tester/scripts/system_test.py --once\n"
        "   This tests Flask routes, strategy imports, data linkage, and backtest smoke.\n"
        "   It writes pass/fail results to .gemini/skills/crypto-qa-tester/logs/qa_results.log\n"
        "   and automatically sends inbox messages for any failures.\n"
        "2. After the script finishes, read the last 30 lines of qa_results.log to get the summary.\n"
        "3. If any FAIL entries were not already routed by the script, write inbox messages "
        "   to the appropriate agent using the routing table in your SKILL.md.\n"
        "4. Append a summary row to .gemini/shared/AGENT_COLLABORATION.md.\n"
        "5. Update your heartbeat.json with the result summary. NEVER write status: OFFLINE."
    ),
    'tuner': (
        "You are the strategy tuner. Follow your SKILL.md §1→§4 in order.\n\n"
        "STEP 1 — Inbox priority (check first):\n"
        "  - RUN_SCAN_NOW → run scan immediately regardless of classified state\n"
        "  - FORCE_RESCAN_NOW → delete scan_results.json, run fresh scan\n"
        "  - FINETUNE → run finetune.py (see §3 in SKILL.md for full instructions)\n"
        "    NOTE: --date_from/--date_to in the message are the Optuna trial window only. "
        "The script handles full-period validation automatically.\n"
        "    The script handles all file updates — do NOT manually edit settings.py or strategy files.\n\n"
        "STEP 2 — Scan logic (if no dashboard command):\n"
        "  - scan_results.json exists AND classified=true AND no PENDING → skip scan\n"
        "  - scan_results.json exists AND classified=false → classify PENDING only (no re-scan)\n"
        "  - scan_results.json missing OR force_rescan.flag exists → "
        "run: ./venv/bin/python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py\n"
        "  Classify: grade (GOOD/MEDIOCRE/BAD) + grade_reason per strategy using tuner_specs.md. "
        "Grades: GOOD ≥ 1.0 | MEDIOCRE 0.3–1.0 | BAD < 0.3\n\n"
        "STEP 3 — Proactive fine-tuning (only if no FINETUNE inbox messages exist):\n"
        "  - Find the worst BAD strategy in scan_results.json (lowest Sharpe, grade='BAD')\n"
        "  - Check finetune_results.json — skip if fine-tuned within last 24 hours\n"
        "  - If eligible: run finetune.py --strategy_id {id} (omit --trials — script auto-scales)\n"
        "  - Limit: 1 autonomous fine-tune per wake-up only\n\n"
        "STEP 4: Append a one-line summary to .gemini/shared/AGENT_COLLABORATION.md.\n"
        "STEP 5: Update heartbeat.json. NEVER write status: OFFLINE."
    ),
}

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    global _running
    if len(sys.argv) < 2 or sys.argv[1] not in AGENT_MAP:
        print(f'Usage: python agent_watcher.py <agent_id>')
        print(f'agent_id: {" | ".join(AGENT_MAP.keys())}')
        sys.exit(1)

    agent_id   = sys.argv[1]
    agent_name = AGENT_MAP[agent_id]
    agent_dir  = os.path.join(SKILLS_DIR, agent_name)
    inbox_dir  = os.path.join(agent_dir, 'inbox')
    os.makedirs(inbox_dir, exist_ok=True)

    # Prevent duplicate watcher processes for the same agent
    if not _register_watcher(agent_id):
        print(f'✗ {agent_name} watcher already running — exiting to prevent duplicate.')
        sys.exit(0)

    skill          = read_skill(agent_name)
    interval       = SCHEDULED_INTERVAL[agent_id]
    scheduled_task = SCHEDULED_TASKS.get(agent_id, '')
    model_start    = AGENT_MODEL_START.get(agent_id, 2)
    last_scheduled = 0.0

    log(agent_dir,
        f'═══ {agent_name} ONLINE — polling every 30s, '
        f'scheduled every {interval//60}m, '
        f'starting model: {MODEL_CASCADE[model_start]} ═══')
    # Initial heartbeat
    standby_flag = os.path.join(agent_dir, 'standby_mode.flag')
    in_standby   = os.path.exists(standby_flag)
    ui_status    = 'STANDBY' if in_standby else 'ONLINE'
    update_heartbeat(agent_dir, ui_status, 'Idle',
                     next_run_at=f'{interval//60}m 00s',
                     model=MODEL_CASCADE[model_start])

    while _running:
        now        = time.time()
        in_standby = os.path.exists(standby_flag)

        # 1. Check inbox first (always — even in STANDBY)
        messages = drain_inbox(inbox_dir)
        if messages:
            topics = ', '.join(m.get('topic', '?') for m in messages)
            log(agent_dir, f'📥 INBOX: {len(messages)} message(s) — [{topics}]')

            # Move to 'active' subfolder so dashboard knows they are being worked on
            active_dir = os.path.join(inbox_dir, 'active')
            os.makedirs(active_dir, exist_ok=True)
            active_files = []
            for m in messages:
                dest = os.path.join(active_dir, os.path.basename(m['_file']))
                os.rename(m['_file'], dest)
                active_files.append(dest)

            # HIGH priority inbox → start at Pro regardless of agent type
            has_high = any(m.get('priority') == 'HIGH' for m in messages)
            inbox_model_start = 0 if has_high else model_start

            # Researcher inbox runs on Flash — inbox processing needs no research
            final_prompt = build_prompt(skill, messages, agent_dir=agent_dir)
            if agent_id == 'researcher' and inbox_model_start > 0:
                final_prompt += "\n\nCRITICAL SYSTEM OVERRIDE: You are running on a LIGHT model. Do NOT perform research. SKIP all discovery and implementation steps. Check queue and go IDLE immediately."

            run_gemini(final_prompt,
                       agent_dir, f'Inbox: {len(messages)} message(s)',
                       model_start_idx=inbox_model_start)

            # --- Sequential Gating Check ---
            # If the agent just completed an implementation/research handoff, 
            # we don't need a multi-call loop here yet as inbox processing is usually one-shot.
            # But for scheduled tasks, we will implement the true stage-by-stage loop below.

            # Trim session memory after each run (keep max 10 sessions)
            trim_session_memory(agent_dir)

            # Delete active files after Gemini finishes
            for fpath in active_files:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
            last_scheduled = time.time()

        # 2. Scheduled autonomous task — skipped when in STANDBY mode
        elif not in_standby and interval and (now - last_scheduled) >= interval:
            log(agent_dir, f'⏰ SCHEDULED TASK triggered (interval {interval//60}m elapsed)')
            
            # Use stage-by-stage loop if STAGES.md exists
            stages_path = os.path.join(agent_dir, 'STAGES.md')
            if os.path.exists(stages_path):
                total_stages = 8 if agent_id == 'developer' else 4
                log(agent_dir, f'🚀 Starting Sequential Mission: {total_stages} Stages...')
                
                for s_idx in range(1, total_stages + 1):
                    # Check for stop signal during loop
                    if not _running: break
                    
                    # Read dynamic gated skill for THIS STAGE ONLY
                    gated_skill = read_skill(agent_name, stage=s_idx)
                    
                    # Model Downshifting: Use Pro (0) for Research/Dev heavy lifting, Flash (1) for mechanical/reporting stages
                    task_model_start = model_start
                    if agent_id == 'researcher':
                        task_model_start = 0 if s_idx <= 2 else 1
                    elif agent_id == 'developer':
                        task_model_start = 0 if s_idx <= 4 else 1
                    
                    # Context Isolation: Only inject heavy global memory on Stage 1
                    inject_mem = (s_idx == 1)
                    stage_prompt = build_prompt(gated_skill, [], f"Mission Milestone {s_idx}/{total_stages}", agent_dir=agent_dir, inject_memory=inject_mem)
                    
                    log(agent_dir, f'▶ Running Stage {s_idx}/{total_stages}...')
                    run_gemini(stage_prompt, agent_dir, f'Stage {s_idx}', model_start_idx=task_model_start)
                    
                    # Trim session memory between stages to keep context fresh
                    trim_session_memory(agent_dir)
                    
                log(agent_dir, f'✓ Full Sequential Mission Complete.')
                # AUTO-STOP: Exit the loop after mission completion
                _running = False
            else:
                # One-shot task for agents without STAGES.md
                # Context Isolation: Mechanical agents (Tuner, Data, QA, Fullstack) rely on JSON/DB states, not text memory.
                task_model_start = model_start
                task_prompt = build_prompt(skill, [], scheduled_task, agent_dir=agent_dir, inject_memory=False)
                run_gemini(task_prompt, agent_dir, 'Scheduled task', model_start_idx=task_model_start)
                trim_session_memory(agent_dir)
            
            last_scheduled = time.time()

        # 3. Update idle heartbeat with next-run countdown
        ui_status = 'STANDBY' if in_standby else 'ONLINE'
        
        if interval and scheduled_task:
            secs_until = max(0, int(interval - (time.time() - last_scheduled)))
            next_label = f'{secs_until // 60}m {secs_until % 60:02d}s'
        else:
            next_label = ''

        update_heartbeat(agent_dir, ui_status, 'Idle',
                         next_run_at=next_label,
                         model=MODEL_CASCADE[model_start])

        for _ in range(30):
            if not _running:
                break
            time.sleep(1)

    # Clean shutdown
    _unregister_watcher(agent_id)
    log(agent_dir, f'═══ {agent_name} OFFLINE — stopped by user ═══')
    update_heartbeat(agent_dir, 'OFFLINE', 'Stopped by user')


if __name__ == '__main__':
    main()
