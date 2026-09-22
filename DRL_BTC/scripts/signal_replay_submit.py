"""
Run DRL agent deterministically and submit position-change signals to Signal Replay API.

The agent is run through a continuous date window.  Every time the position
changes (flat→long, flat→short, long→flat, etc.) a signal is emitted with the
bar's UTC timestamp in nanoseconds.  If the env hits the 50% DD kill we emit
a flat signal (we've been stopped out) and continue from the next available bar.

Sizing sent with every signal (Run B, alongside platform's standard Run A):
  margin   = $20,000  (20% of $100K starting capital)
  leverage = 1.5×     (matches fixed leverage in env)
  → notional = $30,000 per trade

Usage:
  # OOS period dry-run (inspect payload, no network)
  python DRL_BTC/scripts/signal_replay_submit.py --tag best_s42 --dry-run

  # OOS period live submit
  python DRL_BTC/scripts/signal_replay_submit.py --tag best_s42

  # Custom window
  python DRL_BTC/scripts/signal_replay_submit.py --tag best_s42 \\
      --start 2023-01-01 --end 2025-01-01

  # Full history (IS + OOS)
  python DRL_BTC/scripts/signal_replay_submit.py --tag best_s42 \\
      --start 2021-01-01
"""

import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import torch

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from DRL_BTC.signal_replay_use.config import CKPT_DIR
# Import training-matched params from main config so action decoding mirrors what the env saw during training
from DRL_BTC.config import ACTION_DIM, DIR_THRESHOLD, POS_SIZE_MIN, POS_SIZE_MAX, INITIAL_CAPITAL
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.signal_replay_use.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.utils import select_device


def _auto_patch_hidden(tag: str) -> None:
    """Detect LSTM hidden size from checkpoint and patch config so make_networks matches."""
    import DRL_BTC.config as _cfg
    path = CKPT_DIR / f"sac_{tag}.pt"
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    for k, v in ckpt["actor"].items():
        if "lstm" in k and "weight_hh" in k:
            hidden = v.shape[1]
            if hidden != _cfg.LSTM_HIDDEN or hidden != _cfg.FC_HIDDEN:
                print(f"[submit] Checkpoint hidden={hidden}; patching LSTM_HIDDEN/FC_HIDDEN {_cfg.LSTM_HIDDEN}→{hidden}")
                _cfg.LSTM_HIDDEN = hidden
                _cfg.FC_HIDDEN   = hidden
            break
    del ckpt

API_URL      = "https://btest.abcz-tr.com/api/v1/signals"
API_KEY_FILE = ROOT / "API & others" / "signal_replay_api.txt"

# Target scale: multiplied by the agent's raw position fraction to get submitted target.
# 1.0 = agent can go all-in (target=±1.0 at max conviction) → matches monster runs like sr_64da503058.
# 0.15 = conservative 15% cap (S27 original); 1.0 = full compounding (S28+).
TARGET_SCALE = 1.0


def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split("=", 1)[-1].strip()


def _ts_ns(ts) -> int:
    """Convert pandas Timestamp → int nanoseconds since epoch."""
    return int(ts.value)


