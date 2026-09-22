#!/usr/bin/env bash
# Deploy updated code + new futures_metrics.parquet to server.
# Run locally after download completes and feature rebuild is done.
# Usage: bash DRL_BTC/scripts/deploy_to_server.sh

set -euo pipefail

SERVER="root@47.250.37.200"
KEY="$HOME/.ssh/myserver"
REMOTE="/root/wkang"
LOCAL="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== Deploying to $SERVER ==="
echo "Local root: $LOCAL"

# 1. Sync updated Python code
echo ""
echo "--- Syncing Python code ---"
rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/features/feature_builder.py" \
    "$SERVER:$REMOTE/DRL_BTC/features/"

rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/models/actor_critic.py" \
    "$SERVER:$REMOTE/DRL_BTC/models/"

rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/scripts/fetch_futures_metrics.py" \
    "$SERVER:$REMOTE/DRL_BTC/scripts/"

rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/training/train.py" \
    "$SERVER:$REMOTE/DRL_BTC/training/"

rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/config.py" \
    "$SERVER:$REMOTE/DRL_BTC/"

rsync -av --no-perms -e "ssh -i $KEY" \
    "$LOCAL/DRL_BTC/env/btc_env.py" \
    "$SERVER:$REMOTE/DRL_BTC/env/"

# 2. Sync futures metrics data (large file, show progress)
echo ""
echo "--- Syncing futures_metrics.parquet ---"
METRICS_LOCAL="$LOCAL/dataset/BTC/1h/futures_metrics.parquet"
if [ -f "$METRICS_LOCAL" ]; then
    rsync -av --progress --no-perms -e "ssh -i $KEY" \
        "$METRICS_LOCAL" \
        "$SERVER:$REMOTE/dataset/BTC/1h/"
    echo "Metrics file synced."
else
    echo "WARNING: futures_metrics.parquet not found locally at $METRICS_LOCAL"
    echo "Run: python -u -m DRL_BTC.scripts.fetch_futures_metrics first"
fi

# 3. Sync raw 5m cache (for resumability on server)
RAW_LOCAL="$LOCAL/dataset/BTC/1h/_metrics_5m_raw.parquet"
if [ -f "$RAW_LOCAL" ]; then
    rsync -av --progress --no-perms -e "ssh -i $KEY" \
        "$RAW_LOCAL" \
        "$SERVER:$REMOTE/dataset/BTC/1h/"
    echo "Raw 5m cache synced."
fi

# 4. Rebuild feature cache on server (runs fast ~5-10 min)
echo ""
echo "--- Rebuilding feature cache on server ---"
ssh -i "$KEY" "$SERVER" "
    cd $REMOTE
    source /root/ytee/.venv/bin/activate
    echo 'Rebuilding features...'
    python -u -m DRL_BTC.features.feature_builder 2>&1
"
echo "Feature rebuild complete."

# 5. Print new feature count
echo ""
echo "--- New feature cache info ---"
ssh -i "$KEY" "$SERVER" "
    source /root/ytee/.venv/bin/activate
    python3 -c \"
import pandas as pd
from pathlib import Path
p = Path('$REMOTE/DRL_BTC/data/features/features.parquet')
df = pd.read_parquet(p)
print(f'Features: {df.shape[1]} cols x {df.shape[0]} rows')
print(f'New OI/sentiment cols: {[c for c in df.columns if any(c.startswith(x) for x in (\\\"oi_\\\", \\\"ls_\\\", \\\"top_\\\", \\\"taker_ls\\\", \\\"basis_\\\"))]}')
\"
"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Next steps:"
echo "  1. Wait for current training to complete (~06:00 Jul 17)"
echo "  2. SSH to server: ssh -i ~/.ssh/myserver root@47.250.37.200"
echo "  3. cd /root/wkang && tmux new-session -s next_run"
echo "  4. unset LD_LIBRARY_PATH && source /root/ytee/.venv/bin/activate"
echo "  5. python -m DRL_BTC.training.train --seed 42"
