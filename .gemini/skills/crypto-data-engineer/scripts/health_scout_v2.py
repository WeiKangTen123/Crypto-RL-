import os
import sys
import json
import time
import glob
import pandas as pd
from datetime import datetime, timedelta

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR    = os.path.dirname(SCRIPT_DIR)
ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(AGENT_DIR)))
LOG_DIR      = os.path.join(AGENT_DIR, 'logs')
INBOX_DIR    = os.path.join(AGENT_DIR, 'inbox')
COLLAB_FILE  = os.path.join(ROOT_DIR, '.gemini', 'shared', 'AGENT_COLLABORATION.md')
HEALTH_LOG   = os.path.join(LOG_DIR, 'system_health.log')
ACTIVITY_LOG = os.path.join(AGENT_DIR, 'activity.log')
HEARTBEAT    = os.path.join(AGENT_DIR, 'heartbeat.json')
DATASET_DIR  = os.path.join(ROOT_DIR, 'dataset')

# Expected bars per day for each timeframe
BARS_PER_DAY = {'1m': 1440, '5m': 288, '15m': 96, '30m': 48, '1h': 24, '4h': 6, '1d': 1}

# Columns that must be numeric
REQUIRED_NUMERIC = ['Open', 'High', 'Low', 'Close', 'Volume']
OPTIONAL_NUMERIC = ['taker_buy_base_vol', 'num_trades']


# Shared logger
sys.path.insert(0, '/Users/weikangten/Desktop/Crypto-RL/.gemini/shared')
from logger import log_to_agent
from log_rotator import rotate_log

# ── Paths ────────────────────────────────────────────────────────────────────
...
LOG_DIR      = os.path.join(AGENT_DIR, 'logs')
HEALTH_LOG   = os.path.join(LOG_DIR, 'system_health.log')
ACTIVITY_LOG = os.path.join(AGENT_DIR, 'activity.log')

def log(msg):
    # Log to local file (legacy)
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    with open(HEALTH_LOG, 'a') as f:
        f.write(line + '\n')
    
    # Log to shared dashboard/activity.log
    print(line)
    log_to_agent('crypto-data-engineer', msg)


def update_heartbeat(action, status='ONLINE'):
    ts = datetime.now().isoformat()
    with open(HEARTBEAT, 'w') as f:
        json.dump({'ts': ts, 'action': action, 'status': status}, f)


def write_inbox(target_agent: str, topic: str, priority: str, message: str, context: dict):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    inbox_path = os.path.join(ROOT_DIR, '.gemini', 'skills', target_agent, 'inbox')
    os.makedirs(inbox_path, exist_ok=True)
    filename = f'{ts}_from_data-engineer_{topic}.json'
    payload = {
        'from': 'crypto-data-engineer',
        'priority': priority,
        'topic': topic,
        'message': message,
        'context': context,
    }
    with open(os.path.join(inbox_path, filename), 'w') as f:
        json.dump(payload, f, indent=2)
    log(f'  → Sent {priority} inbox message to @{target_agent}: {topic}')


def update_collaboration_md(task, status, notes=""):
    if not os.path.exists(COLLAB_FILE):
        return
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    new_row = f'| {ts} | @crypto-data-engineer | {task} | {status} | {notes} |\n'
    
    with open(COLLAB_FILE, 'r') as f:
        lines = f.readlines()
    
    # Try to find the Latest Tasks section
    found = False
    for i, line in enumerate(lines):
        if '## Latest Tasks & Handoffs' in line:
            # Insert after the table header (usually 2 lines down)
            lines.insert(i + 3, new_row)
            found = True
            break
    
    if not found:
        lines.append('\n## Latest Tasks & Handoffs\n')
        lines.append('| Date | Agent | Task | Status |\n')
        lines.append('| :--- | :--- | :--- | :--- |\n')
        lines.append(new_row)
        
    with open(COLLAB_FILE, 'w') as f:
        f.writelines(lines)
    log(f'  Updated AGENT_COLLABORATION.md with task: {task}')