def run_agent_signals(tag, start, end):
    """
    Run the DRL agent deterministically through [start, end] and return a list
    of position-change signals:
      [{"ts": <ns>, "target": +1/-1/0, "bar_time": <str>}, ...]

    Handles DD-kill episodes by emitting a flat signal and continuing from the
    next bar so the full window is covered in one continuous signal stream.
    """
    _auto_patch_hidden(tag)
    device = select_device()
    feats, close = load_features()
    feats = feats.fillna(0.0)
    market_cols = list(feats.columns)

    # Build date_range for BTCEnv
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_range = (
        start or "2021-01-01",
        end   or today,
    )

    agent = SACAgent(market_cols, N_PORTFOLIO_FEATS, ACTION_DIM, device)
    agent.load(tag)

    from DRL_BTC.signal_replay_use.config import SEQ_LEN

    # We need to scan through all bars in the range.  BTCEnv resets to the
    # start of the range on reset(); when truncated (DD kill) we note the bar
    # index and create a fresh env that starts exactly from there.
    #
    # Strategy: keep running episodes end-to-end; between episodes advance the
    # start pointer so we don't replay already-seen bars.

    signals: list[dict] = []
    current_position   = 0     # track our position for change detection
    last_step_idx      = None  # server-side step pointer after last episode

    episode_start_idx = None   # SEQ_LEN (beginning of date_range)

    # First episode — start from the beginning of the range
    env = BTCEnv(feats, close, mode="val", date_range=date_range)
    obs, _ = env.reset()
    episode_start_bar = env._step_idx  # = SEQ_LEN (first usable bar in range)

    n_episodes = 0
    total_bars = 0

    while True:
        action = agent.select_action(obs, deterministic=True)
        next_obs, _, terminated, truncated, info = env.step(action)
        total_bars += 1

        # Decode position + conviction from action[0] directly.
        # Direction: info["position"] (±1 or 0) set by env via the same DIR_THRESHOLD decode.
        # Size: |action[0]| beyond DIR_THRESHOLD, rescaled to [POS_SIZE_MIN, POS_SIZE_MAX],
        #       then normalised to [0, TARGET_SCALE] for submission.
        # This preserves the agent's per-trade conviction — strong signal → bigger position → more compounding.
        new_position = int(info["position"])   # -1, 0, or 1

        # Bar timestamp — step_idx already advanced, so current bar is step_idx-1
        bar_idx = min(env._step_idx - 1, len(env._features) - 1)
        bar_ts  = env._features.index[bar_idx]

        signed = float(action[0])
        if new_position != 0:
            raw_abs  = abs(signed)
            raw_size = max(0.0, min(1.0, (raw_abs - DIR_THRESHOLD) / (1.0 - DIR_THRESHOLD)))
            env_size = POS_SIZE_MIN + raw_size * (POS_SIZE_MAX - POS_SIZE_MIN)
            submit_target   = float(new_position) * (env_size / POS_SIZE_MAX) * TARGET_SCALE
            submit_strength = abs(submit_target)
        else:
            submit_target   = 0.0
            submit_strength = 0.0

        if new_position != current_position:
            sig = {
                "ts":       _ts_ns(bar_ts),
                "symbol":   "BTCUSDT",
                "target":   submit_target,
                "strength": float(submit_strength),
                "bar_time": str(bar_ts),
            }
            # Run B — must tag EVERY signal (including flat) or platform skips Run B entirely.
            sig["margin"]   = INITIAL_CAPITAL
            sig["leverage"] = 1.0
            # v2: NO TP/SL prices — platform was hitting SL on intrabar wicks (wick penetrates
            # SL but bar closes above it). Our env checks SL at bar close only. Removing TP/SL
            # makes platform exit match our env: only on signal change (direction flip in env).
            # if trade_params["take_profit_price"] is not None:
            #     sig["take_profit_price"] = float(trade_params["take_profit_price"])
            # if trade_params["stop_loss_price"] is not None:
            #     sig["stop_loss_price"] = float(trade_params["stop_loss_price"])
                
            signals.append(sig)
            current_position = new_position

        if terminated:
            break

        if truncated:
            # DD kill — ensure flat signal emitted
            if current_position != 0:
                signals.append({
                    "ts":       _ts_ns(bar_ts),
                    "target":   0.0,
                    "bar_time": str(bar_ts),
                    "margin":   INITIAL_CAPITAL,
                    "leverage": 1.0,
                })
                current_position = 0

            # Restart from the next bar
            n_episodes += 1
            next_start_idx = env._step_idx

            if next_start_idx >= len(env._features) - 1:
                break

            # Slice feature range so BTCEnv starts from next_start_idx after reset()
            next_bar_time = str(env._features.index[next_start_idx - SEQ_LEN])
            new_dr = (next_bar_time, date_range[1])

            env = BTCEnv(feats, close, mode="val", date_range=new_dr)
            if len(env._features) <= SEQ_LEN + 1:
                break
            obs, _ = env.reset()
            continue

        obs = next_obs  # normal step — advance obs
        # Normal case: just got next obs from step()
        # (env.step already returned next_obs; we use the obs from step return)
        # Re-assign: obs was already updated at the top of the loop via step return value

    # Do NOT append a final flat signal — let the platform hold the last
    # position until the window's end date (omitting a signal = keep last state).

    # Prepend a flat signal so the platform starts from a known flat state.
    if signals:
        anchor_ts = signals[0]["ts"] - 1  # 1 ns before first real signal
        signals.insert(0, {
            "ts":       anchor_ts,
            "symbol":   "BTCUSDT",
            "target":   0.0,
            "margin":   INITIAL_CAPITAL,
            "leverage": 1.0,
        })

    print(f"  Episodes   : {n_episodes + 1}")
    print(f"  Bars       : {total_bars:,}")
    print(f"  Signals    : {len(signals) - 1} trades + 1 anchor")
    print(f"  TargetScale: {TARGET_SCALE}  (POS_SIZE_MAX={POS_SIZE_MAX})")
    print(f"  Run B      : margin=${INITIAL_CAPITAL:,.0f}, leverage=1.0")

    return signals


