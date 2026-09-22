# API & others

Central store for **every credential** used by this repo. The entire folder is
git-ignored (`.gitignore` → `API & others/*`); only `README.md` and the
`*.example` templates are tracked.

**Never commit anything else from this folder.**

## Files

| File | Used by | Format |
|---|---|---|
| `signal_replay_api.txt` | `Signal_Replay/submit_*.py`, `DRL_BTC/scripts/signal_replay_submit.py` | `Signal_Replay_API_KEY=<key>` |
| `binance_api.txt` | reference only (runtime uses `.env`) | labelled key / secret blocks |
| `open_router_API.txt` | `main_controller/main.py` | raw key, no prefix |
| `factorhub_api.txt` | `post_feature_to_hub.py` | `API_TOKEN=<token>` |
| `feature_hub_jwt.txt` | `post_feature_to_hub_v2.py`, `develop_10_factors.py` | `TOKEN=<jwt>` |
| `signal_strive_API.txt` | reference doc — no code reads it | Signal Strive API notes with a live `sk_sig_…` key in the curl examples |
| `myserver` | SSH key for TEE server `47.250.37.200` | OpenSSH private key |

## Setup on a fresh clone

Copy each template and fill in the real value:

```bash
cd "API & others"
for f in *.example; do cp "$f" "${f%.example}"; done
chmod 600 *                      # keep them private
```

`myserver` is **not** templated — copy your existing key in, or generate a new
one. Note that `DRL_BTC/scripts/deploy_to_server.sh` reads it from
`~/.ssh/myserver`, not from here; this copy is a backup.

## `.env` is separate

`.env` stays at the repo root on purpose — `load_dotenv()` auto-discovers it by
walking up from the current working directory, and `core/config_api.py` plus the
`.gemini/skills/crypto-data-engineer/scripts/*` fetchers depend on that
behaviour. It is git-ignored independently.

It holds: `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `HTTPS_PROXY`.