def check_parquet(coin: str, tf: str, parquet_path: str) -> dict:
    result = {'coin': coin, 'tf': tf, 'ok': True, 'issues': []}
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        result['ok'] = False
        result['issues'].append(f'UNREADABLE: {e}')
        return result

    # Normalise column names (case-insensitive check)
    cols_found = {c.lower(): c for c in df.columns}
    col_map = {}
    for req in REQUIRED_NUMERIC + OPTIONAL_NUMERIC:
        if req.lower() in cols_found:
            col_map[cols_found[req.lower()]] = req
    
    df = df.rename(columns=col_map)

    # Set datetime index
    date_cols = ['open_time', 'timestamp', 'Date', 'datetime']
    found_date_col = None
    for c in df.columns:
        if c.lower() in [dc.lower() for dc in date_cols]:
            found_date_col = c
            break
    
    if found_date_col:
        df[found_date_col] = pd.to_datetime(df[found_date_col])
        df = df.set_index(found_date_col)
    elif not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except:
            result['ok'] = False
            result['issues'].append('INVALID_INDEX: Index is not datetime and open_time missing')
            return result
            
    df = df.sort_index()

    # 1. Dtype validation
    for col in REQUIRED_NUMERIC:
        if col not in df.columns:
            result['ok'] = False
            result['issues'].append(f'MISSING_COLUMN: {col}')
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            result['ok'] = False
            result['issues'].append(f'DTYPE_ERROR: {col} is {df[col].dtype}, expected numeric')

    for col in OPTIONAL_NUMERIC:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            result['ok'] = False
            result['issues'].append(f'DTYPE_ERROR: {col} is {df[col].dtype}, expected numeric')

    # 2. Gap detection
    if len(df) > 0 and tf in BARS_PER_DAY:
        # Check for duplicates first
        if df.index.duplicated().any():
            result['issues'].append(f'DUPLICATES: Found {df.index.duplicated().sum()} duplicate timestamps')
            df = df[~df.index.duplicated(keep='first')]

        date_range_days = (df.index[-1] - df.index[0]).total_seconds() / 86400
        expected = int(date_range_days * BARS_PER_DAY[tf])
        actual = len(df)
        if expected > 0:
            coverage = actual / expected
            if coverage < 0.95:
                pct_missing = round((1 - coverage) * 100, 1)
                result['issues'].append(f'DATA_GAP: {pct_missing}% missing ({actual}/{expected} bars)')
                if coverage < 0.80:
                    result['ok'] = False

    # 3. Freshness check
    if len(df) > 0:
        latest = df.index[-1]
        # Use UTC for comparison if possible
        now = datetime.now(latest.tzinfo) if latest.tzinfo else datetime.now()
        hours_stale = (now - latest).total_seconds() / 3600
        if hours_stale > 168:
            result['ok'] = False
            result['issues'].append(f'STALE_CRITICAL: latest bar is {int(hours_stale)}h ago')
        elif hours_stale > 48:
            result['issues'].append(f'STALE_WARN: latest bar is {int(hours_stale)}h ago')

        # 4. Anomaly detection (Price Spike > 10%)
        if 'Close' in df.columns:
            pct_change = df['Close'].pct_change().abs()
            anomalies = pct_change[pct_change > 0.10]
            if not anomalies.empty:
                count = len(anomalies)
                max_spike = round(anomalies.max() * 100, 1)
                result['issues'].append(f'ANOMALY: Found {count} price spikes >10% (Max: {max_spike}%)')
                # We don't mark 'ok' = False for anomalies yet, but we log them.

        result['bars'] = len(df)
        result['latest'] = str(latest.date())
        result['oldest'] = str(df.index[0].date())

    return result


def write_known_data_gaps(gap_issues: dict):
    """Write gap_issues {coin: {tf: [issue_str]}} to known_data_gaps.md at project root."""
    gaps_path = os.path.join(ROOT_DIR, 'known_data_gaps.md')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# Known Data Gaps\n',
        '\n',
        f'**Owned by `@crypto-data-engineer`** — refreshed after every sync run. Do not edit manually.\n',
        f'**Last refreshed**: {ts}\n',
        '\n',
        'The following coin/timeframe pairs have data gaps or stale data. Avoid in backtests until repaired.\n',
        '\n',
        '**Note on 1m timeframe**: 1m data is not used by any active strategy — safely ignored unless explicitly needed.\n',
        '\n',
    ]
    crypto_coins = {'BTC', 'ETH', 'BNB', 'SOL', 'XRP'}
    drl_coins = {'DXY', 'JPY', 'SPY', 'VIX'}
    has_gaps = False
    for coin in sorted(gap_issues.keys()):
        tfs_with_issues = sorted(gap_issues[coin].keys())
        if not tfs_with_issues:
            continue
        has_gaps = True
        suffix = ' (DRL-only folder — skip for classical strategies)' if coin in drl_coins else ''
        lines.append(f'- **{coin}**: {", ".join(tfs_with_issues)}{suffix}\n')
    if not has_gaps:
        lines.append('- No gaps detected — all crypto assets fresh.\n')
    with open(gaps_path, 'w') as f:
        f.writelines(lines)
    log(f'  Updated known_data_gaps.md ({len(gap_issues)} coins with issues)')