def build_payload(signals, start, end, name=None):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    api_signals = []
    for s in signals:
        sig = {
            "ts":       s["ts"],
            "symbol":   "BTCUSDT",
            "target":   s["target"],
            "strength": s.get("strength", 1.0),
        }
        if "take_profit_price" in s:
            sig["take_profit_price"] = s["take_profit_price"]
        if "stop_loss_price" in s:
            sig["stop_loss_price"] = s["stop_loss_price"]
        if "margin" in s:
            sig["margin"]   = s["margin"]
            sig["leverage"] = s.get("leverage", 1.0)
        api_signals.append(sig)

    payload = {
        "symbol":     "BTCUSDT",
        "resolution": "1h",
        "signals":    api_signals,
    }
    payload["strategy"] = name if name else "Quant_Macro_v2"
    if start:
        payload["start"] = start
    if end:
        payload["end"] = end

    return payload


def submit_payload(payload: dict, api_key: str) -> dict:
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("API Error Response:", resp.text)
        raise e
    return resp.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit DRL agent signals to Signal Replay")
    parser.add_argument("--tag",     default="best_s42", help="Checkpoint tag (default: best_s42)")
    parser.add_argument("--name",    default=None,       help="Strategy name to include in payload (e.g. 'DRL')")
    parser.add_argument("--start",   default=None,       help="Start date YYYY-MM-DD (default: 2025-01-01 OOS)")
    parser.add_argument("--end",     default=None,       help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="Build payload but do not POST")
    args = parser.parse_args()

    # Default to OOS window (2025-01-01 → today) if no dates given
    start = args.start or "2025-01-01"
    end   = args.end

    print(f"\n{'='*60}")
    print(f"  DRL Signal Replay Submission")
    print(f"  Checkpoint : {args.tag}")
    print(f"  Name       : {args.name or '(none)'}")
    print(f"  Window     : {start} → {end or 'today'}")
    print(f"  Mode       : {'DRY RUN' if args.dry_run else 'LIVE SUBMIT'}")
    print(f"{'='*60}\n")

    print("Running agent...")
    signals = run_agent_signals(args.tag, start, end)

    if not signals:
        print("No signals generated — nothing to submit.")
        sys.exit(1)

    payload = build_payload(signals, start, end, name=args.name)

    print(f"\nPayload summary:")
    print(f"  Resolution : {payload['resolution']}")
    print(f"  Signals    : {len(payload['signals'])}")
    if payload["signals"]:
        first = payload["signals"][0]
        last  = payload["signals"][-1]
        print(f"  First      : bar={signals[0].get('bar_time', 'anchor')}  target={first['target']:+.0f}")
        print(f"  Last       : bar={signals[-1].get('bar_time', 'anchor')}  target={last['target']:+.0f}")

    if args.dry_run:
        print("\n[DRY RUN] Payload (first 3 signals):")
        preview = dict(payload)
        preview["signals"] = payload["signals"][:3]
        print(json.dumps(preview, indent=2))
        print(f"  ... + {len(payload['signals']) - 3} more signals")
    else:
        print("\nSubmitting to Signal Replay API...")
        api_key = _load_api_key()
        response = submit_payload(payload, api_key)
        print("\nAPI Response:")
        print(json.dumps(response, indent=2))

        out_file = ROOT / "Signal_Replay" / f"drl_submission_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(out_file, "w") as f:
            json.dump({"payload_summary": {
                "tag": args.tag, "name": args.name, "start": start, "end": end,
                "n_signals": len(payload["signals"]),
            }, "response": response}, f, indent=2)
        print(f"\nSaved → {out_file}")