def run_health_check():
    rotate_log(HEALTH_LOG)
    update_heartbeat('Scanning dataset for health check')
    log('--- DATA ENGINEER HEALTH CHECK START ---')
    issues_by_agent = {'crypto-fullstack': [], 'alpha-researcher': []}
    gap_issues = {}  # {coin: {tf: [issue_str]}} — written to known_data_gaps.md

    if not os.path.exists(DATASET_DIR):
        log(f'  [ERROR] Dataset directory not found: {DATASET_DIR}')
        return

    coins = [d for d in os.listdir(DATASET_DIR)
             if os.path.isdir(os.path.join(DATASET_DIR, d)) and not d.startswith(('.', '_'))]
    log(f'  Scanning {len(coins)} coins: {", ".join(sorted(coins))}')

    for coin in sorted(coins):
        coin_dir = os.path.join(DATASET_DIR, coin)
        tfs = [d for d in os.listdir(coin_dir) if os.path.isdir(os.path.join(coin_dir, d))]
        for tf in sorted(tfs):
            if tf not in BARS_PER_DAY: continue
            parquet = os.path.join(coin_dir, tf, 'spot_ohlcv.parquet')
            if not os.path.exists(parquet):
                continue

            r = check_parquet(coin, tf, parquet)
            if r['issues']:
                for issue in r['issues']:
                    log(f'  [{"ERROR" if not r["ok"] else "WARN"}] {coin}/{tf}: {issue}')
                    if 'DTYPE_ERROR' in issue or 'MISSING_COLUMN' in issue or 'UNREADABLE' in issue:
                        issues_by_agent['crypto-fullstack'].append({
                            'coin': coin, 'tf': tf, 'issue': issue, 'file': parquet
                        })
                    if 'DATA_GAP' in issue or 'STALE' in issue or 'ANOMALY' in issue or 'DUPLICATES' in issue:
                        issues_by_agent['alpha-researcher'].append({
                            'coin': coin, 'tf': tf, 'issue': issue
                        })
                        gap_issues.setdefault(coin, {})[tf] = r['issues']
            else:
                bars = r.get('bars', '?')
                latest = r.get('latest', '?')
                log(f'  [OK] {coin}/{tf}: {bars:,} bars, latest={latest}')

    # Send inbox messages for found issues
    dtype_issues = issues_by_agent['crypto-fullstack']
    if dtype_issues:
        write_inbox(
            'crypto-fullstack', 'DATA_INTEGRITY_ISSUE', 'HIGH',
            f'{len(dtype_issues)} files have schema or corruption issues.',
            {'errors': dtype_issues}
        )

    quant_issues = issues_by_agent['alpha-researcher']
    if quant_issues:
        # Throttle: only send DATA_QUALITY_ISSUE if researcher inbox doesn't already have one
        # (prevents flooding inbox every health check cycle — blocks research)
        researcher_inbox = os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-researcher', 'inbox')
        existing = glob.glob(os.path.join(researcher_inbox, '*DATA_QUALITY_ISSUE*.json')) + \
                   glob.glob(os.path.join(researcher_inbox, 'active', '*DATA_QUALITY_ISSUE*.json'))
        if not existing:
            write_inbox(
                'alpha-researcher', 'DATA_QUALITY_ISSUE', 'MEDIUM',
                f'{len(quant_issues)} coin/timeframe(s) have quality issues (gaps, anomalies, or stale).',
                {'affected': quant_issues}
            )

    summary_status = 'CLEAN' if not (dtype_issues or quant_issues) else 'ISSUES_FOUND'
    notes = ""
    if quant_issues:
        notes = f"{len(quant_issues)} quality issues found (stale/gaps/anomalies)."
    if dtype_issues:
        notes += f" {len(dtype_issues)} schema issues found."

    # Check funding_rate.parquet freshness for each crypto coin (threshold: 24h)
    crypto_coins = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
    funding_stale = []
    for coin in crypto_coins:
        fr_path = os.path.join(DATASET_DIR, coin, '4h', 'funding_rate.parquet')
        if not os.path.exists(fr_path):
            log(f'  [ERROR] {coin}/4h/funding_rate.parquet MISSING')
            funding_stale.append({'coin': coin, 'issue': 'MISSING'})
            continue
        try:
            fr_df = pd.read_parquet(fr_path)
            if 'open_time' in fr_df.columns:
                latest = pd.to_datetime(fr_df['open_time']).iloc[-1]
            else:
                latest = pd.to_datetime(fr_df.index[-1])
            now_ts = datetime.now(latest.tzinfo) if latest.tzinfo else datetime.now()
            hours_stale = (now_ts - latest.to_pydatetime().replace(tzinfo=None)).total_seconds() / 3600
            if hours_stale > 24:
                log(f'  [WARN] {coin}/4h/funding_rate: STALE — latest={latest.date()} ({int(hours_stale)}h ago)')
                funding_stale.append({'coin': coin, 'tf': '4h', 'issue': f'FUNDING_RATE_STALE: {int(hours_stale)}h ago'})
                gap_issues.setdefault(coin, {})['4h/funding_rate'] = [f'FUNDING_RATE_STALE: {int(hours_stale)}h ago']
            else:
                log(f'  [OK] {coin}/4h/funding_rate: {latest.date()} ({int(hours_stale)}h ago)')
        except Exception as e:
            log(f'  [ERROR] {coin}/4h/funding_rate: failed to read — {e}')
            funding_stale.append({'coin': coin, 'issue': str(e)})

    if funding_stale:
        write_inbox(
            'crypto-fullstack', 'FUNDING_RATE_STALE', 'HIGH',
            f'{len(funding_stale)} coin(s) have stale or missing funding_rate.parquet.',
            {'affected': funding_stale}
        )

    write_known_data_gaps(gap_issues)
    update_collaboration_md('Full Data Health Check', summary_status, notes.strip())
    log('--- HEALTH CHECK COMPLETE ---')


def handle_inbox():
    update_heartbeat('Reading inbox')
    os.makedirs(INBOX_DIR, exist_ok=True)
    inbox_files = sorted(glob.glob(os.path.join(INBOX_DIR, '*.json')))
    if not inbox_files:
        return
    
    log(f'  [INBOX] {len(inbox_files)} message(s) to process')
    for fpath in inbox_files:
        try:
            with open(fpath) as f:
                msg = json.load(f)
            
            priority = msg.get('priority', 'LOW')
            topic = msg.get('topic', 'UNKNOWN')
            sender = msg.get('from', 'unknown')
            log(f'  [INBOX] {priority} from @{sender}: {topic}')
            
            if topic == 'DATA_VALIDATION_REQUEST':
                ctx = msg.get('context', {})
                pairs = ctx.get('pairs', [])
                tfs = ctx.get('timeframes', [])
                for pair in pairs:
                    coin = pair.split('/')[0]
                    for tf in tfs:
                        parquet = os.path.join(DATASET_DIR, coin, tf, 'spot_ohlcv.parquet')
                        if os.path.exists(parquet):
                            r = check_parquet(coin, tf, parquet)
                            status = 'CLEAN' if r['ok'] else f'ISSUES: {r["issues"]}'
                            log(f'  [VALIDATION] {coin}/{tf}: {status}')
                        else:
                            log(f'  [VALIDATION] {coin}/{tf}: NOT FOUND')
            
            os.remove(fpath)
            log(f'  [INBOX] Processed: {os.path.basename(fpath)}')
            
        except Exception as e:
            log(f'  [ERROR] Failed to process inbox file {fpath}: {e}')

if __name__ == '__main__':
    handle_inbox()
    run_health_check()
    update_heartbeat('Idle', 'ONLINE')
